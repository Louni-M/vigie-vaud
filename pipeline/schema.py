"""Schéma commun de Vigie Vaud (ADR 0013) : le seul endroit où il s'écrit.

Ces modèles Pydantic décrivent `sources.json` (déclaration des sources, écrite à la main) et les fichiers du
dépôt de données, qui portent tous l'enveloppe `version` + `genere`. Le cron valide ce qu'il lit et écrit en
construisant ces modèles.

On en tire le JSON Schema, versionné dans `schema/` à la racine du dépôt, puis les types TypeScript du site
(`web/src/lib/schema.ts`). Après toute modification, régénérer les deux avec `pnpm --dir web schema` ; la CI
échoue s'ils ne sont pas à jour.

Réglages repris de l'essai de #3, pour des types TypeScript aussi propres qu'écrits à la main :
- pas de titre par champ (sinon `json-schema-to-typescript` crée un alias par champ) ;
- énumérations nommées par `TypeAliasType` (un seul type TypeScript, réutilisé partout) ;
- `extra="forbid"` (sinon chaque interface admet des clés inconnues).

Usage : `uv run python schema.py` écrit les JSON Schema dans `schema/`.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StringConstraints,
    model_validator,
)
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import TypeAliasType

RACINE = Path(__file__).resolve().parent.parent
DOSSIER_SCHEMA = RACINE / "schema"


class Modele(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Types communs ---------------------------------------------------------------------------------------------

Lien = TypeAliasType("Lien", Annotated[str, StringConstraints(pattern=r"^https?://\S+$")])
NumeroOfs = TypeAliasType("NumeroOfs", Annotated[int, Field(ge=1, le=9999)])


def _en_utc(d: datetime) -> datetime:
    if d.utcoffset() != timedelta(0):
        raise ValueError("l'heure doit être en UTC (suffixe Z)")
    return d


Horodatage = TypeAliasType("Horodatage", Annotated[AwareDatetime, AfterValidator(_en_utc)])


class Enveloppe(Modele):
    """Enveloppe de chaque fichier du dépôt de données."""

    version: Annotated[int, Field(ge=1)] = Field(
        description="Version majeure du format : seul un changement incompatible l'augmente. "
        "Le site refuse une version qu'il ne connaît pas."
    )
    genere: Horodatage = Field(description="Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).")


# --- sources.json ----------------------------------------------------------------------------------------------

IdSource = TypeAliasType("IdSource", Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")])
VoieAcces = TypeAliasType("VoieAcces", Literal["direct", "cron", "worker", "preparee"])
SorteFraicheur = TypeAliasType("SorteFraicheur", Literal["donnee", "requete", "millesime", "import"])
ModeCouverture = TypeAliasType("ModeCouverture", Literal["api", "scrape"])


class Attribution(Modele):
    texte: str = Field(min_length=1, description="Texte affiché, par ex. « © swisstopo ».")
    lien: Lien
    licence: str = Field(min_length=1)


class CouvertureDeclaree(Modele):
    communes: Literal["canton"] | Annotated[list[NumeroOfs], Field(min_length=1)] = Field(
        description="« canton » (les 300 communes) ou la liste des n° OFS des communes couvertes."
    )
    mode: ModeCouverture


class Sonde(Modele):
    """Requête de vérification envoyée par le cron, sans conserver de données.

    Une seule requête GET par passage, sans nouvel essai. La réponse doit être un objet JSON dont une clé
    (`enregistrements`) liste les enregistrements ; elle doit donc rester légère (un enregistrement suffit).
    """

    url: Lien
    delai: Annotated[int, Field(ge=1, le=60)] = Field(description="Délai de réponse en secondes.")
    champs: list[str] = Field(
        default=[],
        description="Champs que doit porter chaque enregistrement renvoyé, lus dans `attributes` (JSON ArcGIS) "
        "ou `properties` (GeoJSON), sinon à plat dans l'enregistrement (OpenParlData).",
    )
    enregistrements: str = Field(
        default="features",
        min_length=1,
        description="Clé de la réponse qui liste les enregistrements : `features` (JSON ArcGIS, GeoJSON) ou `data` "
        "(OpenParlData).",
    )
    jamais_vide: bool = Field(default=False, description="Une réponse sans enregistrement compte comme un échec.")


DonneeConseil = TypeAliasType("DonneeConseil", Literal["objets", "preavis", "seances"])


class Conseil(Modele):
    """Un conseil importé par le cron : exposé par OpenParlData, ou lu sur le site de sa commune quand la source a un
    bloc `site`. Le cron importe chaque source qui a ce bloc."""

    body_key: str = Field(
        pattern=r"^[A-Z0-9]+$",
        description="Clé du conseil dans OpenParlData : `VD` (Grand Conseil) ou le n° OFS de la commune. "
        "En minuscules, c'est la clé du conseil dans le dépôt de données.",
    )
    donne: Annotated[list[DonneeConseil], Field(min_length=1)] = Field(
        description="Ce que le conseil donne : ses Objets, ses Séances, ou les deux ; `preavis` : ses préavis seulement, "
        "parmi ses Objets. Pour une commune scrapée, c'est son niveau, déclaré d'après sa variante, jamais déduit de "
        "l'import : `objets` + `seances` (« objets et séances »), `preavis` + `seances` (« séances et préavis ») ou "
        "`seances` (« séances seulement »)."
    )
    page: Lien | None = Field(
        default=None,
        description="Page du conseil sur le site de sa commune, vers laquelle renvoie la note de niveau d'un conseil "
        "qui ne donne pas tout et n'a pas de bloc `site` (Yverdon) ; une commune scrapée renvoie à `site.seances`.",
    )
    groupe: int | None = Field(
        default=None,
        description="`group_id` des Séances à importer : celui du Grand Conseil écarte les Séances du Conseil d'État.",
    )

    @property
    def cle(self) -> str:
        """Clé du conseil dans le dépôt de données : `body_key` en minuscules (`vd`, `5586`), comme `cleConseil`
        du site."""
        return self.body_key.lower()

    @property
    def commune(self) -> int | None:
        """N° OFS de la commune d'un conseil communal (`body_key` numérique) ; `None` pour le Grand Conseil."""
        return int(self.body_key) if self.body_key.isdigit() else None


def nom_du_conseil(nom_source: str) -> str:
    """Nom du conseil, tiré du nom de sa source : sans la mention finale entre parenthèses, l'apostrophe
    typographique (« Conseil communal d’Yverdon-les-Bains »). La même règle que `nomDuConseil` du site."""
    return re.sub(r"\s*\([^()]*\)$", "", nom_source).replace("'", "’")


IdPlateforme = TypeAliasType("IdPlateforme", Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")])


class Site(Modele):
    """Le site d'une commune scrapée : sa plateforme, sa variante et ses pages. Le cron le lit par le robot communal."""

    plateforme: IdPlateforme = Field(description="Identifiant de la plateforme, déclarée dans `plateformes`.")
    variante: str = Field(min_length=1, description="Identifiant de la variante, déclarée dans sa plateforme.")
    seances: Lien = Field(
        description="Page de liste des Séances, relue en entier à chaque import ; c'est aussi la page sondée."
    )
    objets: Lien | None = Field(default=None, description="Page de liste des Objets ou des préavis, selon la variante.")
    membres: Lien | None = Field(
        default=None, description="Page des membres du conseil, en HTML ; absente si le site n'en a pas."
    )


class Variante(Modele):
    id: str = Field(min_length=1, description="Identifiant de la variante dans sa plateforme (`seances`).")
    marqueur: str = Field(
        min_length=1, description="Marqueur que la sonde cherche sur la page de liste des Séances d'une commune."
    )
    niveaux: Annotated[list[Annotated[list[DonneeConseil], Field(min_length=1)]], Field(min_length=1)] = Field(
        description="Les niveaux que la variante permet : chacun est un `conseil.donne` qu'une commune de cette "
        "variante peut déclarer (`[\"seances\"]` : séances seulement ; `[\"preavis\", \"seances\"]` : séances et "
        "préavis)."
    )


class Plateforme(Modele):
    """Une plateforme retenue : le logiciel d'un éditeur sur lequel tournent les sites de plusieurs communes."""

    id: IdPlateforme = Field(description="Identifiant cité par le bloc `site` des sources (`i-web`).")
    nom: str = Field(min_length=1, description="Nom affiché par la page Couverture et l'À propos.")
    editeur: str = Field(min_length=1)
    variantes: Annotated[list[Variante], Field(min_length=1)]


class Source(Modele):
    id: IdSource = Field(description="Identifiant stable, clé de la source dans l'état des sources.")
    nom: str = Field(min_length=1)
    nom_court: str = Field(min_length=1, description="Nom affiché dans le badge de fraîcheur (« · CAMAC »).")
    attribution: Attribution
    voie_acces: VoieAcces
    fraicheur: SorteFraicheur
    couverture: CouvertureDeclaree | None = Field(
        default=None,
        description="Absente, la source n'a pas de Couverture : elle porte sur le canton (Grand Conseil) ou ses "
        "éléments n'appartiennent à aucune commune.",
    )
    limites: str | None = Field(
        default=None,
        min_length=1,
        description="Ce que la source ne publie pas toujours dans les communes qu'elle couvre : une phrase qui "
        "complète « La DGMR publie … ». Reprise par la page Couverture et par l'onglet de la couche ; "
        "ne change ni le mode ni l'état.",
    )
    sonde: Sonde | None = Field(default=None, description="Sans sonde, la source n'est pas surveillée.")
    conseil: Conseil | None = Field(default=None, description="Le conseil que donne la source, importé par le cron.")
    site: Site | None = Field(
        default=None,
        description="Le site d'une commune scrapée. Avec un bloc `conseil`, le cron lit le conseil sur ce site au lieu "
        "d'OpenParlData.",
    )


class FichierSources(Modele):
    """`sources.json` : chaque source y est déclarée une seule fois, pour le site et pour le cron."""

    schema_: str | None = Field(default=None, alias="$schema")
    plateformes: list[Plateforme] = Field(
        default=[], description="Les plateformes retenues, que citent les blocs `site` des sources communales."
    )
    sources: list[Source]

    @model_validator(mode="after")
    def _ids_uniques(self) -> FichierSources:
        vus: set[str] = set()
        for s in self.sources:
            if s.id in vus:
                raise ValueError(f"identifiant de source en double : {s.id}")
            vus.add(s.id)
        return self


def lire_sources(chemin: Path) -> FichierSources:
    return FichierSources.model_validate_json(chemin.read_bytes())


# --- État des sources (etat-sources.json, dépôt de données) ----------------------------------------------------

EtatSonde = TypeAliasType("EtatSonde", Literal["disponible", "en_panne"])


class EtatSource(Modele):
    """Ce que les sondes ont mesuré pour une source, dans un état binaire (sans « dégradée »).

    Aucun numéro d'issue n'y figure.
    """

    etat: EtatSonde
    depuis: Horodatage | None = Field(
        description="En panne : heure de la première sonde en échec. Disponible : heure du retour, ou de la première "
        "sonde réussie ; `null` tant qu'aucune sonde n'a réussi."
    )
    derniere_sonde: Horodatage
    dernier_succes: Horodatage | None = Field(description="`null` tant qu'aucune sonde n'a réussi.")
    echecs_consecutifs: Annotated[int, Field(ge=0)] = Field(description="La source passe en panne à 2.")
    motif: str | None = Field(
        description="Cause courte du dernier échec (« HTTP 503 », « délai dépassé », « marqueur absent »…)."
    )


class EtatSources(Enveloppe):
    """`etat-sources.json` : l'état de chaque source sondée, indexé par identifiant de source."""

    version: Literal[1] = Field(description="Version 1. Le cron repart de zéro devant une autre version.")
    sources: dict[IdSource, EtatSource] = Field(
        description="Les sources qui ont un bloc `sonde`, et les sources communales sondées (bloc `site` et conseil), "
        "qui y figurent dès leur première sonde, faite une fois par jour juste avant leur import."
    )


# --- Import des conseils (conseils/import.json, dépôt de données) ----------------------------------------------

CleConseil = TypeAliasType("CleConseil", Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+$")])


class ImportConseils(Enveloppe):
    """`conseils/import.json` : l'heure du dernier import réussi de chaque conseil, importé à part. C'est la
    mémoire du cron et la base du badge de fraîcheur des sources `import`."""

    version: Literal[1] = Field(description="Version 1.")
    conseils: dict[CleConseil, Horodatage] = Field(
        description="Par clé de conseil (`body_key` en minuscules : `vd`, `5586`…), l'heure du dernier import "
        "réussi. Un conseil jamais importé n'y figure pas."
    )


class MembresConseil(Enveloppe):
    """`conseils/<conseil>/membres.json` : les élu·e·s connu·e·s d'un conseil scrapé, que le masquage épargne
    (ADR 0007) : vu·e·s sur la page des membres du conseil ou comme contributeur·rice·s d'un Objet autre qu'une
    pétition. La liste ne fait que s'allonger : un nom qui disparaît de la page y reste. Publique, en clair, sans
    limite de durée. Les conseils d'OpenParlData n'en ont pas : leurs élu·e·s connu·e·s sont tiré·e·s de l'archive."""

    version: Literal[1] = Field(description="Version 1.")
    conseil: CleConseil = Field(description="Le conseil (`body_key` en minuscules : le n° OFS de la commune).")
    membres: list[str] = Field(
        description="Noms complets, « Prénom Nom », triés sans tenir compte des accents ni de la casse."
    )


# --- Archive des conseils (conseils/<conseil>/objets|seances/*.json, dépôt de données ; ADR 0017) --------------

CleElement = TypeAliasType("CleElement", Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+/[^/\s]+$")])
SorteContributeur = TypeAliasType("SorteContributeur", Literal["personne", "groupe"])


class Statut(Modele):
    libelle: str = Field(
        description="Le `state_name` brut de la source quand il existe, sinon le libellé de la dernière étape datée."
    )
    date: dt.date | None = Field(description="Date de la dernière étape datée ; `null` si aucune étape n'est datée.")


class Contributeur(Modele):
    nom: str
    parti: str | None = Field(description="Abréviation du parti, telle que la source la donne.")
    role: str | None = Field(description="Rôle brut (« Auteur », « Cosignataires », « Federführung »…).")
    sorte: SorteContributeur


class Etape(Modele):
    date: dt.date
    libelle: str = Field(description="`title.fr` de la source, sinon `title_harmonized.fr`, brut.")


class DocumentObjet(Modele):
    titre: str | None = Field(description="Nom du document, sinon sa catégorie.")
    date: dt.date | None
    lien: Lien = Field(description="Le document chez la source (PDF, page ou vidéo).")


OrigineCommune = TypeAliasType("OrigineCommune", Literal["titre", "document", "correction"])


class CommuneRattachee(Modele):
    """Une commune rattachée à un Objet du Grand Conseil (ADR 0016), avec l'origine du rattachement."""

    ofs: NumeroOfs
    origine: OrigineCommune = Field(
        description="`titre` : nommée dans le titre ; `document` : citée dans un document ; `correction` : ajoutée "
        "à la main par `corrections.json`."
    )


class Objet(Enveloppe):
    """`conseils/<conseil>/objets/<numéro>.json` : un Objet d'un conseil, normalisé depuis OpenParlData. Sa clé est
    `<conseil>/<numéro>`, la barre oblique du numéro devenant `-` (`vd/26_INT_140`, `5586/POS25-115`)."""

    version: Literal[1] = Field(description="Version 1.")
    id: int | None = Field(description="Identifiant de l'Objet dans OpenParlData ; `null` pour un Objet scrapé.")
    numero: str = Field(min_length=1, description="Numéro que lui donne le conseil (`26_INT_140`, `POS25/115`).")
    type: str = Field(description="Type brut de la source (`type_name`).")
    statut: Statut | None
    depose: dt.date | None = Field(description="Date de dépôt (`begin_date`).")
    titre: str = Field(description="`title.fr` de la source, noms de particuliers masqués (« [particulier] », ADR 0007).")
    contributeurs: list[Contributeur] = Field(description="Dans l'ordre de la source ; vide pour une pétition.")
    etapes: list[Etape] = Field(description="Étapes datées, de la plus ancienne à la plus récente.")
    documents: list[DocumentObjet]
    lien: Lien | None = Field(description="Page de l'Objet chez le conseil (`url_external`).")
    communes: list[CommuneRattachee] = Field(
        description="Grand Conseil : les communes rattachées par le nom (ADR 0016), dans l'ordre du rattachement "
        "(titre, puis documents de la plus à la moins citée, puis corrections), `corrections.json` appliqué. Vide "
        "pour un conseil communal, dont les Objets n'appartiennent qu'à leur commune."
    )


DateSeance = TypeAliasType(
    "DateSeance", Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?$")]
)


class PointOrdreDuJour(Modele):
    numero: str | None = Field(description="Numéro du point tel que la source l'affiche.")
    titre: str = Field(description="`item_title` de la source, noms de particuliers masqués (« [particulier] », ADR 0007).")
    categorie: str | None
    resultat: str | None = Field(description="Résultat brut (« Transmise au CE », « Renvoi en Municipalité »…).")
    objet: CleElement | None = Field(description="Clé de l'Objet du point, quand il est dans l'archive.")


class Seance(Enveloppe):
    """`conseils/<conseil>/seances/<AAAA-MM-JJ>.json` : une Séance d'un conseil. Sa clé est `<conseil>/<jour>`."""

    version: Literal[1] = Field(description="Version 1.")
    id: int | None = Field(description="Identifiant de la Séance dans OpenParlData ; `null` pour une Séance scrapée.")
    date: DateSeance = Field(description="Jour, heure locale comprise quand la source la donne (`2026-10-01T20:00`).")
    nom: str = Field(description="Nom brut de la source ; le site affiche un nom composé à partir de la date.")
    lien: Lien | None
    ordre_du_jour: list[PointOrdreDuJour]
    documents: list[DocumentObjet] = Field(
        default=[],
        exclude_if=lambda documents: not documents,
        description="Documents de la Séance (ordre du jour, procès-verbal…), titres masqués. Absent quand il n'y en "
        "a pas : Lausanne et Yverdon n'en ont pas.",
    )


class Correction(Modele):
    """Une correction de rattachement écrite à la main dans `corrections.json` (ADR 0016)."""

    objet: CleElement = Field(description="Clé de l'Objet corrigé (`vd/26_INT_140`).")
    retirer: list[NumeroOfs] = Field(default=[], description="Communes à retirer du rattachement par le nom.")
    ajouter: list[NumeroOfs] = Field(
        default=[], description="Communes à ajouter, en fin de liste, avec l'origine `correction`."
    )
    note: str = Field(min_length=1, description="La raison de la correction, pour qui la relit.")


class Corrections(RootModel[list[Correction]]):
    """`corrections.json`, à la racine du dépôt de données : les corrections de rattachement, écrites à la main et
    appliquées à chaque import comme au rattrapage. Sans enveloppe : le cron ne l'écrit jamais."""


# --- Fichiers de lecture des conseils (conseils/*.json, dépôt de données ; ADR 0017) ---------------------------
# Reconstruits en entier depuis l'archive à chaque import : c'est ce que le site lit pour lister.


class Auteur(Modele):
    nom: str
    parti: str | None


class LigneObjet(Modele):
    """Un Objet en ligne légère, commune aux listes par année, à « Au Grand Conseil » et à l'index : de quoi
    l'afficher dans une liste. Le détail est dans son fichier d'archive."""

    cle: CleElement = Field(description="`<conseil>/<numéro>` : le fichier d'archive de l'Objet.")
    numero: str
    type: str
    depose: dt.date | None
    titre: str
    auteurs: list[Auteur] = Field(description="Les deux premiers contributeurs, dans l'ordre de la source.")
    nombre_auteurs: Annotated[int, Field(ge=0)] = Field(description="Nombre de tous les contributeurs.")
    statut: Statut | None
    derniere_etape: dt.date | None = Field(description="Date de la dernière étape datée.")
    communes: list[CommuneRattachee] = Field(
        description="Grand Conseil : les communes rattachées, dans l'ordre du rattachement. Vide pour un conseil "
        "communal, dont les Objets n'appartiennent qu'à sa commune."
    )


class ListeObjets(Enveloppe):
    """`conseils/<conseil>/objets-<année>.json` : les Objets du conseil déposés cette année-là, du plus récent au
    plus ancien. Un Objet sans date de dépôt est classé à l'année de sa première étape datée ; sans aucune date, il
    n'est dans aucune liste (son fichier d'archive reste ouvrable)."""

    version: Literal[1] = Field(description="Version 1.")
    conseil: CleConseil
    annee: int
    objets: list[LigneObjet]


class LigneSeance(Modele):
    """Une Séance en ligne légère : de quoi l'afficher dans une liste, sans son ordre du jour."""

    cle: CleElement = Field(description="`<conseil>/<jour>` : le fichier d'archive de la Séance.")
    date: DateSeance
    points: Annotated[int, Field(ge=0)] = Field(description="Nombre de points de l'ordre du jour.")
    documents: list[DocumentObjet] = Field(
        default=[],
        exclude_if=lambda documents: not documents,
        description="Les documents d'une Séance sans points, que sa ligne montre à la place du nombre de points. "
        "Absent pour une Séance avec points ou sans documents.",
    )


class ListeSeances(Enveloppe):
    """`conseils/<conseil>/seances.json` : toutes les Séances du conseil, de la plus récente à la plus ancienne."""

    version: Literal[1] = Field(description="Version 1.")
    conseil: CleConseil
    seances: list[LigneSeance]


SorteElement = TypeAliasType("SorteElement", Literal["objet", "seance"])


class EntreeFil(Modele):
    """Un Objet ou une Séance, à la forme d'une entrée du fil cantonal."""

    cle: CleElement
    conseil: CleConseil
    sorte: SorteElement
    type: str | None = Field(description="Objet : son type brut. Séance : `null`.")
    date: DateSeance = Field(
        description="Objet : jour de dépôt, sinon de sa première étape datée. Séance : son jour, avec l'heure "
        "quand la source la donne."
    )
    titre: str = Field(description="Objet : son titre masqué. Séance : son nom brut (le site compose le sien).")
    communes: list[NumeroOfs] = Field(
        description="Conseil communal : sa commune. Grand Conseil : les communes rattachées à l'Objet, dans l'ordre "
        "du rattachement ; aucune pour une Séance."
    )
    points: Annotated[int, Field(ge=0)] | None = Field(
        description="Séance : nombre de points de l'ordre du jour. Objet : `null`."
    )


class FilConseils(Enveloppe):
    """`conseils/fil.json` : les Objets et les Séances de tous les conseils datés des 21 derniers jours (heure de
    Suisse, marge pour des imports manqués) ou après, donc toutes les Séances à venir, du plus récent au plus ancien.
    Le site filtre lui-même sur sa fenêtre."""

    version: Literal[1] = Field(description="Version 1.")
    entrees: list[EntreeFil]


class RattachementsCommune(Enveloppe):
    """`conseils/communes/<ofs>.json` (« Au Grand Conseil ») : les Objets du Grand Conseil rattachés à la commune,
    par date de dernière étape décroissante. Écrit seulement s'il y en a au moins un."""

    version: Literal[1] = Field(description="Version 1.")
    commune: NumeroOfs
    objets: list[LigneObjet]


class ConseilIndexe(Modele):
    """Un conseil dans l'index : de quoi remplir le volet et les compteurs sans autre requête."""

    cle: CleConseil
    source: IdSource = Field(description="La source qui donne le conseil, dans `sources.json`.")
    nom: str = Field(description="Nom du conseil, tiré du nom de sa source (« Conseil communal de Lausanne »).")
    commune: NumeroOfs | None = Field(description="La commune d'un conseil communal ; `null` pour le Grand Conseil.")
    donne: list[DonneeConseil]
    objets: Annotated[int, Field(ge=0)] = Field(description="Nombre d'Objets listés, toutes années confondues.")
    objets_par_annee: dict[str, Annotated[int, Field(ge=1)]] = Field(
        description="Nombre d'Objets par année (« 2026 »), une par fichier `objets-<année>.json`."
    )
    recents: list[LigneObjet] = Field(
        description="Les Objets des 14 derniers jours (date de dépôt, sinon de la première étape datée), du plus "
        "récent au plus ancien."
    )
    seances: Annotated[int, Field(ge=0)] = Field(description="Nombre de Séances.")
    prochaine_seance: CleElement | None = Field(description="La première Séance du jour du passage ou après.")
    derniere_seance: CleElement | None = Field(description="La dernière Séance avant le jour du passage.")


class IndexConseils(Enveloppe):
    """`conseils/index.json` : chaque conseil importé, dans l'ordre de `sources.json`, et le nombre d'Objets du
    Grand Conseil rattachés à chaque commune."""

    version: Literal[1] = Field(description="Version 1.")
    conseils: list[ConseilIndexe]
    communes: dict[str, Annotated[int, Field(ge=1)]] = Field(
        description="Par n° OFS de commune (« 5586 »), le nombre d'Objets du Grand Conseil qui lui sont rattachés. "
        "Une commune absente n'en a aucun : « Au Grand Conseil » est vide sans autre requête."
    )


# --- Génération du JSON Schema ---------------------------------------------------------------------------------

# Un JSON Schema par document : `schema/<nom>.schema.json`.
DOCUMENTS: dict[str, type[BaseModel]] = {
    "sources": FichierSources,
    "enveloppe": Enveloppe,
    "etat-sources": EtatSources,
    "import-conseils": ImportConseils,
    "membres-conseil": MembresConseil,
    "objet": Objet,
    "seance": Seance,
    "liste-objets": ListeObjets,
    "liste-seances": ListeSeances,
    "fil-conseils": FilConseils,
    "index-conseils": IndexConseils,
    "rattachements-commune": RattachementsCommune,
    "corrections": Corrections,
}


class _SansTitresDeChamps(GenerateJsonSchema):
    def field_title_should_be_set(self, schema) -> bool:  # noqa: ANN001
        return False


def json_schema(modele: type[BaseModel]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **modele.model_json_schema(schema_generator=_SansTitresDeChamps),
    }


def ecrire_schemas(dossier: Path = DOSSIER_SCHEMA) -> list[Path]:
    dossier.mkdir(parents=True, exist_ok=True)
    ecrits = []
    for nom, modele in DOCUMENTS.items():
        chemin = dossier / f"{nom}.schema.json"
        chemin.write_text(json.dumps(json_schema(modele), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ecrits.append(chemin)
    return ecrits


if __name__ == "__main__":
    for chemin in ecrire_schemas():
        print(chemin.relative_to(RACINE))
