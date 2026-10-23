"""Import des conseils (ADR 0010, 0015 et 0017) : les Objets et les Séances d'OpenParlData et des sites des
communes dans l'archive du dépôt de données, un fichier par élément.

Le passage suit quatre étapes, chacune à sa place :

1. `importer(opd, conseil, depuis)` lit les changements bruts d'un conseil chez OpenParlData, et pour le Grand
   Conseil les Objets dont un document a changé depuis ; pour une source communale (bloc `site`),
   `sites_communaux.lire_site` lit le site de la commune par le robot communal et rend les mêmes `Bruts` ;
2. `vers_archive(bruts, archive, genere, communes, corrections)`, fonction pure, les masque (`masquage.py`,
   ADR 0007), rattache les Objets du Grand Conseil aux communes qu'ils nomment (`rattachement.py`, ADR 0016) et les
   normalise en Objets et Séances de l'archive ;
3. `lecture(archive, sources, genere)`, fonction pure, reconstruit les fichiers de lecture que le site liste
   (`lecture_conseils.py`) ;
4. `ecrire(depot, documents, genere)` compare chaque fichier à l'ancien sans `genere` et n'écrit que ce qui change ;
   `supprimer_perimes(depot, documents)` retire les fichiers de lecture que `lecture` ne produit plus.

`importer_conseils` enchaîne les quatre pour chaque source qui a un bloc `conseil`, et tient à jour
`conseils/import.json` (dernier import réussi de chaque conseil) et, pour un conseil scrapé,
`conseils/<ofs>/membres.json` (ses élu·e·s connu·e·s, une liste qui ne fait que s'allonger). Un conseil en échec
garde sa date et n'empêche pas les autres. L'import ne supprime rien de l'archive : un élément absent d'OpenParlData
y reste. Les fichiers de lecture, eux, sont reconstruits en entier et ne divergent jamais de l'archive.

Usage loyal d'OpenParlData : au plus une requête par seconde, un User-Agent avec un contact, la pagination suivie
jusqu'au bout, et jamais un paramètre répété dans une requête (le cache du serveur ne garde que sa dernière valeur).

En local, contre un clone du dépôt de données (depuis `pipeline/`), sans rien pousser :

    uv run python conseils.py --depot ../../vigie-vaud-donnees --depuis 2026-10-10

Sans `--depuis`, chaque conseil repart du jour de son dernier import réussi, ou de tout l'historique s'il n'a
jamais été importé. `--reconstruire` refait seulement les fichiers de lecture depuis l'archive (après un changement
de leur forme ou une réécriture à la main de l'archive), sans aucune requête à OpenParlData :

    uv run python conseils.py --depot ../../vigie-vaud-donnees --reconstruire
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from collections.abc import Callable, Collection, Iterable, Mapping
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from bruts import Bruts
from lecture_conseils import MOTIFS_LECTURE, lecture
from masquage import TYPES_SANS_AUTEUR, elus_connus, est_point_de_grace, masquer
from rattachement import (
    COMMUNES_JSON,
    Repertoire,
    corriger,
    corriger_archive,
    lire_corrections,
    porte_sur_le_canton,
    rattacher_objet,
)
from robot_communal import Robot, robot_des_sources
from schema import (
    RACINE,
    Conseil,
    Contributeur,
    Correction,
    DocumentObjet,
    Enveloppe,
    Etape,
    FichierSources,
    ImportConseils,
    MembresConseil,
    Objet,
    PointOrdreDuJour,
    Seance,
    Statut,
    lire_sources,
)
from sites_communaux import lire_site

API ="https://api.openparldata.ch/v1"
_CONFIG = json.loads((RACINE / "config.json").read_text())
USER_AGENT = f"VigieVaud-import (+{_CONFIG['depot']}; {_CONFIG['courriel']})"
INTERVALLE = 1.0  # secondes, au moins, entre deux requêtes
TAILLE_PAGE = 200
# Plafond de chaque relation développée (`expand`) : au-delà, l'import du conseil échoue plutôt que de tronquer.
TAILLE_RELATION = 1000
RECOUVREMENT = timedelta(days=1)
PAR_IDENTIFIANTS = 50  # Objets relus par requête (`id=1,2,…`) pour leurs documents tardifs
FICHIER_IMPORT = "conseils/import.json"
FUSEAU = ZoneInfo("Europe/Zurich")  # le jour du passage, d'où part la fenêtre d'un site, est celui de Lausanne

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


def parametres_objets(conseil: Conseil, depuis: date | None) -> dict[str, str]:
    p = {
        "body_key": conseil.body_key,
        "expand": "contributors,events,docs",
        # Le texte des documents ne sert qu'au rattachement par le nom : téléchargé, jamais conservé.
        "fields": CHAMPS_OBJETS + (",docs.text" if porte_sur_le_canton(conseil) else ""),
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
        if depuis is not None and porte_sur_le_canton(conseil):
            bruts.objets += _objets_aux_documents_tardifs(opd, conseil, depuis, {o["id"] for o in bruts.objets})
        for objet in bruts.objets:
            _verifier_relations(objet, ("contributors", "events", "docs"))
    if "seances" in conseil.donne:
        seances = opd.lister("meetings", parametres_seances(conseil, depuis))
        bruts.seances = [s for s in seances if conseil.groupe is None or s.get("group_id") == conseil.groupe]
        for seance in bruts.seances:
            _verifier_relations(seance, ("agendas",))
    return bruts


def _objets_aux_documents_tardifs(opd: OpenParlData, conseil: Conseil, depuis: date, lus: set[int]) -> list[dict]:
    """Les Objets dont un document a changé depuis `depuis` sans que l'Objet lui-même change (un document arrive
    souvent après l'Objet), relus en entier pour recalculer leur rattachement. `lus` : les Objets déjà relus."""
    documents = opd.lister(
        "docs",
        {
            "body_key": conseil.body_key,
            "parent_type": "affair",
            "fields": "id,affair_id",
            "sort_by": "id",
            "from_updated_at": depuis.isoformat(),
        },
    )
    ids = sorted({d["affair_id"] for d in documents if isinstance(d.get("affair_id"), int)} - lus)
    objets = []
    for i in range(0, len(ids), PAR_IDENTIFIANTS):
        par_id = ",".join(str(x) for x in ids[i : i + PAR_IDENTIFIANTS])
        objets += opd.lister("affairs", parametres_objets(conseil, None) | {"id": par_id})
    return objets


def _verifier_relations(enregistrement: dict, relations: Iterable[str]) -> None:
    for relation in relations:
        meta = (enregistrement.get(relation) or {}).get("meta") or {}
        if meta.get("has_more"):
            identifiant = enregistrement.get("id")
            raise ValueError(f"{relation} de {identifiant} au-delà de {TAILLE_RELATION} : relation tronquée")


# --- 2. Normalisation ------------------------------------------------------------------------------------------

Element = Objet | Seance
Archive = Mapping[str, Element]


def cle_objet(conseil: str, numero: str) -> str:
    """`vd/26_INT_140`, `5586/POS25-115` : la barre oblique du numéro devient `-`, et un espace `_`
    (`V 1.9.2026`, au Grand Conseil, donne `vd/V_1.9.2026`)."""
    nom = re.sub(r"\s+", "_", numero.strip()).replace("/", "-")
    return f"{conseil}/{nom}"


def chemin_element(cle: str, element: Element) -> str:
    conseil, nom = cle.split("/", 1)
    dossier = "objets" if isinstance(element, Objet) else "seances"
    return f"conseils/{conseil}/{dossier}/{nom}.json"


def vers_archive(
    bruts: Bruts,
    archive: Archive,
    genere: datetime,
    communes: Repertoire | None = None,
    corrections: Mapping[str, Correction] | None = None,
    membres: Iterable[str] = (),
) -> dict[str, Element]:
    """Les éléments de l'archive tirés de `bruts`, par clé. `archive` (les éléments déjà archivés) sert à résoudre
    l'Objet de chaque point d'ordre du jour et à départager deux Objets de même numéro (il y en a à Lausanne) : le
    plus petit identifiant l'emporte, d'un import à l'autre (entre deux identifiants connus : un élément scrapé n'en a
    pas, et son `id` est nul). Deux Séances d'un même jour n'en font qu'une (`_fusionner`). Les demandes de grâce
    sont écartées, et leurs points d'ordre du jour retirés. Les titres des Objets, de leurs documents, des points et
    des documents des Séances sont masqués (ADR 0007), en
    épargnant les élu·e·s connu·e·s du conseil : les contributeur·rice·s de ses Objets (`archive` et `bruts`), les
    `membres` déjà connus d'un conseil scrapé (`membres.json`) et ceux de sa page des membres (`bruts.membres`). Les
    pétitionnaires que la source connaît le sont dans les textes de leur pétition : son titre, ceux de ses documents
    (et du même document joint à un autre Objet) et ceux de ses points.

    Pour un conseil qui porte sur le canton, chaque Objet est rattaché par le nom (ADR 0016) d'après `communes`
    (`communes.json` par défaut) : son titre masqué, puis le texte de ses documents, qui n'est pas conservé ;
    `corrections` (par clé d'Objet) l'emporte, et s'applique aussi aux Objets déjà archivés."""
    conseil = bruts.conseil.cle
    canton = porte_sur_le_canton(bruts.conseil)
    corrections = corrections or {}
    elements: dict[str, Element] = {}
    textes: dict[str, list[str]] = {}
    petitionnaires: dict[str, list[tuple[str, str]]] = {}
    graces: set[str] = set()
    # Par identifiant croissant ; ceux qui n'en ont pas (scrapés) après, dans l'ordre de la source.
    for brut in sorted(bruts.objets, key=lambda o: (o.get("id") is None, o.get("id") or 0)):
        if _fr(brut.get("type_name")) in TYPES_ECARTES or not brut.get("number"):
            if brut.get("number"):
                graces.add(brut["number"])
            continue
        cle = cle_objet(conseil, brut["number"])
        ident = brut.get("id")
        # Deux Objets de même numéro : le plus petit identifiant l'emporte, d'un import à l'autre, mais seulement
        # entre deux identifiants connus. Sans identifiant, le premier de la source l'emporte sur les suivants du
        # même import, et un Objet relu remplace celui de l'archive.
        if cle in elements and (elements[cle].id is None or ident is None):
            continue
        deja = elements.get(cle) or archive.get(cle)
        if isinstance(deja, Objet) and deja.id is not None and ident is not None and deja.id < ident:
            continue
        elements[cle] = _objet(brut, genere)
        textes[cle] = [d["text"] for d in _relation(brut, "docs") if isinstance(d.get("text"), str)]
        petitionnaires[cle] = _petitionnaires(brut) if elements[cle].type in TYPES_SANS_AUTEUR else []

    connus = {**archive, **elements}
    du_conseil = {cle: e for cle, e in connus.items() if isinstance(e, Objet) and cle.startswith(conseil + "/")}
    elus = elus_connus(du_conseil.values()) | frozenset(membres) | frozenset(bruts.membres)
    # Un document qui répond à la fois à une pétition et à un autre Objet est joint aux deux, sous le même titre.
    petitionnaires_du_document: dict[str, list[tuple[str, str]]] = {}
    for cle, objet in elements.items():
        for d in objet.documents:
            if d.titre and petitionnaires[cle]:
                petitionnaires_du_document.setdefault(d.titre, []).extend(petitionnaires[cle])
    for cle, objet in elements.items():
        titre = masquer(objet.titre, elus, petitionnaires[cle])
        documents = [
            d.model_copy(update={"titre": masquer(d.titre, elus, petitionnaires_du_document.get(d.titre, []))})
            if d.titre
            else d
            for d in objet.documents
        ]
        rattachees = corriger(rattacher_objet(titre, textes[cle], communes), corrections.get(cle)) if canton else []
        elements[cle] = objet.model_copy(update={"titre": titre, "documents": documents, "communes": rattachees})
    if canton:
        anciens = {cle: o for cle, o in du_conseil.items() if cle not in elements}
        elements |= corriger_archive(anciens, corrections)

    par_id = {e.id: cle for cle, e in du_conseil.items() if e.id is not None}
    seances: dict[str, Seance] = {}
    # Dans l'ordre de leur heure, puis de la source : deux Séances d'un même jour n'en font qu'une, la première.
    for brut in sorted(bruts.seances, key=lambda s: s.get("begin_date") or ""):
        points = [
            p
            for p in _relation(brut, "agendas")
            if not est_point_de_grace(p.get("item_title") or "", p.get("item_affair_number"), graces)
        ]
        brut = {**brut, "agendas": {"data": points}}
        seance = _seance(brut, genere, lambda p: _objet_du_point(p, conseil, connus, par_id), elus, petitionnaires)
        if seance is not None:
            cle = f"{conseil}/{seance.date[:10]}"
            seances[cle] = _fusionner(seances[cle], seance) if cle in seances else seance
    return elements | seances


def _fusionner(premiere: Seance, seconde: Seance) -> Seance:
    """Une seule Séance pour deux d'un même jour : l'identifiant, l'heure et le nom de la première, ses points puis
    ceux de la seconde, et leurs documents réunis (un même lien n'y est qu'une fois)."""
    liens = {d.lien for d in premiere.documents}
    return premiere.model_copy(
        update={
            "lien": premiere.lien or seconde.lien,
            "ordre_du_jour": premiere.ordre_du_jour + seconde.ordre_du_jour,
            "documents": premiere.documents + [d for d in seconde.documents if d.lien not in liens],
        }
    )


def _objet(brut: dict, genere: datetime) -> Objet:
    etapes = _etapes(_relation(brut, "events"))
    type_ = _fr(brut.get("type_name")) or ""
    libelle = _fr(brut.get("state_name"))
    derniere = etapes[-1] if etapes else None
    if libelle:
        statut = Statut(libelle=libelle, date=derniere.date if derniere else None)
    else:
        statut = Statut(libelle=derniere.libelle, date=derniere.date) if derniere else None
    return Objet(
        version=1,
        genere=genere,
        id=brut.get("id"),
        numero=brut["number"],
        type=type_,
        statut=statut,
        depose=_jour(brut.get("begin_date")),
        titre=_fr(brut.get("title")) or "",
        contributeurs=[] if type_ in TYPES_SANS_AUTEUR else _contributeurs(_relation(brut, "contributors")),
        etapes=etapes,
        documents=_documents(_relation(brut, "docs")),
        lien=_lien(_fr(brut.get("url_external"))),
        communes=[],  # rattachées par `vers_archive`, après le masquage du titre
    )


def _etapes(bruts: list[dict]) -> list[Etape]:
    etapes = []
    for e in sorted(bruts, key=lambda e: e.get("position") or 0):
        jour = _jour(e.get("date"))
        libelle = _fr(e.get("title")) or _fr(e.get("title_harmonized"))
        if jour is not None and libelle:
            etapes.append(Etape(date=jour, libelle=libelle))
    return sorted(etapes, key=lambda e: e.date)


def _petitionnaires(brut: dict) -> list[tuple[str, str]]:
    """Les pétitionnaires (prénom, nom de famille) qu'OpenParlData donne en contributeurs d'une pétition. Son nom
    complet est parfois celui d'une autre personne, un·e élu·e même : on garde les deux, le nom complet coupé après
    le premier mot (« Prénom Nom », comme Lausanne les donne)."""
    noms = []
    for c in _relation(brut, "contributors"):
        if c.get("type") != "person":
            continue
        prenom, nom, complet = c.get("firstname") or "", c.get("lastname") or "", c.get("fullname") or ""
        if nom:
            noms.append((prenom, nom))
        if complet and complet.split() != f"{prenom} {nom}".split():
            premier, _, reste = complet.strip().partition(" ")
            noms.append((premier, reste) if reste else ("", premier))
    return noms


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


def _seance(
    brut: dict,
    genere: datetime,
    objet_du_point: Callable[[dict], str | None],
    elus: frozenset[str],
    petitionnaires: Mapping[str, list[tuple[str, str]]],
) -> Seance | None:
    debut = brut.get("begin_date")
    if not debut:
        return None
    jour, heure = debut[:10], debut[11:16]
    points = sorted(enumerate(_relation(brut, "agendas")), key=lambda ip: (_rang(ip[1]), ip[0]))
    return Seance(
        version=1,
        genere=genere,
        id=brut.get("id"),
        date=jour if heure in ("", "00:00") else f"{jour}T{heure}",
        nom=_fr(brut.get("name")) or "",
        lien=_lien(_fr(brut.get("url_external"))),
        ordre_du_jour=[_point(p, objet_du_point(p), elus, petitionnaires) for _, p in points],
        documents=[
            d.model_copy(update={"titre": masquer(d.titre, elus)}) if d.titre else d
            for d in _documents(_relation(brut, "docs"))
        ],
    )


def _point(
    brut: dict, objet: str | None, elus: frozenset[str], petitionnaires: Mapping[str, list[tuple[str, str]]]
) -> PointOrdreDuJour:
    return PointOrdreDuJour(
        numero=brut.get("item_number_display") or (str(brut["item_number"]) if brut.get("item_number") else None),
        titre=masquer(brut.get("item_title") or "", elus, petitionnaires.get(objet or "", [])),
        categorie=brut.get("item_category"),
        resultat=brut.get("item_result"),
        objet=objet,
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


# --- 4. Écriture -----------------------------------------------------------------------------------------------


def ecrire(depot: Path, documents: Mapping[str, Enveloppe], genere: datetime) -> list[str]:
    """Écrit chaque document dont le contenu, `genere` mis à part, diffère du fichier en place ; son `genere` est
    alors celui du passage. Ne supprime rien (`supprimer_perimes`). Renvoie les chemins écrits."""
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


def supprimer_perimes(depot: Path, documents: Mapping[str, Enveloppe]) -> list[str]:
    """Supprime les fichiers de lecture en place (`MOTIFS_LECTURE`) qui ne sont pas dans `documents`, la lecture
    complète de l'archive : une commune qui n'a plus d'Objet rattaché, un conseil retiré de `sources.json`. Aucun
    fichier d'archive n'est supprimé. Renvoie les chemins supprimés."""
    supprimes = []
    for motif in MOTIFS_LECTURE:
        for fichier in sorted(depot.glob(motif)):
            chemin = fichier.relative_to(depot).as_posix()
            if chemin not in documents:
                fichier.unlink()
                supprimes.append(chemin)
    return supprimes


# --- Le passage ------------------------------------------------------------------------------------------------


def lire_archive(depot: Path) -> dict[str, Element]:
    archive: dict[str, Element] = {}
    for dossier, modele in (("objets", Objet), ("seances", Seance)):
        for fichier in sorted(depot.glob(f"conseils/*/{dossier}/*.json")):
            archive[f"{fichier.parent.parent.name}/{fichier.stem}"] = modele.model_validate_json(fichier.read_bytes())
    return archive


def chemin_membres(conseil: str) -> str:
    return f"conseils/{conseil}/membres.json"


def lire_membres(depot: Path, conseil: str) -> list[str]:
    """Les élu·e·s connu·e·s d'un conseil scrapé, lu·e·s dans son `membres.json` (aucun s'il manque)."""
    try:
        return MembresConseil.model_validate_json((depot / chemin_membres(conseil)).read_bytes()).membres
    except FileNotFoundError:
        return []


def reunir_membres(*listes: Iterable[str]) -> list[str]:
    """Les noms de toutes les `listes`, chacun une fois (espaces resserrés), triés sans tenir compte des accents ni
    de la casse."""
    noms = {" ".join(nom.split()) for liste in listes for nom in liste} - {""}

    def plier(nom: str) -> str:
        decompose = unicodedata.normalize("NFKD", nom)
        return "".join(c for c in decompose if not unicodedata.combining(c)).casefold()

    return sorted(noms, key=lambda nom: (plier(nom), nom))


def _lire_import(depot: Path) -> ImportConseils | None:
    try:
        return ImportConseils.model_validate_json((depot / FICHIER_IMPORT).read_bytes())
    except (FileNotFoundError, ValidationError):
        return None


def lire_imports(depot: Path) -> dict[str, datetime]:
    """Le dernier import réussi de chaque conseil, par clé, lu dans `conseils/import.json` (vide s'il manque)."""
    lu = _lire_import(depot)
    return dict(lu.conseils) if lu else {}


def lire_premiers_imports(depot: Path) -> dict[str, datetime]:
    """Le premier import réussi de chaque conseil scrapé, par clé, lu dans `conseils/import.json` (vide s'il
    manque)."""
    lu = _lire_import(depot)
    return dict(lu.premiers) if lu else {}


def lire_rattrapages(depot: Path) -> dict[str, datetime]:
    """Le dernier rattrapage réussi de chaque conseil, par clé, lu dans `conseils/import.json` (vide s'il manque)."""
    lu = _lire_import(depot)
    return dict(lu.rattrapages) if lu else {}


def importer_conseils(
    depot: Path,
    sources: FichierSources,
    opd: OpenParlData,
    horloge: Callable[[], datetime],
    depuis: date | None = None,
    *,
    dus: Collection[str] | None = None,
    rattrapage: bool = False,
    communes: Path = COMMUNES_JSON,
    robot: Robot | None = None,
) -> ImportConseils:
    """Importe chaque conseil déclaré dans `sources` dans `depot`, un clone du dépôt de données, ou seulement ceux
    dont la clé est dans `dus`. Un conseil d'OpenParlData repart du jour de son dernier import réussi moins un jour
    de recouvrement (`depuis` l'impose à tous), ou de tout l'historique s'il n'a jamais été importé ou pour un
    `rattrapage`. Un conseil dont la source a un bloc `site` est lu sur le site de sa commune par `robot`
    (`lire_site`), dans la fenêtre du jour à Lausanne, ou en entier pour un `rattrapage`. Un conseil en échec est
    signalé, garde sa date, et les autres continuent ; un `rattrapage` réussi est aussi noté dans `rattrapages`.
    Le commit et le push sont l'affaire de l'appelant.

    Le rattachement par le nom lit `communes` (`communes.json` du site) et `corrections.json` du dépôt ; un
    `corrections.json` invalide lève `pydantic.ValidationError` avant tout import."""
    genere = horloge().astimezone(UTC).replace(microsecond=0)
    jour = genere.astimezone(FUSEAU).date()
    repertoire = Repertoire.lire(communes)
    corrections = lire_corrections(depot)
    imports = lire_imports(depot)
    premiers = lire_premiers_imports(depot)
    rattrapages = lire_rattrapages(depot)
    archive = lire_archive(depot)
    nouveaux: dict[str, Element] = {}
    membres: dict[str, MembresConseil] = {}
    for source in sources.sources:
        if source.conseil is None or (dus is not None and source.conseil.cle not in dus):
            continue
        cle = source.conseil.cle
        if rattrapage:
            debut = None
        else:
            debut = depuis or (imports[cle].date() - RECOUVREMENT if cle in imports else None)
        try:
            if source.site is not None:
                if robot is None:
                    raise ValueError("aucun robot communal pour lire le site de la commune")
                bruts = lire_site(robot, source, sources.plateformes, jour, rattrapage)
            else:
                bruts = importer(opd, source.conseil, debut)
            connus = lire_membres(depot, cle) if source.site is not None else []
            elements = vers_archive(bruts, archive, genere, repertoire, corrections, connus)
        except Exception as e:
            # Toute erreur, prévue (HTTP, relation tronquée) ou non (réponse d'une forme inattendue), ne vaut
            # qu'un échec de ce conseil : les conseils réussis sont tout de même écrits.
            print(f"Import en échec : {source.nom} ({type(e).__name__} : {e})", file=sys.stderr)
            continue
        nouveaux |= elements
        archive = {**archive, **elements}
        if source.site is not None and cle not in imports:
            premiers.setdefault(cle, genere)
        imports[cle] = genere
        if rattrapage:
            rattrapages[cle] = genere
        if source.site is not None:
            # La liste ne fait que s'allonger : les noms déjà connus, ceux de la page, les auteur·e·s des Objets.
            objets = [e for k, e in archive.items() if isinstance(e, Objet) and k.startswith(cle + "/")]
            noms = reunir_membres(connus, bruts.membres, elus_connus(objets))
            membres[cle] = MembresConseil(version=1, genere=genere, conseil=cle, membres=noms)
        print(f"{source.nom} : {len(bruts.objets)} Objet(s), {len(bruts.seances)} Séance(s) lus")

    etat = ImportConseils(version=1, genere=genere, conseils=imports, premiers=premiers, rattrapages=rattrapages)
    documents: dict[str, Enveloppe] = {chemin_element(cle, e): e for cle, e in nouveaux.items()}
    documents |= {chemin_membres(cle): liste for cle, liste in membres.items()}
    documents |= lecture(archive, sources, genere)
    documents[FICHIER_IMPORT] = etat
    ecrire(depot, documents, genere)
    supprimer_perimes(depot, documents)
    return etat


def reconstruire(depot: Path, sources: FichierSources, horloge: Callable[[], datetime]) -> list[str]:
    """Reconstruit les fichiers de lecture des conseils de `sources` depuis l'archive de `depot`, sans rien
    importer : ni requête à OpenParlData, ni changement de l'archive ou de `conseils/import.json`. Renvoie les
    chemins écrits ou supprimés."""
    genere = horloge().astimezone(UTC).replace(microsecond=0)
    documents = lecture(lire_archive(depot), sources, genere)
    return ecrire(depot, documents, genere) + supprimer_perimes(depot, documents)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Importe les conseils dans un clone du dépôt de données, sans push.")
    parser.add_argument("--depot", type=Path, required=True, help="clone local du dépôt de données")
    parser.add_argument("--sources", type=Path, default=RACINE / "sources.json", help="déclaration des sources")
    parser.add_argument("--depuis", type=date.fromisoformat, help="jour de départ imposé à tous les conseils")
    parser.add_argument(
        "--reconstruire", action="store_true", help="refaire les fichiers de lecture depuis l'archive, sans import"
    )
    args = parser.parse_args(argv)

    horloge = lambda: datetime.now(UTC)  # noqa: E731
    if args.reconstruire:
        changes = reconstruire(args.depot.resolve(), lire_sources(args.sources), horloge)
        print(f"Fichiers de lecture reconstruits : {len(changes)} écrit(s) ou supprimé(s)")
        return
    sources = lire_sources(args.sources)
    with httpx.Client() as http:
        opd = OpenParlData(http, horloge)
        # Un import lancé à la main est un passage ordinaire : réseaux ralentis et plafond de 60 requêtes par commune.
        robot = robot_des_sources(http, sources, horloge)
        importer_conseils(args.depot.resolve(), sources, opd, horloge, args.depuis, robot=robot)


if __name__ == "__main__":
    main()
