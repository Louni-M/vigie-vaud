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

Variante **Objets** (modules Séances et Objets, niveau « objets et séances ») : la liste des Objets (`site.objets`,
tableau `icmsTable-geschaefteList` en `data-entities`) donne pour chacun son numéro brut (`_nummer`, `2026-PM-23`,
pris là seulement), sa catégorie (le type, sans regroupement), sa date (`_geschaeftsdatum`), son titre et son lien
stable `/_rte/information/<id>`. La fiche de chaque Objet de la fenêtre donne ses documents et, s'ils y figurent, son
statut et ses auteur·e·s (`dl` : « Statut », « Auteur »). Un Objet sans numéro n'est pas importé ; de deux Objets de
même numéro, le premier du site l'emporte ; l'un et l'autre sont notés dans le journal. Un point d'ordre du jour est
relié à son Objet par le numéro (`item_affair_number`) de l'Objet que sa colonne « Affaire » cite.

Variante **pages** (module Séances et préavis rédigés, niveau « séances et préavis ») : la page des préavis
(`site.objets`, parfois la page des Séances elle-même, alors lue une seule fois) porte un tableau saisi à la main
(`div.icms-wysiwyg`). Chaque ligne est un Objet de type « Préavis », sans page propre : numéro brut et date dans la
première colonne, titre et statut dans les colonnes « Titre » et « Statut » de l'en-tête, documents par ses liens.
La liste est relue en entier à chaque passage, sans fenêtre. Mêmes règles pour un préavis sans numéro ou en double.
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
TABLEAU_OBJETS = "icmsTable-geschaefteList"
VARIANTES = ("seances", "objets", "pages")
TYPE_PREAVIS = "Préavis"  # le type des Objets d'une page qui ne liste que des préavis


def lire(robot: Robot, source: Source, depuis: date | None) -> Bruts:
    """Le conseil de `source`, une commune i-web, lu sur son site : les Séances de la liste datées de `depuis` ou
    après (toutes sans `depuis`), chacune avec sa page, et, si son niveau en donne, ses Objets."""
    site, conseil = source.site, source.conseil
    if site is None or conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    if site.variante not in VARIANTES:
        raise ValueError(f"{source.id} : variante i-web {site.variante} pas encore lue")
    liste = robot.lire(site.seances, "import")
    lignes = _lignes_de_seances(liste.texte, liste.url)
    lignes_objets: list[_LigneObjet] = []
    preavis: list[dict] = []
    if site.variante != "seances" and {"objets", "preavis"} & set(conseil.donne):
        if site.objets is None:
            raise ValueError(f"{source.id} : variante {site.variante} sans page `objets`")
        # La page des préavis peut être celle des Séances (Puidoux) : elle n'est pas relue.
        page = liste if site.objets == site.seances else robot.lire(site.objets, "import")
        if site.variante == "objets":
            lignes_objets = _lignes_d_objets(source, page.texte, page.url)
        else:
            preavis = _preavis_rediges(source, page.texte, page.url)
    numeros = {o.lien: o.numero for o in lignes_objets}  # pour relier les points à leur Objet
    seances = []
    for ligne in lignes:
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
        seances.append(_meeting(ligne, page.texte, page.url, numeros))
    objets = preavis
    for objet in lignes_objets:
        if depuis is not None and objet.jour is not None and objet.jour < depuis:
            continue
        try:
            page = robot.lire(objet.lien, "import")
        except PageNonLue as e:
            _journal(source, f"Objet {objet.lien} non lu ({e})")
            continue
        objets.append(_affair(objet, page.texte, page.url))
    return Bruts(conseil, objets=objets, seances=seances)


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


def _meeting(ligne: _Ligne, texte: str, url: str, numeros: dict[str, str]) -> dict:
    """La Séance à la forme d'un *meeting* d'OpenParlData, réduit aux champs que l'import lit. Un point est relié à
    son Objet par le numéro (`item_affair_number`) du premier Objet cité dans sa colonne « Affaire » dont la liste
    des Objets donne le numéro (`numeros`, par lien stable)."""
    arbre = _arbre(texte)
    documents = _documents(arbre, url)
    points = []
    for tr in arbre.elements():
        if tr.tag != "tr" or not (tr.attr("id") or "").startswith("traktanden_"):
            continue
        cellules = [c for c in tr.enfants_elements() if c.tag == "td"]
        if len(cellules) < 2:
            continue
        numero = _espaces(cellules[0].texte()) or None
        liens = [urljoin(url, a.attr("href") or "") for c in cellules[2:] for a in c.elements() if a.tag == "a"]
        points.append(
            {
                "item_number_display": numero,
                "item_title": _espaces(cellules[1].texte()),
                "item_affair_number": next((numeros[lien] for lien in liens if lien in numeros), None),
            }
        )
    debut = ligne.jour.isoformat() + (f"T{ligne.heure}:00" if ligne.heure else "")
    return {
        "id": None,
        "name": {"fr": ligne.nom},
        "begin_date": debut,
        "url_external": {"fr": ligne.lien},
        "agendas": {"data": points},
        "docs": {"data": documents},
    }


def _documents(arbre: _Noeud, url: str) -> list[dict]:
    """Les documents d'une page (liens `/_doc/<id>`), chacun une fois, nommés par le texte du lien, sinon son titre,
    sinon la fin du lien."""
    documents, vus = [], set()
    for a in arbre.elements():
        lien = urljoin(url, a.attr("href") or "") if a.tag == "a" else ""
        if "/_doc/" not in lien or lien in vus:
            continue
        vus.add(lien)
        nom = _espaces(a.texte()) or a.attr("title") or lien.rsplit("/", 1)[-1]
        documents.append({"name": nom, "url": lien, "date": None, "category": None})
    return documents


# --- Liste des Objets (variante Objets) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _LigneObjet:
    numero: str  # brut, tel que la liste le donne (`2026-PM-23`)
    type: str  # la catégorie du site (« Préavis municipal »)
    titre: str
    lien: str  # lien stable `/_rte/information/<id>`, absolu
    jour: date | None


_LIEN_INFORMATION = re.compile(r"""href=["']([^"']*/_rte/information/\d+)["'][^>]*>(.*?)</a>""", re.S)


def _lignes_d_objets(source: Source, texte: str, url: str) -> list[_LigneObjet]:
    """Les Objets de la liste du module Objets, dans l'ordre du site : numéro brut (pris là seulement), catégorie,
    date, titre et lien stable. Un Objet sans numéro n'est pas gardé, ni le second de deux Objets de même numéro ; une
    ligne sans lien est illisible ; tous sont notés dans le journal. Une liste sans son tableau ou dont aucune ligne
    ne se lit lève `ValueError`."""
    tableau = next((n for n in _arbre(texte).elements() if n.tag == "table" and n.attr("id") == TABLEAU_OBJETS), None)
    if tableau is None:
        raise ValueError(f"{url} : aucun tableau d'Objets ({TABLEAU_OBJETS})")
    try:
        donnees = json.loads(tableau.attr("data-entities") or "")["data"]
    except (ValueError, KeyError, TypeError) as e:
        raise ValueError(f"{url} : `data-entities` illisible dans {TABLEAU_OBJETS}") from e
    lignes: list[_LigneObjet] = []
    illisibles = 0
    for brute in donnees:
        lien = _LIEN_INFORMATION.search(str(brute.get("title") or "")) if isinstance(brute, dict) else None
        if lien is None:
            illisibles += 1
            _journal(source, "ligne d'Objet illisible (sans lien vers sa page)")
            continue
        titre, numero = _texte(lien[2]), _texte(str(brute.get("_nummer") or ""))
        if not numero:
            _journal(source, f"Objet sans numéro, non importé : {titre}")
            continue
        if any(o.numero == numero for o in lignes):
            _journal(source, f"Objet {numero} en double, le premier du site gardé : {titre}")
            continue
        jour = _DATE.search(_texte(str(brute.get("_geschaeftsdatum") or "")))
        lignes.append(
            _LigneObjet(
                numero=numero,
                type=_texte(str(brute.get("_kategorieId") or "")),
                titre=titre,
                lien=urljoin(url, lien[1]),
                jour=_date(jour) if jour else None,
            )
        )
    if donnees and illisibles == len(donnees):
        raise ValueError(f"{url} : aucune ligne d'Objet lisible")
    return lignes


def _date(jour: re.Match) -> date | None:
    """La date d'un `_DATE` trouvé, ou `None` si elle n'existe pas (« 31.02.2026 »)."""
    try:
        return date(int(jour[3]), int(jour[2]), int(jour[1]))
    except ValueError:
        return None


# --- Page d'un Objet ----------------------------------------------------------------------------------------------


def _affair(ligne: _LigneObjet, texte: str, url: str) -> dict:
    """L'Objet à la forme d'une *affair* d'OpenParlData : numéro, type, date et titre de la liste ; statut et
    auteur·e·s de sa fiche (`dl` : « Statut », « Auteur »), seulement s'ils y sont ; ses documents."""
    arbre = _arbre(texte)
    statut, auteurs = None, []
    for dl in (n for n in arbre.elements() if n.tag == "dl"):
        enfants = dl.enfants_elements()
        for dt, dd in zip(enfants, enfants[1:], strict=False):
            if dt.tag != "dt" or dd.tag != "dd":
                continue
            libelle = _espaces(dt.texte()).lower()
            if libelle == "statut":
                statut = _espaces(dd.texte()) or None
            elif libelle.startswith(("auteur", "co-auteur")):
                auteurs += [
                    {"type": "person", "fullname": _prenom_nom(_espaces(a.texte()))}
                    for a in dd.elements()
                    if a.tag == "a" and "/_rte/person/" in (a.attr("href") or "") and a.texte().strip()
                ]
    return {
        "id": None,
        "number": ligne.numero,
        "title": {"fr": ligne.titre},
        "type_name": {"fr": ligne.type},
        "state_name": {"fr": statut} if statut else None,
        "begin_date": ligne.jour.isoformat() if ligne.jour else None,
        "url_external": {"fr": ligne.lien},
        "contributors": {"data": auteurs},
        "docs": {"data": _documents(arbre, url)},
    }


def _prenom_nom(nom: str) -> str:
    """« Krebs Yann », comme i-web nomme une personne, devient « Yann Krebs », l'ordre des élu·e·s que le masquage
    reconnaît : le dernier mot est pris pour le prénom."""
    mots = nom.split()
    return " ".join([mots[-1], *mots[:-1]])


# --- Préavis rédigés dans une page (variante pages) ---------------------------------------------------------------

# « Préavis 09-2021 – 09.11.2021 », « Préavis n° 12/2026 du 19 mai 2026 » : le numéro est le premier mot qui suit le
# mot « Préavis » (s'il y est), quand il porte un chiffre et n'est pas une date.
_NUMERO_PREAVIS = re.compile(r"^(?:préavis(?:\s+municipal)?\s*)?(?:n[°o]\.?\s*)?(?P<numero>\S*\d\S*)", re.I)
_MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
_DATE_EN_LETTRES = re.compile(rf"\b(\d{{1,2}})(?:er)?\s+({'|'.join(_MOIS)})\s+(\d{{4}})\b", re.I)


def _preavis_rediges(source: Source, texte: str, url: str) -> list[dict]:
    """Les préavis des tableaux rédigés dans la page (`div.icms-wysiwyg`), dans l'ordre du site, à la forme d'une
    *affair* : la première colonne donne le numéro brut et la date (« Préavis 09-2021 – 09.11.2021 »), les colonnes
    « Titre » et « Statut » de l'en-tête (sinon la deuxième, et pas de statut) le titre et le statut ; les liens de la
    ligne sont ses documents. Un préavis sans numéro n'est pas importé, ni le second de deux préavis de même
    numéro ; l'un et l'autre sont notés dans le journal. Une page sans tableau rédigé lève `ValueError`."""
    redige = [n for n in _arbre(texte).elements() if "icms-wysiwyg" in (n.attr("class") or "").split()]
    tableaux = [t for r in redige for t in r.elements() if t.tag == "table"]
    if not tableaux:
        raise ValueError(f"{url} : aucun tableau de préavis rédigé dans la page")
    preavis: list[dict] = []
    for tableau in tableaux:
        rangees = [
            [c for c in tr.enfants_elements() if c.tag in ("td", "th")] for tr in tableau.elements() if tr.tag == "tr"
        ]
        rangees = [r for r in rangees if r]
        entete = [_espaces(c.texte()).lower() for c in rangees[0]] if rangees else []
        if entete and not re.search(r"\d", entete[0]):
            rangees = rangees[1:]
        else:
            entete = []
        col_titre = next((i for i, t in enumerate(entete) if "titre" in t), 1)
        col_statut = next((i for i, t in enumerate(entete) if "statut" in t), None)
        for cellules in rangees:
            textes = [_espaces(c.texte()) for c in cellules]
            if len(textes) <= col_titre:
                _journal(source, f"ligne de préavis illisible ({textes[0]})")
                continue
            numero = _NUMERO_PREAVIS.match(textes[0])
            numero = numero["numero"].rstrip(".,;:") if numero and not _DATE.fullmatch(numero["numero"]) else None
            if not numero:
                _journal(source, f"Objet sans numéro, non importé : {textes[0]}")
                continue
            if any(p["number"] == numero for p in preavis):
                _journal(source, f"Objet {numero} en double, le premier du site gardé : {textes[col_titre]}")
                continue
            reste = textes[0][textes[0].index(numero) + len(numero) :]
            statut = textes[col_statut] if col_statut is not None and col_statut < len(textes) else ""
            liens = [a for c in cellules for a in c.elements() if a.tag == "a" and a.attr("href")]
            preavis.append(
                {
                    "id": None,
                    "number": numero,
                    "title": {"fr": textes[col_titre]},
                    "type_name": {"fr": TYPE_PREAVIS},
                    "state_name": {"fr": statut} if statut else None,
                    "begin_date": _jour_ecrit(reste),
                    "url_external": None,
                    "docs": {
                        "data": [
                            {
                                "name": _espaces(a.texte()) or (a.attr("href") or "").rsplit("/", 1)[-1],
                                "url": urljoin(url, a.attr("href") or ""),
                                "date": None,
                                "category": None,
                            }
                            for a in liens
                        ]
                    },
                }
            )
    return preavis


def _jour_ecrit(texte: str) -> str | None:
    """La première date d'un texte, en chiffres (« 09.11.2021 ») ou en lettres (« 19 mai 2026 »), au format ISO."""
    chiffres, lettres = _DATE.search(texte), _DATE_EN_LETTRES.search(texte)
    if chiffres and (not lettres or chiffres.start() < lettres.start()):
        jour = _date(chiffres)
    elif lettres:
        try:
            jour = date(int(lettres[3]), _MOIS.index(lettres[2].lower()) + 1, int(lettres[1]))
        except ValueError:
            jour = None
    else:
        jour = None
    return jour.isoformat() if jour else None


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
