"""Préparation des sources communales de `sources.json` (spec de J3, « Scripts de préparation » ; ADR 0010).

Les déclarations des communes scrapées ne changent que par une PR, jamais par le cron. Ce script aide à les écrire et à
les tenir justes, en **remesurant les sites d'une plateforme** par le robot communal (ADR 0006 : une requête à la
fois, 5 s au moins par /24, `VigieVaud-import`) :

- la **plateforme réelle** : une page du conseil sans trace de la plateforme l'écarte (les 15 sites OIOI web que le
  recensement prenait pour i-web) ;
- les **pages** : la liste des Séances (celle que la sonde lit), la page des Objets ou des préavis, la page des
  membres ; d'abord celles déjà déclarées, puis la page du conseil et quelques liens de son menu (`ESSAIS` au plus par
  sorte de page) ;
- la **variante**, d'où vient le niveau ;
- le **nombre de requêtes** que la commune coûtera au passage ordinaire, face au plafond de 60 (`robots.txt` et
  sonde compris) : il est compté en passant les pages lues au module de lecture de la plateforme, sans réseau (une
  page d'une Séance ou d'un Objet de la fenêtre compte pour deux requêtes, son lien stable étant redirigé).

Trois opérations :

- `verifier_declarations` : les règles de déclaration, sans réseau (les tests de CI les passent sur le fichier réel) ;
- `verifier` : remesure les communes déjà déclarées d'une plateforme et rend les écarts, sans rien écrire ;
- `brouillon` : remesure des communes candidates (le recensement, ou les communes déjà déclarées) et rend le
  brouillon de leurs sources, à relire commune par commune avant la PR.

Lancé à la main, jamais par le cron. Usage (depuis `pipeline/`) :

    uv run python preparation_sources.py i-web --verifier                 # revérifie sources.json, sans l'écrire
    uv run python preparation_sources.py i-web --recensement sites.csv    # brouillon d'après le recensement
    uv run python preparation_sources.py i-web                            # brouillon des communes déjà déclarées
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import re
import socket
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

import lecture_iweb
from robot_communal import PLAFOND, ErreurHttp, PageNonLue, Reponse, Robot
from schema import RACINE, FichierSources, Plateforme, Site, Source, lire_sources
from sites_communaux import debut_de_fenetre

ESSAIS = 3  # liens du menu essayés au plus, par sorte de page
LICENCE = "Actes officiels (art. 5 LDA) : métadonnées et liens seulement"
# Les communes qui disparaissent au 1er janvier 2027 ne sont pas déclarées (spec de J3, « Sources communales »).
NON_DECLAREES = {5873: "Le Lieu", 5675: "Lucens"}


# --- Règles de déclaration, sans réseau -------------------------------------------------------------------------


def verifier_declarations(chemin_sources: Path, chemin_communes: Path) -> list[str]:
    """Les écarts de `sources.json` aux règles de déclaration, sans réseau : chaque n° OFS déclaré existe dans
    `communes.json` ; un conseil n'a qu'une source ; la plateforme et la variante citées sont déclarées et permettent
    le niveau ; une commune non couverte a une raison et pas de conseil ; une commune couverte d'une plateforme a un
    conseil, une variante et une page `seances`. Liste vide : tout est juste."""
    try:
        fichier = lire_sources(chemin_sources)
    except ValidationError as e:
        return [f"sources.json invalide : {e}"]
    communes = {c["bfs"] for c in json.loads(chemin_communes.read_text(encoding="utf-8"))}
    return _ecarts(fichier, communes)


def _ecarts(fichier: FichierSources, communes: set[int]) -> list[str]:
    ecarts: list[str] = []
    conseils: dict[str, list[str]] = defaultdict(list)
    plateformes = {p.id: p for p in fichier.plateformes}
    for s in fichier.sources:
        declares = []
        if s.couverture is not None and s.couverture.communes != "canton":
            declares += s.couverture.communes
        if s.conseil is not None:
            conseils[s.conseil.cle].append(s.id)
            if s.conseil.commune is not None:
                declares.append(s.conseil.commune)
        ecarts += [f"{s.id} : n° OFS {o} absent de communes.json" for o in dict.fromkeys(declares) if o not in communes]
        non_couverte = s.couverture is not None and s.couverture.mode == "non_couvert"
        if non_couverte and (s.couverture.raison is None or s.conseil is not None):
            ecarts.append(f"{s.id} : une commune non couverte a une raison et pas de conseil")
        if s.site is None:
            continue
        plateforme = plateformes.get(s.site.plateforme)
        if plateforme is None:
            ecarts.append(f"{s.id} : plateforme {s.site.plateforme} non déclarée")
            continue
        if non_couverte:
            continue
        if s.conseil is None:
            ecarts.append(f"{s.id} : une commune couverte déclare son conseil")
            continue
        if s.site.variante is None or s.site.seances is None:
            ecarts.append(f"{s.id} : une commune couverte déclare sa variante et sa page des Séances")
            continue
        variante = next((v for v in plateforme.variantes if v.id == s.site.variante), None)
        if variante is None:
            ecarts.append(f"{s.id} : variante {s.site.variante} non déclarée dans {plateforme.id}")
        elif sorted(s.conseil.donne) not in [sorted(n) for n in variante.niveaux]:
            ecarts.append(
                f"{s.id} : la variante {plateforme.id}/{variante.id} ne permet pas le niveau "
                + " + ".join(sorted(s.conseil.donne))
            )
    ecarts += [
        f"conseil {cle} déclaré par plusieurs sources : {', '.join(ids)}" for cle, ids in conseils.items() if len(ids) > 1
    ]
    return ecarts


# --- Candidats et mesures ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidat:
    """Une commune dont on mesure le site : sa page du conseil (l'attribution), et les pages déjà déclarées."""

    ofs: int
    commune: str
    conseil: str  # « Conseil communal » ou « Conseil général »
    page: str  # page du conseil sur le site de la commune
    declare: Site | None = None


@dataclass
class Mesure:
    """Ce que le site d'un candidat montre. `plateforme` : celle mesurée, `None` si la page du conseil n'a pas été lue
    (`remarques` dit pourquoi), « autre » si elle n'est pas celle qu'on mesure."""

    plateforme: str | None
    variante: str | None = None
    seances: str | None = None
    objets: str | None = None
    membres: str | None = None
    requetes: int | None = None  # au passage ordinaire, sonde comprise
    remarques: list[str] = field(default_factory=list)


class _Lecteur:
    """Le robot, avec la mémoire des pages lues : une page n'est demandée qu'une fois par lancement."""

    def __init__(self, robot: Robot) -> None:
        self._robot = robot
        self.pages: dict[str, Reponse | PageNonLue] = {}

    def lire(self, url: str) -> Reponse | PageNonLue:
        if url not in self.pages:
            try:
                self.pages[url] = self._robot.lire(url, "import")
            except PageNonLue as e:
                self.pages[url] = e
        return self.pages[url]

    def texte(self, url: str) -> str | None:
        page = self.lire(url)
        return page.texte if isinstance(page, Reponse) else None


def _motif(erreur: PageNonLue) -> str:
    return f"HTTP {erreur.statut}" if isinstance(erreur, ErreurHttp) else str(erreur)


# --- i-web ------------------------------------------------------------------------------------------------------

_TRACE_IWEB = re.compile(r"icms|/_rt[er]/")
_TABLEAU_SEANCES = re.compile(r"""id=["']icmsTable(?:Past|Future)Sitzungen["']""")
_TABLEAU_OBJETS = re.compile(r"""id=["']icmsTable-geschaefteList["']""")
_TABLEAU_MEMBRES = re.compile(r"""id=["']icmsTable-personList["']""")
_LIENS = {
    "seances": re.compile(r"s[ée]ances?|sitzung", re.I),
    "objets": re.compile(r"objets?[ -]?politiques|geschaefte|pr[ée]avis", re.I),
    "membres": re.compile(r"membres|composition|conseill[eè]re?s|bureau", re.I),
}


def _mesurer_iweb(lecteur: _Lecteur, candidat: Candidat, plateforme: Plateforme, jour: date) -> Mesure:
    conseil = lecteur.lire(candidat.page)
    if isinstance(conseil, PageNonLue):
        return Mesure(None, remarques=[f"page du conseil {candidat.page} non lue ({_motif(conseil)})"])
    if not _TRACE_IWEB.search(conseil.texte):
        return Mesure("autre", remarques=[f"aucune trace d'i-web sur {candidat.page}"])
    mesure = Mesure(plateforme.id)
    declare = candidat.declare or Site(plateforme=plateforme.id)
    liens = _liens(conseil.texte, conseil.url)

    def chercher(sorte: str, deja: list[str | None], trouve: Callable[[str, str], bool]) -> str | None:
        essais = [u for u in deja if u] + [u for u, texte in liens if _LIENS[sorte].search(f"{u} {texte}")][:ESSAIS]
        for url in dict.fromkeys(essais):
            texte = lecteur.texte(url)
            if texte is not None and trouve(url, texte):
                return url
        return None

    mesure.seances = chercher("seances", [declare.seances, candidat.page], lambda _, t: bool(_TABLEAU_SEANCES.search(t)))
    if mesure.seances is None:
        mesure.remarques.append("aucune page des Séances i-web trouvée")
        return mesure
    marqueurs = {v.marqueur for v in plateforme.variantes}
    if not any(m in (lecteur.texte(mesure.seances) or "") for m in marqueurs):
        mesure.remarques.append(f"la page des Séances n'a pas le marqueur de la sonde ({', '.join(sorted(marqueurs))})")

    def preavis_rediges(url: str, texte: str) -> bool:
        if "préavis" not in texte.lower():
            return False
        essai = _source_de_mesure(candidat, mesure.seances, "pages", url, None)
        bruts = _lire_sans_reseau(lecteur, essai, None)[1]
        return bruts is not None and bool(bruts.objets)

    pages_preavis: list[str] = []

    def objets_ou_preavis(url: str, texte: str) -> bool:
        if _TABLEAU_OBJETS.search(texte):
            return True
        if not pages_preavis and preavis_rediges(url, texte):
            pages_preavis.append(url)
        return False

    mesure.objets = chercher("objets", [declare.objets, mesure.seances, candidat.page], objets_ou_preavis)
    if mesure.objets is not None:
        mesure.variante = "objets"
    elif pages_preavis:
        mesure.variante, mesure.objets = "pages", pages_preavis[0]
    else:
        mesure.variante = "seances"
    mesure.membres = chercher("membres", [declare.membres, candidat.page], lambda _, t: bool(_TABLEAU_MEMBRES.search(t)))
    source = _source_de_mesure(candidat, mesure.seances, mesure.variante, mesure.objets, mesure.membres)
    mesure.requetes, bruts = _lire_sans_reseau(lecteur, source, debut_de_fenetre(jour))
    if bruts is None:
        mesure.remarques.append("la liste ne se lit pas par le module de lecture")
    elif mesure.requetes > PLAFOND:
        mesure.remarques.append(f"{mesure.requetes} requêtes au passage ordinaire, au-delà du plafond de {PLAFOND}")
    return mesure


class _Liens(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.liens: list[tuple[str, str]] = []
        self._ouvert: list[str] | None = None
        self._href = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._ouvert = dict(attrs).get("href") or "", []

    def handle_data(self, data):
        if self._ouvert is not None:
            self._ouvert.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._ouvert is not None:
            self.liens.append((self._href, " ".join(" ".join(self._ouvert).split())))
            self._ouvert = None


def _liens(texte: str, url: str) -> list[tuple[str, str]]:
    """Les liens de la page vers d'autres pages du même site (ni éléments, ni documents, ni pages techniques), dans
    l'ordre de la page, chacun une fois : (URL absolue, texte du lien)."""
    analyse = _Liens()
    analyse.feed(texte)
    hote, vus, liens = urlsplit(url).hostname, set(), []
    for href, libelle in analyse.liens:
        absolu = urljoin(url, href).split("#")[0]
        parties = urlsplit(absolu)
        if parties.scheme not in ("http", "https") or parties.hostname != hote or absolu in vus:
            continue
        if re.match(r"/_(rt[er]|doc|docn)/", parties.path) or parties.path in ("", "/"):
            continue
        vus.add(absolu)
        liens.append((absolu, libelle))
    return liens


def _source_de_mesure(
    candidat: Candidat, seances: str, variante: str, objets: str | None, membres: str | None
) -> Source:
    donne = NIVEAUX[variante]
    return Source.model_validate(
        {
            "id": f"site-{candidat.ofs}",
            "nom": candidat.commune,
            "nom_court": candidat.commune,
            "attribution": {"texte": candidat.commune, "lien": candidat.page, "licence": LICENCE},
            "voie_acces": "cron",
            "fraicheur": "import",
            "conseil": {"body_key": str(candidat.ofs), "donne": donne},
            "site": {"plateforme": "i-web", "variante": variante, "seances": seances, "objets": objets,
                     "membres": membres},
        }
    )


class _RobotSansReseau:
    """Un robot qui rend les pages déjà lues et compte les requêtes que le passage ordinaire ferait : deux pour une
    page redirigée (lien stable d'une Séance ou d'un Objet), une sinon. Une page jamais lue est rendue vide."""

    def __init__(self, pages: dict[str, Reponse | PageNonLue]) -> None:
        self._pages = pages
        self.requetes = 0

    def lire(self, url: str, role: str) -> Reponse:
        page = self._pages.get(url)
        if isinstance(page, PageNonLue):
            self.requetes += 1
            raise page
        if page is None:
            self.requetes += 2 if "/_rte/" in url else 1
            return Reponse(url, 200, "", {})
        self.requetes += 1 if page.url == url else 2
        return page


def _lire_sans_reseau(lecteur: _Lecteur, source: Source, depuis: date | None):
    """Le conseil de `source` lu par le module de lecture sur les pages déjà lues : (requêtes du passage ordinaire,
    `robots.txt` et sonde compris ; `Bruts`, ou `None` si la lecture échoue). Le journal du module est tu."""
    robot = _RobotSansReseau(lecteur.pages)
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            bruts = lecture_iweb.lire(robot, source, depuis)  # type: ignore[arg-type]
        except (ValueError, PageNonLue):
            bruts = None
    return robot.requetes + 2, bruts  # `robots.txt` et la sonde, lus avant l'import


MESURES: dict[str, Callable[[_Lecteur, Candidat, Plateforme, date], Mesure]] = {"i-web": _mesurer_iweb}
NIVEAUX = {"seances": ["seances"], "objets": ["objets", "seances"], "pages": ["preavis", "seances"]}


def _mesurer(lecteur: _Lecteur, candidat: Candidat, plateforme: Plateforme, jour: date) -> Mesure:
    if plateforme.id not in MESURES:
        raise ValueError(f"aucune mesure pour la plateforme {plateforme.id}")
    return MESURES[plateforme.id](lecteur, candidat, plateforme, jour)


# --- Vérification -----------------------------------------------------------------------------------------------


def verifier(robot: Robot, fichier: FichierSources, id_plateforme: str, jour: date) -> list[str]:
    """Remesure les communes de `fichier` déclarées sur la plateforme `id_plateforme` et rend leurs écarts au site,
    sans rien écrire : plateforme, page des Séances (et son marqueur), variante, pages des Objets et des membres,
    requêtes au passage ordinaire face au plafond ; pour une commune non couverte, une page des Séances apparue."""
    plateforme = next(p for p in fichier.plateformes if p.id == id_plateforme)
    lecteur = _Lecteur(robot)
    ecarts = []
    for source in fichier.sources:
        if source.site is None or source.site.plateforme != id_plateforme:
            continue
        candidat = _candidat_de_source(source)
        mesure = _mesurer(lecteur, candidat, plateforme, jour)
        ecarts += [f"{source.id} ({candidat.commune}) : {e}" for e in _comparer(source, mesure, plateforme)]
    return ecarts


def _comparer(source: Source, mesure: Mesure, plateforme: Plateforme) -> list[str]:
    if mesure.plateforme is None:
        return mesure.remarques
    if mesure.plateforme != plateforme.id:
        return [f"le site n'est pas sur {plateforme.nom} ({'; '.join(mesure.remarques)})"]
    site = source.site
    if source.conseil is None:
        if mesure.seances is None:
            return []
        return [f"non couverte, mais une page des Séances est mesurée : {mesure.seances}"]

    def ecart(libelle: str, declaree: str | None, mesuree: str | None) -> list[str]:
        if declaree == mesuree:
            return []
        return [f"{libelle} déclarée {declaree or 'aucune'}, mesurée {mesuree or 'aucune'}"]

    ecarts = ecart("page des Séances", site.seances, mesure.seances)
    if mesure.seances is None:
        return ecarts
    ecarts += mesure.remarques  # page des Séances trouvée : marqueur absent, liste illisible, plafond dépassé
    if site.variante != mesure.variante:
        ecarts.append(f"variante déclarée {site.variante}, mesurée {mesure.variante}")
    ecarts += ecart("page des Objets", site.objets, mesure.objets)
    ecarts += ecart("page des membres", site.membres, mesure.membres)
    return ecarts


def _candidat_de_source(source: Source) -> Candidat:
    commune = re.sub(r"^Commune d(?:e |')", "", source.attribution.texte)
    conseil = "Conseil général" if source.nom.startswith("Conseil général") else "Conseil communal"
    ofs = source.couverture.communes[0] if source.couverture and source.couverture.communes != "canton" else 0
    return Candidat(ofs, commune, conseil, str(source.attribution.lien), source.site)


# --- Brouillon --------------------------------------------------------------------------------------------------


def brouillon(
    robot: Robot, candidats: Sequence[Candidat], plateforme: Plateforme, jour: date
) -> tuple[list[dict], dict[str, list[str]]]:
    """Remesure les `candidats` et rend le brouillon de leurs sources (au format de `sources.json`), avec les
    remarques à relire par source. Un candidat qui n'est pas sur la plateforme, ou dont la page du conseil ne se lit
    pas, n'est pas déclaré ; un candidat sans page des Séances est proposé non couvert, raison à relire."""
    lecteur = _Lecteur(robot)
    sources, remarques = [], {}
    for candidat in candidats:
        mesure = _mesurer(lecteur, candidat, plateforme, jour)
        cle = f"site-{candidat.ofs}"
        if mesure.plateforme != plateforme.id:
            pourquoi = f"pas sur {plateforme.nom} ({'; '.join(mesure.remarques)})" if mesure.plateforme else (
                "; ".join(mesure.remarques)
            )
            remarques[cle] = [f"{candidat.commune} : {pourquoi}, non déclarée"]
            continue
        sources.append(_declaration(candidat, mesure, plateforme))
        if mesure.seances is None:
            remarques[cle] = [f"{candidat.commune} : aucune page des Séances {plateforme.nom} trouvée ; raison à relire"]
        elif mesure.remarques:
            remarques[cle] = [f"{candidat.commune} : {r}" for r in mesure.remarques]
    return sources, remarques


def _de(nom: str) -> str:
    return f"d'{nom}" if nom[0].upper() in "AEIOUYÉÈÊÂÎÔ" else f"de {nom}"


def _declaration(candidat: Candidat, mesure: Mesure, plateforme: Plateforme) -> dict:
    """La source d'une commune mesurée, au format de `sources.json` (spec de J3, « Sources communales »)."""
    source = {
        "id": f"site-{candidat.ofs}",
        "nom": f"{candidat.conseil} {_de(candidat.commune)} (site de la commune)",
        "nom_court": f"Site {_de(candidat.commune)}",
        "attribution": {"texte": f"Commune {_de(candidat.commune)}", "lien": candidat.page, "licence": LICENCE},
        "voie_acces": "cron",
        "fraicheur": "import",
    }
    if mesure.seances is None:
        source["couverture"] = {"communes": [candidat.ofs], "mode": "non_couvert", "raison": "rien_en_ligne"}
        source["site"] = {"plateforme": plateforme.id}
        return source
    source["couverture"] = {"communes": [candidat.ofs], "mode": "scrape"}
    source["conseil"] = {"body_key": str(candidat.ofs), "donne": NIVEAUX[mesure.variante]}
    pages = {"seances": mesure.seances, "objets": mesure.objets, "membres": mesure.membres}
    source["site"] = {"plateforme": plateforme.id, "variante": mesure.variante} | {
        k: v for k, v in pages.items() if v is not None
    }
    return source


def candidats_du_recensement(chemin: Path, id_plateforme: str) -> list[Candidat]:
    """Les communes que le recensement des sites communaux (#118, `sites-communaux.csv`) met sur la plateforme, sauf
    celles qui disparaissent au 1er janvier 2027. Sans page du conseil relevée, la page d'accueil en tient lieu."""
    with chemin.open(encoding="utf-8", newline="") as f:
        lignes = [r for r in csv.DictReader(f) if r["plateforme"] == id_plateforme]
    return [
        Candidat(
            int(r["ofs"]),
            r["commune"],
            "Conseil général" if r["conseil"] == "conseil général" else "Conseil communal",
            r["page_conseil"] or r["url_finale"],
        )
        for r in lignes
        if int(r["ofs"]) not in NON_DECLAREES
    ]


# --- Ligne de commande ------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("plateforme", help="identifiant de la plateforme (`i-web`)")
    parser.add_argument("--sources", type=Path, default=RACINE / "sources.json", help="déclaration des sources")
    parser.add_argument("--verifier", action="store_true", help="revérifie sources.json sans l'écrire")
    parser.add_argument("--recensement", type=Path, help="candidats : le CSV du recensement des sites communaux")
    parser.add_argument("--sortie", type=Path, help="fichier du brouillon (défaut : brouillon-sources-<plateforme>.json)")
    args = parser.parse_args(argv)
    communes = RACINE / "web" / "static" / "communes.json"
    if args.verifier:
        hors_ligne = verifier_declarations(args.sources, communes)
        for e in hors_ligne:
            print(e)
        if hors_ligne:
            return 1
    fichier = lire_sources(args.sources)
    plateforme = next((p for p in fichier.plateformes if p.id == args.plateforme), None)
    if plateforme is None:
        print(f"plateforme {args.plateforme} absente de la section `plateformes` de {args.sources}", file=sys.stderr)
        return 2
    jour = datetime.now(ZoneInfo("Europe/Lausanne")).date()
    with httpx.Client() as http:
        robot = Robot(http, lambda: datetime.now(UTC), time.sleep, socket.gethostbyname)
        if args.verifier:
            ecarts = verifier(robot, fichier, plateforme.id, jour)
            for e in ecarts:
                print(e)
            print(f"{len(ecarts)} écart(s)", file=sys.stderr)
            return 1 if ecarts else 0
        if args.recensement:
            candidats = candidats_du_recensement(args.recensement, plateforme.id)
        else:
            candidats = [_candidat_de_source(s) for s in fichier.sources if s.site and s.site.plateforme == plateforme.id]
        sources, remarques = brouillon(robot, candidats, plateforme, jour)
    sortie = args.sortie or Path(f"brouillon-sources-{plateforme.id}.json")
    sortie.write_text(
        json.dumps({"sources": sources, "remarques": remarques}, ensure_ascii=False, indent="\t") + "\n", "utf-8"
    )
    print(f"{sortie} : {len(sources)} source(s), {len(remarques)} à relire", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
