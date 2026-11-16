"""Module de lecture de la plateforme i-web (ADR 0010) : une seule opération publique pour l'import, `lire`, qui lit
le conseil d'une commune i-web par le robot communal et rend ses `Bruts`, à la forme d'OpenParlData ; et, pour le
script de préparation des sources seulement, `mesurer` et `requetes` (`mesure_sites.py`).

Une seule variante, **Séances** (module Séances d'i-web, niveau « séances seulement ») : la page de liste
(`site.seances`) porte deux tableaux, les Séances à venir (`icmsTableFutureSitzungen`) et passées
(`icmsTablePastSitzungen`), dont les lignes sont en JSON échappé dans l'attribut `data-entities` ; chaque ligne donne
le nom de la Séance, son lien `/_rte/anlass/<id>` et sa date (« 10.09.2026, 20h00 - 22h00 »). La page de chaque Séance de la fenêtre est ouverte par ce lien stable, que le site
redirige vers `/seances/<id>` ou `/sitzung/<id>` : elle donne ses documents (liens `/_doc/<id>`, nommés par le texte
du lien) et, quand le site les publie en HTML, les points de son ordre du jour (`tr#traktanden_<n>` : numéro, titre).

Une Séance scrapée n'a pas d'identifiant (`id` nul) : son lien est le lien stable, sa date celle de la liste, telle
quelle, même fictive. Une ligne sans lien ou sans date lisible, ou une Séance dont la page n'a pas pu être lue, est
sautée et notée dans le journal ; une liste dont aucune ligne ne se lit, ou sans ses tableaux, lève `ValueError`.

**Dates** : celle que la liste des Séances donne. L'ADR-0010 prend sinon la mise en ligne du premier document, mais
i-web ne l'affiche nulle part de ce que le robot lit (un document n'y porte que son type et sa taille, et le robot ne
l'ouvre pas). Tous les documents de la page d'une Séance, ceux de ses points compris, sont à la Séance : la variante
Séances ne lit pas d'Objets (ADR-0010).

**Membres** : la page des membres (`site.membres`, facultative) porte le tableau `icmsTable-personList`, en JSON
échappé dans `data-entities` comme les Séances ; la colonne `_nameVorname` donne « Nom Prénom », remis en « Prénom
Nom » (ordre des contributeurs d'OpenParlData, que le masquage attend). Une page des membres illisible est notée dans
le journal et ne donne personne : l'import continue.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin, urlsplit

import socle_lecture
from bruts import Bruts
from pages_html import Noeud, arbre, espaces, texte_html
from mesure_sites import Mesure, PagesLues, RobotSansReseau, liens
from robot_communal import PageNonLue, Robot
from schema import Plateforme, Site, Source
from socle_lecture import (
    DATE_CHIFFRES,
    document,
    heure_de,
    jour_en_chiffres,
    journal,
    meeting,
    point,
)

TABLEAUX_SEANCES = ("icmsTableFutureSitzungen", "icmsTablePastSitzungen")
TABLEAU_MEMBRES = "icmsTable-personList"
VARIANTES = ("seances",)


def lire(robot: Robot, source: Source, depuis: date | None) -> Bruts:
    """Le conseil de `source`, une commune i-web, lu sur son site : les Séances de la liste datées de `depuis` ou
    après (toutes sans `depuis`), chacune avec sa page."""
    site, conseil = socle_lecture.site_et_conseil(source, "i-web", VARIANTES)
    liste = robot.lire(site.seances, "import")
    seances = []
    for ligne in _lignes_de_seances(liste.texte, liste.url):
        if isinstance(ligne, str):
            journal(source.nom, f"ligne de Séance illisible ({ligne})")
            continue
        if depuis is not None and ligne.jour < depuis:
            continue
        try:
            page = robot.lire(ligne.lien, "import")
        except PageNonLue as e:
            journal(source.nom, f"Séance {ligne.lien} non lue ({e})")
            continue
        seances.append(_seance(ligne, page.texte, page.url))
    return Bruts(conseil, objets=[], seances=seances, membres=_membres(robot, source))


# --- Page de liste ------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Ligne:
    nom: str
    lien: str  # lien stable `/_rte/anlass/<id>`, absolu
    jour: date
    heure: str | None  # « 20:00 »


_LIEN_ANLASS = re.compile(r"""href=["']([^"']*/_rte/anlass/\d+)["'][^>]*>(.*?)</a>""", re.S)


def _lignes_de_seances(texte: str, url: str) -> list[_Ligne | str]:
    """Les lignes des deux tableaux de Séances, dans l'ordre du site : chacune lue (`_Ligne`) ou, illisible, la raison
    de son échec."""
    racine = arbre(texte)
    tableaux = [n for n in racine.elements() if n.tag == "table" and n.attr("id") in TABLEAUX_SEANCES]
    if not tableaux:
        raise ValueError(f"{url} : aucun tableau de Séances ({', '.join(TABLEAUX_SEANCES)})")
    lignes: list[_Ligne | str] = []
    for tableau in tableaux:
        try:
            donnees = json.loads(tableau.attr("data-entities") or "")["data"]
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"{url} : `data-entities` illisible dans {tableau.attr('id')}") from e
        lignes += [_ligne(brute, url) for brute in donnees]
    if lignes and all(isinstance(ligne, str) for ligne in lignes):
        raise ValueError(f"{url} : aucune ligne de Séance lisible ({lignes[0]})")
    return lignes


def _ligne(brute: object, url: str) -> _Ligne | str:
    if not isinstance(brute, dict):
        return "ligne sans champs"
    lien = _LIEN_ANLASS.search(str(brute.get("name") or ""))
    if lien is None:
        return "sans lien vers sa page"
    datum = texte_html(str(brute.get("_datum") or ""))
    jour = DATE_CHIFFRES.search(datum)
    if jour is None:
        return f"sans date : {lien[1]}"
    try:
        quand = jour_en_chiffres(jour)
    except ValueError:
        return f"date impossible « {jour[0]} » : {lien[1]}"
    return _Ligne(nom=texte_html(lien[2]), lien=urljoin(url, lien[1]), jour=quand, heure=heure_de(datum[jour.end() :]))


# --- Page d'une Séance --------------------------------------------------------------------------------------------


def _seance(ligne: _Ligne, texte: str, url: str) -> dict:
    """La Séance à la forme d'un *meeting* d'OpenParlData, réduit aux champs que l'import lit : ses points, sans
    Objet relié, et tous les documents de la page (ADR-0010). Un document n'a pas de date : i-web n'en affiche pas,
    ni sa mise en ligne."""
    racine = arbre(texte)
    points = []
    for tr in racine.elements():
        if tr.tag != "tr" or not (tr.attr("id") or "").startswith("traktanden_"):
            continue
        cellules = [c for c in tr.enfants_elements() if c.tag == "td"]
        if len(cellules) < 2:
            continue
        points.append(point(espaces(cellules[1].texte()), numero=espaces(cellules[0].texte())))
    return meeting(ligne.nom, ligne.jour, _documents(racine, url), heure=ligne.heure, lien=ligne.lien, points=points)


def _documents(racine: Noeud, url: str) -> list[dict]:
    """Les documents d'une page (liens `/_doc/<id>`), chacun une fois, nommés par le texte du lien, sinon son titre,
    sinon la fin du lien."""
    documents, vus = [], set()
    for a in racine.elements():
        lien = urljoin(url, a.attr("href") or "") if a.tag == "a" else ""
        if "/_doc/" not in lien or lien in vus:
            continue
        vus.add(lien)
        nom = espaces(a.texte()) or a.attr("title") or lien.rsplit("/", 1)[-1]
        documents.append(document(nom, lien))
    return documents


# --- Page des membres ---------------------------------------------------------------------------------------------


def _prenom_nom(nom: str) -> str:
    """« Krebs Yann », comme i-web nomme une personne, devient « Yann Krebs », l'ordre des élu·e·s que le masquage
    reconnaît : le dernier mot est pris pour le prénom."""
    mots = nom.split()
    return " ".join([mots[-1], *mots[:-1]])


def _membres(robot: Robot, source: Source) -> list[str]:
    """Les élu·e·s de la page des membres (`site.membres`), dans l'ordre du site, chacun·e « Prénom Nom ». Sans page
    des membres, aucun·e ; une page qui ne se lit pas, ou sans son tableau, n'empêche pas l'import : notée dans le
    journal, elle ne donne personne (en cas de doute, on masque)."""
    url = source.site.membres if source.site else None
    if url is None:
        return []
    try:
        page = robot.lire(url, "import")
    except PageNonLue as e:
        journal(source.nom, f"page des membres {url} non lue ({e})")
        return []
    tableau = arbre(page.texte).premier(lambda n: n.tag == "table" and n.attr("id") == TABLEAU_MEMBRES)
    try:
        lignes = json.loads(tableau.attr("data-entities") or "")["data"] if tableau else None
    except (ValueError, KeyError, TypeError):
        lignes = None
    if not isinstance(lignes, list):
        journal(source.nom, f"page des membres {page.url} sans tableau `{TABLEAU_MEMBRES}` lisible")
        return []
    membres = []
    for ligne in lignes:
        nom = _nom_de_membre(ligne) if isinstance(ligne, dict) else None
        if nom:
            membres.append(nom)
    return membres


def _nom_de_membre(ligne: dict) -> str | None:
    """« Prénom Nom », depuis la colonne `_nameVorname` (« Nom Prénom » : le dernier mot est pris pour le prénom,
    un prénom composé s'écrivant avec un trait d'union) ou `_vornameName` (déjà dans l'ordre)."""
    if ligne.get("_vornameName"):
        return texte_html(str(ligne["_vornameName"])) or None
    nom = texte_html(str(ligne.get("_nameVorname") or ""))
    return _prenom_nom(nom) if nom else None


# --- Mesure du site, pour le script de préparation des sources ------------------------------------------------------

ESSAIS = 3  # liens du menu essayés au plus, par sorte de page
_TRACE = re.compile(r"icms|/_rt[er]/")  # une page d'i-web en porte toujours
_TECHNIQUES = re.compile(r"^/_(rt[er]|doc|docn)/")  # liens vers un élément, un document ou une page technique
_LIENS_DU_MENU = {
    "seances": re.compile(r"s[ée]ances?|sitzung", re.I),
    "membres": re.compile(r"membres|composition|conseill[eè]re?s|bureau", re.I),
}


def _porte(texte: str, *tableaux: str) -> bool:
    """La page porte-t-elle l'un de ces tableaux (`id`) ?"""
    ids = "|".join(re.escape(t) for t in tableaux)
    return re.search(rf"""id=["'](?:{ids})["']""", texte) is not None


def mesurer(pages: PagesLues, page_du_conseil: str, declare: Site, plateforme: Plateforme) -> Mesure:
    """Le site d'une commune mesuré pour le script de préparation des sources, d'après sa page du conseil (déjà lue)
    et ses pages déjà déclarées : une page du conseil sans trace d'i-web l'écarte (« autre » : les sites OIOI web que
    le recensement prenait pour i-web) ; puis la page des Séances (tableaux du module Séances) et celle des membres
    (`personList`), cherchées d'abord parmi les pages déclarées, puis la page du conseil et `ESSAIS` liens de son menu au plus par sorte de page. Le
    niveau et les requêtes du passage ordinaire sont l'affaire du script (`requetes`)."""
    conseil = pages.texte(page_du_conseil) or ""
    if not _TRACE.search(conseil):
        return Mesure("autre", remarques=[f"aucune trace d'i-web sur {page_du_conseil}"])
    mesure = Mesure(plateforme.id)
    menu = [(u, t) for u, t in liens(conseil, page_du_conseil) if not _TECHNIQUES.match(urlsplit(u).path)]

    def chercher(sorte: str, deja: list[str | None], trouve: Callable[[str, str], bool]) -> str | None:
        essais = [u for u in deja if u] + [u for u, t in menu if _LIENS_DU_MENU[sorte].search(f"{u} {t}")][:ESSAIS]
        for url in dict.fromkeys(essais):
            texte = pages.texte(url)
            if texte is not None and trouve(url, texte):
                return url
        return None

    mesure.seances = chercher(
        "seances", [declare.seances, page_du_conseil], lambda _, t: _porte(t, *TABLEAUX_SEANCES)
    )
    if mesure.seances is None:
        mesure.remarques.append("aucune page des Séances i-web trouvée")
        return mesure
    mesure.variante = "seances"
    mesure.membres = chercher("membres", [declare.membres, page_du_conseil], lambda _, t: _porte(t, TABLEAU_MEMBRES))
    return mesure


def requetes(pages: PagesLues, source: Source, depuis: date | None) -> int | None:
    """Les requêtes que coûterait la lecture de `source` (`lire`) au passage ordinaire dont la fenêtre part de
    `depuis`, rejouée sans réseau sur les pages déjà lues : le lien stable d'une Séance jamais lue en
    coûte deux, le site le redirigeant. `robots.txt` et la sonde n'y sont pas. `None` si la lecture échoue."""
    robot = RobotSansReseau(pages.pages, lambda url: 2 if "/_rte/" in url else 1)
    return socle_lecture.requetes(lire, robot, source, depuis)
