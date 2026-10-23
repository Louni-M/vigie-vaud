"""Préparation des sources communales de `sources.json` (spec de J3, « Scripts de préparation » ; ADR 0010).

Les déclarations des communes scrapées ne changent que par une PR, jamais par le cron. Ce script aide à les écrire et à
les tenir justes, en **remesurant les sites d'une plateforme** par le robot communal (ADR 0006 : une requête à la
fois, 5 s au moins par /24, `VigieVaud-import`). La mesure propre à une plateforme est celle de son module de lecture
(`sites_communaux.LECTEURS`, opérations `mesurer` et `requetes`) ; ce script n'en connaît aucune :

- la **plateforme réelle** : une page du conseil sans trace de la plateforme l'écarte (les 15 sites OIOI web que le
  recensement prenait pour i-web) ;
- les **pages** : la liste des Séances (celle que la sonde lit, avec le marqueur de sa variante), la page des Objets
  ou des préavis, la page des membres ;
- la **variante**, et le **niveau** : le plus haut de ceux que la variante permet (section `plateformes`) dont le
  passage ordinaire tient sous le plafond de 60 requêtes, `robots.txt` et sonde compris ; ces requêtes sont comptées
  en rejouant le module de lecture sur les pages lues, sans réseau.

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
import csv
import json
import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from mesure_sites import Mesure, PagesLues
from robot_communal import PLAFOND, ErreurHttp, PageNonLue, Robot, robot_des_sources
from schema import RACINE, FichierSources, Plateforme, Site, Source, lire_sources
from sites_communaux import LECTEURS, debut_de_fenetre

LICENCE = "Actes officiels (art. 5 LDA) : métadonnées et liens seulement"
# Les communes qui disparaissent au 1er janvier 2027 ne sont pas déclarées (spec de J3, « Sources communales »).
NON_DECLAREES = {5873: "Le Lieu", 5675: "Lucens"}
REQUETES_AVANT_L_IMPORT = 2  # `robots.txt` et la sonde, lus avant l'import


# --- Règles de déclaration, sans réseau -------------------------------------------------------------------------


def verifier_declarations(chemin_sources: Path, chemin_communes: Path) -> list[str]:
    """Les écarts de `sources.json` aux règles de déclaration, sans réseau : chaque n° OFS déclaré existe dans
    `communes.json` ; un conseil n'a qu'une source ; la plateforme et la variante citées sont déclarées et permettent
    le niveau ; une commune couverte d'une plateforme a un conseil. Une commune non couverte avec un conseil ou sans
    raison, ou un conseil scrapé sans variante ou sans page des Séances, sont refusés par le schéma lui-même
    (« sources.json invalide »). Liste vide : tout est juste."""
    try:
        fichier = lire_sources(chemin_sources)
    except ValidationError as e:
        return [f"sources.json invalide : {e}"]
    communes = {c["bfs"] for c in json.loads(chemin_communes.read_text(encoding="utf-8"))}
    return _ecarts(fichier, communes)


def _ecarts(fichier: FichierSources, communes: set[int]) -> list[str]:
    ecarts: list[str] = []
    conseils: dict[str, list[str]] = defaultdict(list)
    for s in fichier.sources:
        declares = []
        if s.couverture is not None and s.couverture.communes != "canton":
            declares += s.couverture.communes
        if s.conseil is not None:
            conseils[s.conseil.cle].append(s.id)
            if s.conseil.commune is not None:
                declares.append(s.conseil.commune)
        ecarts += [f"{s.id} : n° OFS {o} absent de communes.json" for o in dict.fromkeys(declares) if o not in communes]
        if s.site is None:
            continue
        plateforme = fichier.plateforme(s.site.plateforme)
        if plateforme is None:
            ecarts.append(f"{s.id} : plateforme {s.site.plateforme} non déclarée")
            continue
        if s.couverture is not None and s.couverture.mode == "non_couvert":
            continue
        if s.conseil is None:
            ecarts.append(f"{s.id} : une commune couverte déclare son conseil")
            continue
        variante = plateforme.variante(s.site.variante)
        if variante is None:
            ecarts.append(f"{s.id} : variante {s.site.variante} non déclarée dans {plateforme.id}")
        elif sorted(s.conseil.donne) not in [sorted(n) for n in variante.niveaux]:
            ecarts.append(
                f"{s.id} : la variante {plateforme.id}/{variante.id} ne permet pas le niveau {_niveau(s.conseil.donne)}"
            )
    ecarts += [
        f"conseil {cle} déclaré par plusieurs sources : {', '.join(ids)}" for cle, ids in conseils.items() if len(ids) > 1
    ]
    return ecarts


def _niveau(donne: Sequence[str]) -> str:
    """« objets + seances » : un niveau, tel que `conseil.donne` l'écrit."""
    return " + ".join(sorted(donne))


# --- Candidats et mesures ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidat:
    """Une commune dont on mesure le site : sa page du conseil (l'attribution), et les pages déjà déclarées."""

    ofs: int
    commune: str
    conseil: str  # « Conseil communal » ou « Conseil général »
    page: str  # page du conseil sur le site de la commune
    declare: Site | None = None


def _motif(erreur: PageNonLue) -> str:
    return f"HTTP {erreur.statut}" if isinstance(erreur, ErreurHttp) else str(erreur)


# Les niveaux plus complets que celui de la mesure, dont le passage ordinaire dépasse le plafond : (niveau, requêtes).
AuDela = list[tuple[list[str], int]]


def _mesurer(pages: PagesLues, candidat: Candidat, plateforme: Plateforme, jour: date) -> tuple[Mesure, AuDela]:
    """Le site du candidat mesuré par le module de lecture de la plateforme, puis son niveau : le premier des niveaux
    de sa variante (section `plateformes`, du plus complet au moins complet) dont le passage ordinaire tient sous le
    plafond, et ceux qui le dépassent."""
    if plateforme.id not in LECTEURS:
        raise ValueError(f"aucun module de lecture pour la plateforme {plateforme.id}")
    module = LECTEURS[plateforme.id]
    au_dela: AuDela = []
    conseil = pages.lire(candidat.page)
    if isinstance(conseil, PageNonLue):
        return Mesure(None, remarques=[f"page du conseil {candidat.page} non lue ({_motif(conseil)})"]), au_dela
    mesure = module.mesurer(pages, candidat.page, candidat.declare or Site(plateforme=plateforme.id), plateforme)
    if mesure.plateforme != plateforme.id or mesure.seances is None:
        return mesure, au_dela
    variante = plateforme.variante(mesure.variante)
    if variante is None:
        mesure.remarques.append(f"variante {mesure.variante} non déclarée dans {plateforme.nom}")
        return mesure, au_dela
    if variante.marqueur not in (pages.texte(mesure.seances) or ""):
        mesure.remarques.append(f"la page des Séances n'a pas le marqueur de la sonde ({variante.marqueur})")
    for niveau in variante.niveaux:
        requetes = module.requetes(pages, _source_de_mesure(candidat, plateforme, mesure, niveau), debut_de_fenetre(jour))
        if requetes is None:
            mesure.remarques.append("la liste ne se lit pas par le module de lecture")
            return mesure, au_dela
        mesure.requetes = requetes + REQUETES_AVANT_L_IMPORT
        if mesure.requetes <= PLAFOND:
            mesure.niveau = list(niveau)
            return mesure, au_dela
        au_dela.append((list(niveau), mesure.requetes))
    mesure.remarques.append(f"{mesure.requetes} requêtes au passage ordinaire, au-delà du plafond de {PLAFOND}")
    return mesure, au_dela


def _source_de_mesure(candidat: Candidat, plateforme: Plateforme, mesure: Mesure, niveau: Sequence[str]) -> Source:
    """La source que déclarerait la mesure, au `niveau` donné : de quoi rejouer le module de lecture."""
    pages = {"seances": mesure.seances, "objets": mesure.objets, "membres": mesure.membres}
    return Source.model_validate(
        {
            "id": f"site-{candidat.ofs}",
            "nom": candidat.commune,
            "nom_court": candidat.commune,
            "attribution": {"texte": candidat.commune, "lien": candidat.page, "licence": LICENCE},
            "voie_acces": "cron",
            "fraicheur": "import",
            "conseil": {"body_key": str(candidat.ofs), "donne": list(niveau)},
            "site": {"plateforme": plateforme.id, "variante": mesure.variante} | pages,
        }
    )


# --- Vérification -----------------------------------------------------------------------------------------------


def verifier(robot: Robot, fichier: FichierSources, id_plateforme: str, jour: date) -> list[str]:
    """Remesure les communes de `fichier` déclarées sur la plateforme `id_plateforme` et rend leurs écarts au site,
    sans rien écrire : plateforme, page des Séances (et son marqueur), variante, niveau, pages des Objets et des
    membres, requêtes au passage ordinaire face au plafond ; pour une commune non couverte, une page des Séances
    apparue."""
    plateforme = fichier.plateforme(id_plateforme)
    if plateforme is None:
        raise ValueError(f"plateforme {id_plateforme} absente de la section `plateformes`")
    pages = PagesLues(robot)
    ecarts = []
    for source in fichier.sources:
        if source.site is None or source.site.plateforme != id_plateforme:
            continue
        candidat = _candidat_de_source(source)
        mesure, au_dela = _mesurer(pages, candidat, plateforme, jour)
        ecarts += [f"{source.id} ({candidat.commune}) : {e}" for e in _comparer(source, mesure, au_dela, plateforme)]
    return ecarts


def _comparer(source: Source, mesure: Mesure, au_dela: AuDela, plateforme: Plateforme) -> list[str]:
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
    elif mesure.niveau is not None and sorted(source.conseil.donne) != sorted(mesure.niveau):
        depasse = {_niveau(n): r for n, r in au_dela}.get(_niveau(source.conseil.donne))
        pourquoi = f" ({depasse} requêtes au passage ordinaire, au-delà du plafond de {PLAFOND})" if depasse else ""
        ecarts.append(f"niveau déclaré {_niveau(source.conseil.donne)}, mesuré {_niveau(mesure.niveau)}{pourquoi}")
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
    pas, n'est pas déclaré ; un candidat sans page des Séances est proposé non couvert, raison à relire ; un candidat
    dont le niveau le plus complet dépasse le plafond est déclaré au niveau qui le tient, et le brouillon le dit."""
    pages = PagesLues(robot)
    sources, remarques = [], {}
    for candidat in candidats:
        mesure, au_dela = _mesurer(pages, candidat, plateforme, jour)
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
            continue
        a_relire = [f"{candidat.commune} : {r}" for r in mesure.remarques]
        if mesure.niveau is not None:
            a_relire += [
                f"{candidat.commune} : {requetes} requêtes au niveau {_niveau(niveau)}, au-delà du plafond de "
                f"{PLAFOND} ; déclarée au niveau {_niveau(mesure.niveau)}"
                for niveau, requetes in au_dela
            ]
        if a_relire:
            remarques[cle] = a_relire
    return sources, remarques


def _de(nom: str) -> str:
    return f"d'{nom}" if nom[0].upper() in "AEIOUYÉÈÊÂÎÔ" else f"de {nom}"


def _declaration(candidat: Candidat, mesure: Mesure, plateforme: Plateforme) -> dict:
    """La source d'une commune mesurée, au format de `sources.json` (spec de J3, « Sources communales ») ; sans niveau
    sous le plafond, le moins complet de sa variante, à relire."""
    source = {
        "id": f"site-{candidat.ofs}",
        "nom": f"{candidat.conseil} {_de(candidat.commune)} (site de la commune)",
        "nom_court": f"Site {_de(candidat.commune)}",
        "attribution": {"texte": f"Commune {_de(candidat.commune)}", "lien": candidat.page, "licence": LICENCE},
        "voie_acces": "cron",
        "fraicheur": "import",
    }
    variante = plateforme.variante(mesure.variante)
    if mesure.seances is None or variante is None:
        source["couverture"] = {"communes": [candidat.ofs], "mode": "non_couvert", "raison": "rien_en_ligne"}
        source["site"] = {"plateforme": plateforme.id}
        return source
    source["couverture"] = {"communes": [candidat.ofs], "mode": "scrape"}
    source["conseil"] = {"body_key": str(candidat.ofs), "donne": mesure.niveau or list(variante.niveaux[-1])}
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
    plateforme = fichier.plateforme(args.plateforme)
    if plateforme is None:
        print(f"plateforme {args.plateforme} absente de la section `plateformes` de {args.sources}", file=sys.stderr)
        return 2
    jour = datetime.now(ZoneInfo("Europe/Zurich")).date()
    with httpx.Client() as http:
        robot = robot_des_sources(http, fichier, lambda: datetime.now(UTC))
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
