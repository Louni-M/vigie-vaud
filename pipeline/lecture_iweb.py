"""Module de lecture de la plateforme i-web (ADR 0010) : une seule opération publique, `lire`, qui lit le conseil
d'une commune i-web par le robot communal et rend ses `Bruts`, à la forme d'OpenParlData.

Variante **Séances** (module Séances d'i-web) : la page de liste (`site.seances`) porte deux tableaux, les Séances à
venir (`icmsTableFutureSitzungen`) et passées (`icmsTablePastSitzungen`), dont les lignes sont en JSON échappé dans
l'attribut `data-entities` ; chaque ligne donne le nom de la Séance, son lien `/_rte/anlass/<id>` et sa date
(« 10.09.2026, 20h00 - 22h00 »). La page de chaque Séance de la fenêtre est ouverte par ce lien stable, que le site
redirige vers `/seances/<id>` ou `/sitzung/<id>` : elle donne ses documents (liens `/_doc/<id>`, nommés par le texte
du lien) et, quand le site les publie en HTML, les points de son ordre du jour (`tr#traktanden_<n>` : numéro, titre).

Une Séance scrapée n'a pas d'identifiant (`id` nul) : son lien est le lien stable, sa date celle de la liste, telle
quelle, même fictive. Une ligne sans lien ou sans date lisible, ou une Séance dont la page n'a pas pu être lue, est
sautée et notée dans le journal ; une liste dont aucune ligne ne se lit, ou sans ses tableaux, lève `ValueError`.

**Membres** : la page des membres (`site.membres`, facultative) porte le tableau `icmsTable-personList`, en JSON
échappé dans `data-entities` comme les Séances ; la colonne `_nameVorname` donne « Nom Prénom », remis en « Prénom
Nom » (ordre des contributeurs d'OpenParlData, que le masquage attend). Une page des membres illisible est notée dans
le journal et ne donne personne : l'import continue.
"""

from __future__ import annotations

import html
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urljoin

from bruts import Bruts
from robot_communal import PageNonLue, Robot
from schema import Source

TABLEAUX_SEANCES = ("icmsTableFutureSitzungen", "icmsTablePastSitzungen")
TABLEAU_MEMBRES = "icmsTable-personList"
VARIANTES = ("seances",)


def lire(robot: Robot, source: Source, depuis: date | None) -> Bruts:
    """Le conseil de `source`, une commune i-web, lu sur son site : les Séances de la liste datées de `depuis` ou
    après (toutes sans `depuis`), chacune avec sa page."""
    site, conseil = source.site, source.conseil
    if site is None or conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    if site.variante not in VARIANTES:
        raise ValueError(f"{source.id} : variante i-web {site.variante} pas encore lue")
    liste = robot.lire(site.seances, "import")
    seances = []
    for ligne in _lignes_de_seances(liste.texte, liste.url):
        if isinstance(ligne, str):
            _journal(source, f"ligne de Séance illisible ({ligne})")
            continue
        if depuis is not None and ligne.jour < depuis:
            continue
        try:
            page = robot.lire(ligne.lien, "import")
        except PageNonLue as e:
            _journal(source, f"Séance {ligne.lien} non lue ({e})")
            continue
        seances.append(_meeting(ligne, page.texte, page.url))
    return Bruts(conseil, seances=seances, membres=_membres(robot, source))


def _journal(source: Source, message: str) -> None:
    print(f"{source.nom} : élément sauté, {message}", file=sys.stderr)


# --- Page de liste ------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Ligne:
    nom: str
    lien: str  # lien stable `/_rte/anlass/<id>`, absolu
    jour: date
    heure: str | None  # « 20:00 »


_LIEN_ANLASS = re.compile(r"""href=["']([^"']*/_rte/anlass/\d+)["'][^>]*>(.*?)</a>""", re.S)
_DATE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_HEURE = re.compile(r"\b(\d{1,2})h(\d{2})\b")


def _lignes_de_seances(texte: str, url: str) -> list[_Ligne | str]:
    """Les lignes des deux tableaux de Séances, dans l'ordre du site : chacune lue (`_Ligne`) ou, illisible, la raison
    de son échec."""
    arbre = _arbre(texte)
    tableaux = [n for n in arbre.elements() if n.tag == "table" and n.attr("id") in TABLEAUX_SEANCES]
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
    datum = _texte(str(brute.get("_datum") or ""))
    jour = _DATE.search(datum)
    if jour is None:
        return f"sans date : {lien[1]}"
    try:
        quand = date(int(jour[3]), int(jour[2]), int(jour[1]))
    except ValueError:
        return f"date impossible « {jour[0]} » : {lien[1]}"
    heure = _HEURE.search(datum[jour.end() :])
    return _Ligne(
        nom=_texte(lien[2]),
        lien=urljoin(url, lien[1]),
        jour=quand,
        heure=f"{int(heure[1]):02d}:{heure[2]}" if heure else None,
    )


# --- Page d'une Séance --------------------------------------------------------------------------------------------


def _meeting(ligne: _Ligne, texte: str, url: str) -> dict:
    """La Séance à la forme d'un *meeting* d'OpenParlData, réduit aux champs que l'import lit."""
    arbre = _arbre(texte)
    documents, vus = [], set()
    for a in arbre.elements():
        lien = urljoin(url, a.attr("href") or "") if a.tag == "a" else ""
        if "/_doc/" not in lien or lien in vus:
            continue
        vus.add(lien)
        nom = _espaces(a.texte()) or a.attr("title") or lien.rsplit("/", 1)[-1]
        documents.append({"name": nom, "url": lien, "date": None, "category": None})
    points = []
    for tr in arbre.elements():
        if tr.tag != "tr" or not (tr.attr("id") or "").startswith("traktanden_"):
            continue
        cellules = [c for c in tr.enfants_elements() if c.tag == "td"]
        if len(cellules) < 2:
            continue
        numero = _espaces(cellules[0].texte()) or None
        points.append({"item_number_display": numero, "item_title": _espaces(cellules[1].texte())})
    debut = ligne.jour.isoformat() + (f"T{ligne.heure}:00" if ligne.heure else "")
    return {
        "id": None,
        "name": {"fr": ligne.nom},
        "begin_date": debut,
        "url_external": {"fr": ligne.lien},
        "agendas": {"data": points},
        "docs": {"data": documents},
    }


# --- Page des membres ---------------------------------------------------------------------------------------------


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
        _journal(source, f"page des membres {url} non lue ({e})")
        return []
    tableau = next(
        (n for n in _arbre(page.texte).elements() if n.tag == "table" and n.attr("id") == TABLEAU_MEMBRES), None
    )
    try:
        lignes = json.loads(tableau.attr("data-entities") or "")["data"] if tableau else None
    except (ValueError, KeyError, TypeError):
        lignes = None
    if not isinstance(lignes, list):
        _journal(source, f"page des membres {page.url} sans tableau `{TABLEAU_MEMBRES}` lisible")
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
        return _texte(str(ligne["_vornameName"])) or None
    mots = _texte(str(ligne.get("_nameVorname") or "")).split()
    if not mots:
        return None
    return " ".join(mots[-1:] + mots[:-1])


# --- Analyse du HTML ----------------------------------------------------------------------------------------------

_VIDES = frozenset("area base br col embed hr img input link meta source track wbr".split())


@dataclass
class _Noeud:
    tag: str
    attrs: dict[str, str]
    enfants: list[_Noeud | str] = field(default_factory=list)

    def attr(self, nom: str) -> str | None:
        return self.attrs.get(nom)

    def elements(self):
        for e in self.enfants:
            if isinstance(e, _Noeud):
                yield e
                yield from e.elements()

    def enfants_elements(self) -> list[_Noeud]:
        return [e for e in self.enfants if isinstance(e, _Noeud)]

    def texte(self) -> str:
        return " ".join(e if isinstance(e, str) else e.texte() for e in self.enfants)


class _Arbre(HTMLParser):
    """Un arbre tolérant : une balise fermante sans ouvrante est ignorée, une fermante referme ce qu'elle englobe."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.racine = _Noeud("#document", {})
        self._pile = [self.racine]

    def handle_starttag(self, tag, attrs):
        noeud = _Noeud(tag, {k: v or "" for k, v in attrs})
        self._pile[-1].enfants.append(noeud)
        if tag not in _VIDES:
            self._pile.append(noeud)

    def handle_endtag(self, tag):
        for i in range(len(self._pile) - 1, 0, -1):
            if self._pile[i].tag == tag:
                del self._pile[i:]
                return

    def handle_data(self, data):
        self._pile[-1].enfants.append(data)


def _arbre(texte: str) -> _Noeud:
    analyse = _Arbre()
    analyse.feed(texte)
    analyse.close()
    return analyse.racine


def _texte(fragment: str) -> str:
    """Le texte d'un fragment HTML, balises retirées, entités décodées, espaces réduites."""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", fragment)).split())


def _espaces(texte: str) -> str:
    return " ".join(texte.split())
