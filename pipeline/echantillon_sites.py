"""Enregistre l'échantillon de test d'une plateforme de sites communaux (`tests/echantillon-sites/`, ADR 0010).

Pour chaque variante, une commune choisie et chaque sorte de page que son module de lecture lit (liste des
Séances, page d'une Séance, liste et page des Objets, page des membres…). Chaque page passe par le robot communal
(ADR 0006 : une requête à la fois, 5 s au moins par /24), puis elle est **réduite de façon déterministe** :

- seuls restent les blocs déclarés (`blocs`, des sélecteurs simples comme `table#icmsTablePastSitzungen`) et le
  chemin de balises qui y mène, réduit au nom, à l'`id` et à la `class` de chaque ancêtre ; le marqueur de la sonde
  est l'un de ces blocs ;
- dans les blocs, ni scripts, ni styles, ni menus, ni formulaires, ni images ; ni attribut `style` ni `on…` ;
- les lignes d'une liste ne sont gardées que si elles portent l'un des identifiants choisis (`ids`) : les lignes du
  JSON d'un attribut `data-entities` (i-web), et les éléments désignés par `lignes` (`li`, `tr`…) ; un identifiant
  porte une ligne quand l'une de ses valeurs l'égale, ou qu'un lien y finit par `/<identifiant>` ;
- un commentaire de provenance (commune, URL, date de lecture, réduction) ouvre chaque page.

Les identifiants sont choisis pour porter les cas à couvrir **sans nommer aucun particulier** ; après chaque
enregistrement, on relit l'échantillon. Un bloc ou un identifiant qui manque arrête le script : la page a changé, la
déclaration est à revoir. Une page non lue (erreur HTTP, refus, délai) l'arrête aussi, sans nouvel essai.

Chaque variante a son dossier (`<plateforme>/<variante>/`), avec ses pages réduites, encodées comme le site les a
servies, et `index.json` (URL demandée et finale, statut, en-têtes utiles de chaque page ; le corps enregistré est
décompressé, un faux transport qui sert son `content-encoding` le recompresse). Les pages entières
restent hors du dépôt, dans le dossier `--brut` : relancé avec `--hors-ligne`, le script refait la réduction sans
aucune requête et produit les mêmes fichiers.

Lancé à la main, jamais par le cron : au début de chaque étape de J3 pour sa plateforme, puis dans la PR qui corrige
une refonte si elle touche la commune d'un échantillon. Usage (depuis `pipeline/`) :

    uv run python echantillon_sites.py i-web                 # les variantes d'une plateforme
    uv run python echantillon_sites.py i-web/seances         # une seule variante
    uv run python echantillon_sites.py i-web --hors-ligne    # réduction refaite depuis les pages brutes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx

from robot_communal import Robot, robot_des_sources
from schema import RACINE, lire_sources

DOSSIER = Path(__file__).resolve().parent / "tests" / "echantillon-sites"
BRUT = Path.home() / ".cache" / "vigie-vaud" / "echantillon-sites"
SOURCES = RACINE / "sources.json"


@dataclass(frozen=True)
class PageEchantillon:
    sorte: str  # « seances », « seance », « objets », « objet », « membres »… : nom du fichier
    url: str
    blocs: tuple[str, ...]  # sélecteurs des blocs lus (`tag`, `#id`, `.classe`, `tag#id`, `tag.classe`)
    ids: tuple[str, ...] = ()  # identifiants des lignes gardées ; vide : toutes
    lignes: str | None = None  # sélecteur des lignes d'une liste HTML (`tr`, `tbody>tr`…)
    sans: tuple[str, ...] = ()  # sélecteurs des éléments retirés des blocs (bouton d'archive, contact…)


@dataclass(frozen=True)
class Echantillon:
    plateforme: str
    variante: str
    commune: str
    ofs: int
    pages: tuple[PageEchantillon, ...]

    @property
    def nom(self) -> str:
        return f"{self.plateforme}/{self.variante}"


_SEANCES_IWEB = ("table#icmsTableFutureSitzungen", "table#icmsTablePastSitzungen")
_SEANCE_IWEB = dict(
    blocs=("h1.contentTitle", "div.icms-content-col-a"),
    lignes="tbody>tr",
    # Le bouton de l'archive Zip, la description et le contact sont des textes de la commune, pas des données.
    sans=("div#zipDownloadDiv", "div.icms-desclist-container", "div.icms-container-callout"),
)

# Communes choisies d'après la recherche « Publications des conseils » (branche research/publications-conseils).
ECHANTILLONS: tuple[Echantillon, ...] = (
    # Module Séances seul : liste en JSON échappé, une page par Séance (lien stable redirigé vers /sitzung/<id>),
    # documents de Séance ; les membres du bureau dans `personList`.
    Echantillon("i-web", "seances", "Préverenges", 5643, (
        PageEchantillon(
            "seances", "https://www.preverenges.ch/sitzung", _SEANCES_IWEB,
            # À venir ; 18 juin, 10 septembre (page lue) et 5 février 2026, dans le désordre du site.
            ("6987214", "6987193", "6987205", "7273262"),
        ),
        PageEchantillon(
            "seance", "https://www.preverenges.ch/_rte/anlass/6987205",
            ids=("7223149", "7223152", "7223158", "7223161"),  # ordre du jour, préavis, décision, procès-verbal
            **_SEANCE_IWEB,
        ),
        PageEchantillon(
            "membres", "https://www.preverenges.ch/conseil", ("h1.contentTitle", "table#icmsTable-personList"),
            ("123379", "123415"),  # le président et la 1re vice-présidente du Conseil
        ),
    )),
    # Modules Séances et Objets : Objets numérotés (`2026-PM-23`) avec catégorie, statut et autorité ; points
    # d'ordre du jour reliés à leurs Objets.
    Echantillon("i-web", "objets", "Blonay - Saint-Légier", 5892, (
        PageEchantillon(
            "seances", "https://www.blonay-saint-legier.ch/seances", _SEANCES_IWEB,
            # À venir ; 8 et 29 septembre 2026 (page lue), puis l'installation du 18 juin, dans le désordre du site.
            ("6895126", "6895117", "6895123", "7693285"),
        ),
        PageEchantillon(
            "seance", "https://www.blonay-saint-legier.ch/_rte/anlass/6895123",
            ids=(
                "7246414", "7262080",  # ordre du jour, procès-verbal
                "traktanden_197017", "traktanden_197032", "traktanden_197035",  # points 1, 5 et 6
                "2909893", "2981212", "3002125",  # Objets de la Séance : préavis 23-2026, deux communications
            ),
            **_SEANCE_IWEB,
        ),
        PageEchantillon(
            "objets", "https://www.blonay-saint-legier.ch/objets-politiques", ("table#icmsTable-geschaefteList",),
            # Préavis 23-2026 (point 6) et 37-2026 (page lue), un postulat d'élu·e, deux communications.
            ("2909893", "3002200", "3000802", "2981212", "3002125"),
        ),
        PageEchantillon("objet", "https://www.blonay-saint-legier.ch/_rte/information/3002200", ("div.maincontent",)),
        # Le postulat d'un élu (2026-PO-02) : un Objet dont la fiche publie ses auteur·e·s.
        PageEchantillon("postulat", "https://www.blonay-saint-legier.ch/_rte/information/3000802", ("div.maincontent",)),
    )),
    # Préavis rédigés dans une page (tableau saisi à la main sous les Séances), à côté du module Séances.
    Echantillon("i-web", "pages", "Puidoux", 5607, (
        PageEchantillon(
            "seances", "https://www.puidoux.ch/seances", (*_SEANCES_IWEB, "table.Table"),
            (
                "7115819", "7115804", "7115816",  # à venir ; séance annulée du 29 janvier ; 1er octobre (page lue)
                "N° du préavis et date",  # ligne d'en-tête du tableau des préavis
                "09-2021",  # préavis sans document
                "5549947", "5550052",  # retiré, refusé
                "7014520",  # date en toutes lettres
                "7206067",  # 05-2026 et 07-2026, liés au même document
                "7206046",  # proposition du bureau, sans numéro
            ),
            lignes="tbody>tr",
        ),
        PageEchantillon(
            "seance", "https://www.puidoux.ch/_rte/anlass/7115816",
            ids=("7206034", "7206037", "7266115", "7266130"),  # ordre du jour, préavis, extrait de décision, PV
            **_SEANCE_IWEB,
        ),
    )),
)


# --- Lecture, par le robot ou depuis les pages brutes -----------------------------------------------------------


@dataclass(frozen=True)
class Brute:
    """Une page telle que le robot l'a lue, gardée hors du dépôt."""

    url: str
    finale: str
    statut: int
    entetes: dict[str, str]
    texte: str
    lu_le: str  # « 2026-10-23 »


def _chemin_brut(brut: Path, url: str) -> Path:
    return brut / (hashlib.sha256(url.encode("utf-8")).hexdigest()[:24] + ".json")


def _lire(robot: Robot | None, url: str, brut: Path, horloge: Callable[[], datetime]) -> Brute:
    chemin = _chemin_brut(brut, url)
    if chemin.exists():
        return Brute(**json.loads(chemin.read_text(encoding="utf-8")))
    if robot is None:
        raise FileNotFoundError(f"{url} : page brute absente de {brut}, relancer sans --hors-ligne")
    reponse = robot.lire(url, "import")
    page = Brute(url, reponse.url, reponse.statut, reponse.entetes, reponse.texte, horloge().date().isoformat())
    brut.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(page.__dict__, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return page


def enregistrer(
    robot: Robot | None,
    echantillon: Echantillon,
    dossier: Path,
    brut: Path,
    horloge: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> list[Path]:
    """Lit les pages de `echantillon` (par `robot`, ou depuis `brut` si elles y sont déjà ; sans robot, seulement
    depuis `brut`), écrit leur réduction et l'index de la variante dans `dossier`, et rend les fichiers écrits."""
    sortie = dossier / echantillon.plateforme / echantillon.variante
    lues = [(page, _lire(robot, page.url, brut, horloge)) for page in echantillon.pages]
    reduites = [_provenance(echantillon, page, brute) + reduire(brute.texte, page) for page, brute in lues]
    sortie.mkdir(parents=True, exist_ok=True)
    ecrits, index = [], []
    for (page, brute), texte in zip(lues, reduites, strict=True):
        fichier = sortie / f"{page.sorte}.html"
        fichier.write_bytes(texte.encode(_charset(brute.entetes), errors="xmlcharrefreplace"))
        ecrits.append(fichier)
        index.append(
            {"sorte": page.sorte, "url": brute.url, "finale": brute.finale, "statut": brute.statut,
             "entetes": brute.entetes, "fichier": fichier.name}
        )
    chemin_index = sortie / "index.json"
    entete = {"plateforme": echantillon.plateforme, "variante": echantillon.variante,
              "commune": echantillon.commune, "ofs": echantillon.ofs}
    chemin_index.write_text(json.dumps(entete | {"pages": index}, ensure_ascii=False, indent=1) + "\n", "utf-8")
    return [*ecrits, chemin_index]


def _charset(entetes: dict[str, str]) -> str:
    m = re.search(r"charset=\"?([\w.:-]+)", entetes.get("content-type", ""), re.I)
    return m[1].lower() if m else "utf-8"


def _provenance(echantillon: Echantillon, page: PageEchantillon, brute: Brute) -> str:
    url = brute.url if brute.finale == brute.url else f"{brute.url} (redirigée vers {brute.finale})"
    lignes = f" ; lignes gardées : {', '.join(page.ids)}" if page.ids else ""
    return (
        "<!--\n"
        f"  Échantillon {echantillon.plateforme}, variante {echantillon.variante} : {echantillon.commune} "
        f"(OFS {echantillon.ofs}), page {page.sorte}.\n"
        f"  URL : {url}\n"
        f"  Enregistrée le {brute.lu_le} par pipeline/echantillon_sites.py.\n"
        f"  Réduction : blocs {', '.join(page.blocs)} et leur chemin de balises{lignes} ;\n"
        "  sans scripts, styles, menus ni textes rédigés.\n"
        "-->\n"
    )


# --- Réduction ----------------------------------------------------------------------------------------------------

VIDES = frozenset("area base br col embed hr img input link meta source track wbr".split())
RETIRES = frozenset(
    "script style noscript template nav header footer iframe svg img picture form button input select textarea "
    "link meta".split()
)


@dataclass
class _Noeud:
    tag: str
    attrs: list[tuple[str, str]]
    enfants: list[_Noeud | str] = field(default_factory=list)
    parent: _Noeud | None = None

    def attr(self, nom: str) -> str | None:
        return next((v for k, v in self.attrs if k == nom), None)

    def elements(self):
        for e in self.enfants:
            if isinstance(e, _Noeud):
                yield e
                yield from e.elements()


class _Arbre(HTMLParser):
    """Un arbre tolérant : une balise fermante sans ouvrante est ignorée, une fermante referme ce qu'elle englobe."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.racine = _Noeud("#document", [])
        self._pile = [self.racine]

    def handle_starttag(self, tag, attrs):
        noeud = _Noeud(tag, [(k, v or "") for k, v in attrs], parent=self._pile[-1])
        self._pile[-1].enfants.append(noeud)
        if tag not in VIDES:
            self._pile.append(noeud)

    def handle_startendtag(self, tag, attrs):
        self._pile[-1].enfants.append(_Noeud(tag, [(k, v or "") for k, v in attrs], parent=self._pile[-1]))

    def handle_endtag(self, tag):
        for i in range(len(self._pile) - 1, 0, -1):
            if self._pile[i].tag == tag:
                del self._pile[i:]
                return

    def handle_data(self, data):
        self._pile[-1].enfants.append(data)


_SELECTEUR = re.compile(r"^(?P<tag>[a-z][a-z0-9]*)?(?:#(?P<id>[\w-]+))?(?:\.(?P<classe>[\w-]+))?$", re.I)


def _correspond(noeud: _Noeud, selecteur: str) -> bool:
    """`tag`, `#id`, `.classe` et leurs combinaisons, ou `parent>enfant` (enfant direct)."""
    if ">" in selecteur:
        parent, enfant = selecteur.rsplit(">", 1)
        return (
            _correspond(noeud, enfant.strip())
            and noeud.parent is not None
            and _correspond(noeud.parent, parent.strip())
        )
    m = _SELECTEUR.match(selecteur)
    if not m or not any(m.groups()):
        raise ValueError(f"sélecteur non pris en charge : {selecteur}")
    return (
        (m["tag"] is None or noeud.tag == m["tag"].lower())
        and (m["id"] is None or noeud.attr("id") == m["id"])
        and (m["classe"] is None or m["classe"] in (noeud.attr("class") or "").split())
    )


def _porte(valeur: object, identifiant: str) -> bool:
    """Une valeur porte un identifiant si elle l'égale ou si un lien y finit par `/<identifiant>`. Une ligne HTML
    le porte aussi si son texte le contient comme un mot (un numéro de préavis dans une ligne sans lien)."""
    if isinstance(valeur, _Noeud):
        texte = " ".join(_texte_de(valeur).split())
        if re.search(rf"(?<![\w-]){re.escape(identifiant)}(?![\w-])", texte):
            return True
        return _porte([v for n in (valeur, *valeur.elements()) for _, v in n.attrs], identifiant)
    if isinstance(valeur, dict):
        return any(_porte(v, identifiant) for v in valeur.values())
    if isinstance(valeur, list):
        return any(_porte(v, identifiant) for v in valeur)
    texte = str(valeur)
    return texte == identifiant or re.search(rf"/{re.escape(identifiant)}(?![\w-])", texte) is not None


def reduire(texte: str, page: PageEchantillon) -> str:
    """La page réduite à ses blocs lus, sans le commentaire de provenance. Lève `ValueError` si un bloc ou un
    identifiant manque."""
    arbre = _Arbre()
    arbre.feed(texte)
    arbre.close()
    tous = list(arbre.racine.elements())
    blocs = []
    for selecteur in page.blocs:
        trouves = [n for n in tous if _correspond(n, selecteur) and not any(b in _ancetres(n) for b in blocs)]
        if not trouves:
            raise ValueError(f"{page.url} : aucun bloc {selecteur}")
        blocs += trouves
    vus: set[str] = set()
    for bloc in blocs:
        _filtrer(bloc, page, vus)
    manquants = [i for i in page.ids if i not in vus]
    if manquants:
        raise ValueError(f"{page.url} : identifiants absents des blocs : {', '.join(manquants)}")
    chemin = {id(a) for b in blocs for a in _ancetres(b)}
    gardes = {id(b) for b in blocs}
    return "".join(_ecrire_chemin(e, chemin, gardes) for e in arbre.racine.enfants if isinstance(e, _Noeud))


def _ancetres(noeud: _Noeud) -> list[_Noeud]:
    out = []
    while noeud.parent is not None and noeud.parent.tag != "#document":
        noeud = noeud.parent
        out.append(noeud)
    return out


def _filtrer(bloc: _Noeud, page: PageEchantillon, vus: set[str]) -> None:
    """Retire du bloc les balises retirées et les lignes qui ne portent aucun identifiant choisi."""
    for noeud in [bloc, *bloc.elements()]:
        noeud.enfants = [
            e for e in noeud.enfants
            if not (isinstance(e, _Noeud) and (e.tag in RETIRES or any(_correspond(e, x) for x in page.sans)))
        ]
        noeud.attrs = [(k, v) for k, v in noeud.attrs if k != "style" and not k.startswith("on")]
        entites = noeud.attr("data-entities")
        if entites is not None and page.ids:
            donnees = json.loads(entites)
            donnees["data"] = [r for r in donnees.get("data", []) if _garder(r, page.ids, vus)]
            valeur = _json(donnees, entites)
            noeud.attrs = [(k, valeur if k == "data-entities" else v) for k, v in noeud.attrs]
        if page.lignes and page.ids:
            noeud.enfants = [
                e for e in noeud.enfants
                if not (isinstance(e, _Noeud) and _correspond(e, page.lignes))
                or _garder(e, page.ids, vus)
            ]


def _json(donnees: object, original: str) -> str:
    """Les données réécrites dans le style de l'original : celui de PHP chez i-web (`\\/`, `\\u00e9`)."""
    texte = json.dumps(donnees, ensure_ascii="\\u" in original, separators=(",", ":"))
    return texte.replace("/", "\\/") if "\\/" in original else texte


def _texte_de(noeud: _Noeud) -> str:
    return " ".join(e if isinstance(e, str) else _texte_de(e) for e in noeud.enfants)


def _garder(valeur: object, ids: tuple[str, ...], vus: set[str]) -> bool:
    portes = [i for i in ids if _porte(valeur, i)]
    vus.update(portes)
    return bool(portes)


def _attributs(noeud: _Noeud, tous: bool = True) -> str:
    attrs = noeud.attrs if tous else [(k, v) for k, v in noeud.attrs if k in ("id", "class")]
    return "".join(f' {k}="{_echapper(v)}"' for k, v in attrs)


def _echapper(valeur: str) -> str:
    return valeur.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _texte(t: str) -> str:
    return re.sub(r"\s+", " ", t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ecrire_chemin(noeud: _Noeud, chemin: set[int], gardes: set[int]) -> str:
    if id(noeud) in gardes:
        return _ecrire(noeud)
    if id(noeud) not in chemin:
        return ""
    interieur = "".join(_ecrire_chemin(e, chemin, gardes) for e in noeud.enfants if isinstance(e, _Noeud))
    return f"<{noeud.tag}{_attributs(noeud, tous=False)}>\n{interieur}</{noeud.tag}>\n"


def _ecrire(noeud: _Noeud) -> str:
    """Un élément gardé, une ligne par élément (espaces réduites, pour un diff lisible), sauf ceux qui tiennent
    sur une ligne : texte seul, texte mêlé d'éléments, ou un seul enfant qui tient lui-même sur une ligne."""
    if noeud.tag in VIDES:
        return f"<{noeud.tag}{_attributs(noeud)}>\n"
    if _sur_une_ligne(noeud):
        return f"<{noeud.tag}{_attributs(noeud)}>{_en_ligne(noeud).strip()}</{noeud.tag}>\n"
    elements = [e for e in noeud.enfants if isinstance(e, _Noeud)]
    return f"<{noeud.tag}{_attributs(noeud)}>\n" + "".join(_ecrire(e) for e in elements) + f"</{noeud.tag}>\n"


def _sur_une_ligne(noeud: _Noeud) -> bool:
    elements = [e for e in noeud.enfants if isinstance(e, _Noeud)]
    mele = any(isinstance(e, str) and e.strip() for e in noeud.enfants)
    return not elements or mele or (len(elements) == 1 and _sur_une_ligne(elements[0]))


def _en_ligne(noeud: _Noeud) -> str:
    out = []
    for e in noeud.enfants:
        if isinstance(e, str):
            out.append(_texte(e))
        elif e.tag in VIDES:
            out.append(f"<{e.tag}{_attributs(e)}>")
        else:
            out.append(f"<{e.tag}{_attributs(e)}>{_en_ligne(e).strip()}</{e.tag}>")
    return "".join(out)


# --- Ligne de commande ------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("choix", nargs="+", help="plateforme (`i-web`) ou variante (`i-web/seances`)")
    parser.add_argument("--brut", type=Path, default=BRUT, help="dossier des pages entières, hors du dépôt")
    parser.add_argument("--hors-ligne", action="store_true", help="aucune requête : pages brutes seulement")
    args = parser.parse_args(argv)
    choisis = [e for e in ECHANTILLONS if e.nom in args.choix or e.plateforme in args.choix]
    if not choisis:
        sys.exit(f"aucun échantillon pour {', '.join(args.choix)} ; connus : {', '.join(e.nom for e in ECHANTILLONS)}")
    with httpx.Client() as http:
        # Au débit de l'ADR-0006, réseaux ralentis à la main compris (section `reseaux` de `sources.json`).
        robot = None if args.hors_ligne else robot_des_sources(http, lire_sources(SOURCES), lambda: datetime.now(UTC))
        for echantillon in choisis:
            for chemin in enregistrer(robot, echantillon, DOSSIER, args.brut):
                print(f"{chemin.relative_to(DOSSIER)} : {chemin.stat().st_size / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
