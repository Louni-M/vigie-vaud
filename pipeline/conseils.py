"""Import des conseils (ADR 0015 et 0017) : les Objets et les Séances d'OpenParlData dans l'archive du dépôt de
données, un fichier par élément.

Le passage suit quatre étapes, chacune à sa place :

1. `importer(opd, conseil, depuis)` lit les changements bruts d'un conseil chez OpenParlData ;
2. `vers_archive(bruts, archive, genere)`, fonction pure, les normalise en Objets et Séances de l'archive ;
3. `lecture(archive)`, fonction pure, reconstruit les fichiers de lecture que le site liste ;
4. `ecrire(depot, documents, genere)` compare chaque fichier à l'ancien sans `genere` et n'écrit que ce qui change.

`importer_conseils` enchaîne les quatre pour chaque source qui a un bloc `conseil`, et tient à jour
`conseils/import.json` (dernier import réussi de chaque conseil). Un conseil en échec garde sa date et n'empêche
pas les autres. L'import ne supprime rien : un élément absent d'OpenParlData reste dans l'archive.

Usage loyal d'OpenParlData : au plus une requête par seconde, un User-Agent avec un contact, la pagination suivie
jusqu'au bout, et jamais un paramètre répété dans une requête (le cache du serveur ne garde que sa dernière valeur).

En local, contre un clone du dépôt de données (depuis `pipeline/`), sans rien pousser :

    uv run python conseils.py --depot ../../vigie-vaud-donnees --depuis 2026-10-10

Sans `--depuis`, chaque conseil repart du jour de son dernier import réussi, ou de tout l'historique s'il n'a
jamais été importé.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from schema import (
    RACINE,
    Conseil,
    Contributeur,
    DocumentObjet,
    Enveloppe,
    Etape,
    FichierSources,
    ImportConseils,
    Objet,
    PointOrdreDuJour,
    Seance,
    Statut,
    lire_sources,
)

API = "https://api.openparldata.ch/v1"
_CONFIG = json.loads((RACINE / "config.json").read_text())
USER_AGENT = f"VigieVaud-import (+{_CONFIG['depot']}; {_CONFIG['courriel']})"
INTERVALLE = 1.0  # secondes, au moins, entre deux requêtes
TAILLE_PAGE = 200
# Plafond de chaque relation développée (`expand`) : au-delà, l'import du conseil échoue plutôt que de tronquer.
TAILLE_RELATION = 1000
RECOUVREMENT = timedelta(days=1)
FICHIER_IMPORT = "conseils/import.json"

# Les demandes de grâce ne sont pas des Objets : elles nomment un particulier. L'exclusion est une liste de types.
TYPES_ECARTES = frozenset({"Grâce"})

CHAMPS_OBJETS = (
    "id,number,title,type_name,state_name,begin_date,url_external,"
    "contributors.type,contributors.fullname,contributors.firstname,contributors.lastname,contributors.party,"
    "contributors.role,contributors.position,"
    "events.date,events.position,events.title,events.title_harmonized,"
    "docs.name,docs.url,docs.date,docs.category"
)
CHAMPS_SEANCES = (
    "id,name,group_id,begin_date,url_external,"
    "agendas.item_number,agendas.item_number_display,agendas.item_title,agendas.item_category,agendas.item_result,"
    "agendas.item_affair_number,agendas.item_affair_id"
)


# --- 1. Lecture d'OpenParlData ---------------------------------------------------------------------------------


class OpenParlData:
    """Client d'OpenParlData qui s'en tient à l'usage loyal : une requête par seconde au plus (mesurée par
    `horloge`, attendue par `attendre`), un User-Agent avec un contact, et la pagination suivie jusqu'au bout.
    Une erreur HTTP lève `httpx.HTTPError`."""

    def __init__(
        self,
        http: httpx.Client,
        horloge: Callable[[], datetime],
        attendre: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = http
        self._horloge = horloge
        self._attendre = attendre
        self._derniere: datetime | None = None

    def lister(self, entite: str, parametres: Mapping[str, str]) -> list[dict]:
        """Tous les enregistrements de `/v1/<entite>/` pour ces paramètres, page après page. Chaque paramètre n'y
        figure qu'une fois (un dictionnaire ne peut pas en répéter)."""
        enregistrements: list[dict] = []
        while True:
            page = self._get(
                f"{API}/{entite}/",
                {**parametres, "client": "vigie-vaud", "offset": str(len(enregistrements)), "limit": str(TAILLE_PAGE)},
            )
            donnees = page.get("data")
            if not isinstance(donnees, list):
                raise ValueError(f"{entite} : réponse sans `data`")
            enregistrements.extend(donnees)
            if not page.get("meta", {}).get("has_more") or not donnees:
                return enregistrements

    def _get(self, url: str, parametres: dict[str, str]) -> dict:
        if self._derniere is not None:
            ecart = (self._horloge() - self._derniere).total_seconds()
            if ecart < INTERVALLE:
                self._attendre(INTERVALLE - ecart)
        self._derniere = self._horloge()
        reponse = self._http.get(url, params=parametres, headers={"User-Agent": USER_AGENT}, timeout=120)
        reponse.raise_for_status()
        return reponse.json()


@dataclass
class Bruts:
    """Ce qu'OpenParlData a renvoyé pour un conseil : ses Objets et ses Séances, relations développées."""

    conseil: Conseil
    objets: list[dict] = field(default_factory=list)
    seances: list[dict] = field(default_factory=list)


def parametres_objets(conseil: Conseil, depuis: date | None) -> dict[str, str]:
    p = {
        "body_key": conseil.body_key,
        "expand": "contributors,events,docs",
        "fields": CHAMPS_OBJETS,
        "sort_by": "id",
        "contributors_limit": str(TAILLE_RELATION),
        "events_limit": str(TAILLE_RELATION),
        "docs_limit": str(TAILLE_RELATION),
    }
    return p | ({"from_updated_at": depuis.isoformat()} if depuis else {})


def parametres_seances(conseil: Conseil, depuis: date | None) -> dict[str, str]:
    p = {
        "body_key": conseil.body_key,
        "expand": "agendas",
        "fields": CHAMPS_SEANCES,
        "sort_by": "id",
        "agendas_limit": str(TAILLE_RELATION),
    }
    if conseil.groupe is not None:
        p["group_id"] = str(conseil.groupe)
    return p | ({"from_updated_at": depuis.isoformat()} if depuis else {})


def importer(opd: OpenParlData, conseil: Conseil, depuis: date | None) -> Bruts:
    """Les Objets et les Séances du conseil modifiés depuis le jour `depuis` (tout l'historique sans `depuis`).
    Les Séances d'un autre groupe que `conseil.groupe` (le Conseil d'État dans le body `VD`) sont écartées."""
    bruts = Bruts(conseil)
    if "objets" in conseil.donne:
        bruts.objets = opd.lister("affairs", parametres_objets(conseil, depuis))
        for objet in bruts.objets:
            _verifier_relations(objet, ("contributors", "events", "docs"))
    if "seances" in conseil.donne:
        seances = opd.lister("meetings", parametres_seances(conseil, depuis))
        bruts.seances = [s for s in seances if conseil.groupe is None or s.get("group_id") == conseil.groupe]
        for seance in bruts.seances:
            _verifier_relations(seance, ("agendas",))
    return bruts


def _verifier_relations(enregistrement: dict, relations: Iterable[str]) -> None:
    for relation in relations:
        meta = (enregistrement.get(relation) or {}).get("meta") or {}
        if meta.get("has_more"):
            identifiant = enregistrement.get("id")
            raise ValueError(f"{relation} de {identifiant} au-delà de {TAILLE_RELATION} : relation tronquée")


# --- 2. Normalisation ------------------------------------------------------------------------------------------

Element = Objet | Seance
Archive = Mapping[str, Element]


def cle_conseil(conseil: Conseil) -> str:
    return conseil.body_key.lower()


def cle_objet(conseil: str, numero: str) -> str:
    """`vd/26_INT_140`, `5586/POS25-115` : la barre oblique du numéro devient `-`, et un espace `_`
    (`V 1.9.2026`, au Grand Conseil, donne `vd/V_1.9.2026`)."""
    nom = re.sub(r"\s+", "_", numero.strip()).replace("/", "-")
    return f"{conseil}/{nom}"


def chemin_element(cle: str, element: Element) -> str:
    conseil, nom = cle.split("/", 1)
    dossier = "objets" if isinstance(element, Objet) else "seances"
    return f"conseils/{conseil}/{dossier}/{nom}.json"


def vers_archive(bruts: Bruts, archive: Archive, genere: datetime) -> dict[str, Element]:
    """Les éléments de l'archive tirés de `bruts`, par clé. `archive` (les éléments déjà archivés) sert à résoudre
    l'Objet de chaque point d'ordre du jour et à départager deux Objets de même numéro (il y en a à Lausanne) : le
    plus petit identifiant l'emporte, d'un import à l'autre. Les demandes de grâce sont écartées."""
    conseil = cle_conseil(bruts.conseil)
    elements: dict[str, Element] = {}
    for brut in sorted(bruts.objets, key=lambda o: o["id"]):
        if _fr(brut.get("type_name")) in TYPES_ECARTES or not brut.get("number"):
            continue
        cle = cle_objet(conseil, brut["number"])
        deja = elements.get(cle) or archive.get(cle)
        if isinstance(deja, Objet) and deja.id < brut["id"]:
            continue
        elements[cle] = _objet(brut, genere)

    connus = {**archive, **elements}
    par_id = {e.id: cle for cle, e in connus.items() if isinstance(e, Objet) and cle.startswith(conseil + "/")}
    for brut in sorted(bruts.seances, key=lambda s: s["id"]):
        seance = _seance(brut, genere, lambda p: _objet_du_point(p, conseil, connus, par_id))
        if seance is not None:
            elements[f"{conseil}/{seance.date[:10]}"] = seance
    return elements


def _objet(brut: dict, genere: datetime) -> Objet:
    etapes = _etapes(_relation(brut, "events"))
    libelle = _fr(brut.get("state_name"))
    derniere = etapes[-1] if etapes else None
    if libelle:
        statut = Statut(libelle=libelle, date=derniere.date if derniere else None)
    else:
        statut = Statut(libelle=derniere.libelle, date=derniere.date) if derniere else None
    return Objet(
        version=1,
        genere=genere,
        id=brut["id"],
        numero=brut["number"],
        type=_fr(brut.get("type_name")) or "",
        statut=statut,
        depose=_jour(brut.get("begin_date")),
        titre=_fr(brut.get("title")) or "",
        contributeurs=_contributeurs(_relation(brut, "contributors")),
        etapes=etapes,
        documents=_documents(_relation(brut, "docs")),
        lien=_lien(_fr(brut.get("url_external"))),
    )


def _etapes(bruts: list[dict]) -> list[Etape]:
    etapes = []
    for e in sorted(bruts, key=lambda e: e.get("position") or 0):
        jour = _jour(e.get("date"))
        libelle = _fr(e.get("title")) or _fr(e.get("title_harmonized"))
        if jour is not None and libelle:
            etapes.append(Etape(date=jour, libelle=libelle))
    return sorted(etapes, key=lambda e: e.date)


def _contributeurs(bruts: list[dict]) -> list[Contributeur]:
    contributeurs = []
    for c in sorted(bruts, key=lambda c: c.get("position") or 0):
        nom = c.get("fullname") or " ".join(x for x in (c.get("firstname"), c.get("lastname")) if x)
        if nom:
            contributeurs.append(
                Contributeur(
                    nom=nom,
                    parti=_fr(c.get("party")),
                    role=_fr(c.get("role")),
                    sorte="personne" if c.get("type") == "person" else "groupe",
                )
            )
    return contributeurs


def _documents(bruts: list[dict]) -> list[DocumentObjet]:
    documents = []
    for d in bruts:
        lien = _lien(d.get("url"))
        if lien is not None:
            documents.append(
                DocumentObjet(titre=d.get("name") or _fr(d.get("category")), date=_jour(d.get("date")), lien=lien)
            )
    return documents


def _seance(brut: dict, genere: datetime, objet_du_point: Callable[[dict], str | None]) -> Seance | None:
    debut = brut.get("begin_date")
    if not debut:
        return None
    jour, heure = debut[:10], debut[11:16]
    points = sorted(enumerate(_relation(brut, "agendas")), key=lambda ip: (_rang(ip[1]), ip[0]))
    return Seance(
        version=1,
        genere=genere,
        id=brut["id"],
        date=jour if heure in ("", "00:00") else f"{jour}T{heure}",
        nom=_fr(brut.get("name")) or "",
        lien=_lien(_fr(brut.get("url_external"))),
        ordre_du_jour=[
            PointOrdreDuJour(
                numero=p.get("item_number_display") or (str(p["item_number"]) if p.get("item_number") else None),
                titre=p.get("item_title") or "",
                categorie=p.get("item_category"),
                resultat=p.get("item_result"),
                objet=objet_du_point(p),
            )
            for _, p in points
        ],
    )


def _rang(point: dict) -> float:
    if isinstance(point.get("item_number"), int):
        return point["item_number"]
    affiche = point.get("item_number_display") or ""
    return int(affiche) if affiche.isdigit() else float("inf")


def _objet_du_point(point: dict, conseil: str, connus: Archive, par_id: Mapping[int, str]) -> str | None:
    """L'Objet du point, par son `id` (Lausanne) ou par son numéro (Grand Conseil), s'il est connu de l'archive."""
    if point.get("item_affair_id") in par_id:
        return par_id[point["item_affair_id"]]
    if point.get("item_affair_number"):
        cle = cle_objet(conseil, point["item_affair_number"])
        if isinstance(connus.get(cle), Objet):
            return cle
    return None


def _relation(brut: dict, nom: str) -> list[dict]:
    return (brut.get(nom) or {}).get("data") or []


def _fr(valeur: object) -> str | None:
    """Le libellé français d'un champ imbriqué (`{"fr": …}`) ou à plat ; `None` s'il est absent ou vide."""
    if isinstance(valeur, dict):
        valeur = valeur.get("fr")
    if isinstance(valeur, str) and valeur.strip():
        return valeur.strip()
    return None


def _jour(valeur: object) -> date | None:
    if isinstance(valeur, str) and len(valeur) >= 10:
        try:
            return date.fromisoformat(valeur[:10])
        except ValueError:
            return None
    return None


def _lien(valeur: str | None) -> str | None:
    """Un lien http(s) sans espace (les espaces sont encodés), ou `None`."""
    if not valeur:
        return None
    valeur = quote(valeur.strip(), safe=":/?#[]@!$&'()*+,;=%~")
    return valeur if valeur.startswith(("http://", "https://")) else None


# --- 3. Fichiers de lecture ------------------------------------------------------------------------------------


def lecture(archive: Archive) -> dict[str, Enveloppe]:
    """Les fichiers de lecture reconstruits depuis l'archive, par chemin. Aucun pour l'instant (ticket #65)."""
    return {}


# --- 4. Écriture -----------------------------------------------------------------------------------------------


def ecrire(depot: Path, documents: Mapping[str, Enveloppe], genere: datetime) -> list[str]:
    """Écrit chaque document dont le contenu, `genere` mis à part, diffère du fichier en place ; son `genere` est
    alors celui du passage. Ne supprime rien. Renvoie les chemins écrits."""
    ecrits = []
    for chemin, document in sorted(documents.items()):
        fichier = depot / chemin
        nouveau = document.model_dump(mode="json")
        nouveau.pop("genere")
        try:
            ancien = json.loads(fichier.read_text(encoding="utf-8"))
            ancien.pop("genere", None)
        except (FileNotFoundError, ValueError):
            ancien = None
        if ancien == nouveau:
            continue
        fichier.parent.mkdir(parents=True, exist_ok=True)
        texte = document.model_copy(update={"genere": genere}).model_dump_json(indent=2)
        fichier.write_text(texte + "\n", encoding="utf-8")
        ecrits.append(chemin)
    return ecrits


# --- Le passage ------------------------------------------------------------------------------------------------


def lire_archive(depot: Path) -> dict[str, Element]:
    archive: dict[str, Element] = {}
    for dossier, modele in (("objets", Objet), ("seances", Seance)):
        for fichier in sorted(depot.glob(f"conseils/*/{dossier}/*.json")):
            archive[f"{fichier.parent.parent.name}/{fichier.stem}"] = modele.model_validate_json(fichier.read_bytes())
    return archive


def _lire_imports(depot: Path) -> dict[str, datetime]:
    try:
        return dict(ImportConseils.model_validate_json((depot / FICHIER_IMPORT).read_bytes()).conseils)
    except (FileNotFoundError, ValidationError):
        return {}


def importer_conseils(
    depot: Path,
    sources: FichierSources,
    opd: OpenParlData,
    horloge: Callable[[], datetime],
    depuis: date | None = None,
) -> ImportConseils:
    """Importe chaque conseil déclaré dans `sources` dans `depot`, un clone du dépôt de données. Chaque conseil
    repart du jour de son dernier import réussi moins un jour de recouvrement (`depuis` l'impose à tous), ou de
    tout l'historique s'il n'a jamais été importé. Un conseil en échec est signalé, garde sa date, et les autres
    continuent. Le commit et le push sont l'affaire de l'appelant."""
    genere = horloge().astimezone(UTC).replace(microsecond=0)
    imports = _lire_imports(depot)
    archive = lire_archive(depot)
    nouveaux: dict[str, Element] = {}
    for source in sources.sources:
        if source.conseil is None:
            continue
        cle = cle_conseil(source.conseil)
        debut = depuis or (imports[cle].date() - RECOUVREMENT if cle in imports else None)
        try:
            bruts = importer(opd, source.conseil, debut)
            elements = vers_archive(bruts, archive, genere)
        except (httpx.HTTPError, ValueError) as e:
            print(f"Import en échec : {source.nom} ({e})", file=sys.stderr)
            continue
        nouveaux |= elements
        archive = {**archive, **elements}
        imports[cle] = genere
        print(f"{source.nom} : {len(bruts.objets)} Objet(s), {len(bruts.seances)} Séance(s) lus")

    etat = ImportConseils(version=1, genere=genere, conseils=imports)
    documents: dict[str, Enveloppe] = {chemin_element(cle, e): e for cle, e in nouveaux.items()}
    documents |= lecture(archive)
    documents[FICHIER_IMPORT] = etat
    ecrire(depot, documents, genere)
    return etat


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Importe les conseils dans un clone du dépôt de données, sans push.")
    parser.add_argument("--depot", type=Path, required=True, help="clone local du dépôt de données")
    parser.add_argument("--sources", type=Path, default=RACINE / "sources.json", help="déclaration des sources")
    parser.add_argument("--depuis", type=date.fromisoformat, help="jour de départ imposé à tous les conseils")
    args = parser.parse_args(argv)

    horloge = lambda: datetime.now(UTC)  # noqa: E731
    with httpx.Client() as http:
        opd = OpenParlData(http, horloge)
        importer_conseils(args.depot.resolve(), lire_sources(args.sources), opd, horloge, args.depuis)


if __name__ == "__main__":
    main()
