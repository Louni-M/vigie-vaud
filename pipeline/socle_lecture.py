"""Le socle des modules de lecture des plateformes (ADR 0010) : ce que chaque module écrirait sinon pour lui-même, sans
rien d'une plateforme. Un nouveau module de lecture s'y appuie pour :

- se déclarer, lui et ses variantes, en un seul endroit (`PlateformeLue`, `VarianteLue`) : la sonde, l'import, la
  mesure des sites et le script de préparation des sources ne lisent que cette déclaration ;
- noter dans le journal du passage un élément sauté (`journal`) ;
- ouvrir la lecture d'une source : ses blocs `site` et `conseil`, et une variante que le module lit (`PlateformeLue.lire`) ;
- compter les requêtes de la lecture pour le script de préparation des sources (`PlateformeLue.requetes`), avec le
  robot qu'il choisit (`mesure_sites`) ;
- lire une date en chiffres (« 10.09.2026 ») et une heure (« 19h30 », « 19 h 30 ») ;
- rendre une Séance, un point de son ordre du jour et un document à la forme d'OpenParlData (`meeting`, `point`,
  `document`), réduits aux champs que l'import lit, sans identifiant.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from bruts import Bruts
from mesure_sites import Mesure, PagesLues, RobotCompteur, sans_journal
from robot_communal import PageNonLue, Robot
from schema import Conseil, DonneeConseil, Site, Source

# --- Déclaration d'une plateforme ---------------------------------------------------------------------------------

# Le conseil d'une source, lu par une variante : son robot, la source, ses blocs `site` et `conseil`, et le début de la
# fenêtre (`None` : tout).
LectureDeVariante = Callable[[Robot, Source, Site, Conseil, date | None], Bruts]
# Ce que la mesure tire d'une page qui pourrait être la page des Séances d'une variante : son URL et son texte, avec les
# liens de la page du conseil tels que la mesure de sa plateforme les retient ((URL, texte), d'après
# `mesure_sites.liens`). Une `Mesure` si la page est celle de la variante (la mesure de la plateforme y reporte sa
# plateforme et sa variante), une remarque si elle en a l'air sans se lire (Quicksite : une recherche `coreapi` d'une
# autre vue), sinon `None`.
Reconnaissance = Callable[[PagesLues, str, str, list[tuple[str, str]]], Mesure | str | None]


@dataclass(frozen=True)
class VarianteLue:
    """Une variante d'une plateforme (GLOSSARY.md), déclarée une fois dans le module de lecture de sa plateforme :
    le marqueur que la sonde cherche sur sa page de liste des Séances, les niveaux qu'elle permet (du plus complet au
    moins complet), sa lecture et sa reconnaissance par la mesure des sites."""

    id: str
    marqueur: str
    niveaux: tuple[tuple[DonneeConseil, ...], ...]
    lire: LectureDeVariante
    reconnaitre: Reconnaissance


@dataclass(frozen=True)
class PlateformeLue:
    """Une plateforme, déclarée une fois dans son module de lecture (`PLATEFORME`) et inscrite dans
    `sites_communaux.PLATEFORMES` : son nom et son éditeur, ses variantes (dans l'ordre où la mesure les essaie sur une
    même page), et ce que la mesure de ses sites a de propre à la plateforme : `mesure`, qui trouve les pages d'une
    commune et y essaie les variantes de la plateforme qu'on lui passe, et `robot_de_mesure`, le robot qui rejoue sa
    lecture pour en compter les requêtes (`RobotSansReseau` ou `RobotCompteur`).

    La section `plateformes` de `sources.json`, que lit le site, en est la copie (`declaration`), vérifiée par les
    tests."""

    id: str
    nom: str
    editeur: str
    variantes: tuple[VarianteLue, ...]
    mesure: Callable[[PagesLues, str, Site, PlateformeLue], Mesure]
    robot_de_mesure: Callable[[PagesLues], RobotCompteur]

    def variante(self, id_variante: str | None) -> VarianteLue | None:
        """La variante déclarée sous cet identifiant, ou `None`."""
        return next((v for v in self.variantes if v.id == id_variante), None)

    def lire(self, robot: Robot, source: Source, depuis: date | None) -> Bruts:
        """Le conseil de `source` lu sur son site par sa variante, dans la fenêtre qui part de `depuis` (`None` :
        tout). Lève `ValueError` s'il manque à la source un bloc `site` ou `conseil`, ou pour une variante que la
        plateforme ne déclare pas."""
        site, conseil = source.site, source.conseil
        if site is None or conseil is None:
            raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
        variante = self.variante(site.variante)
        if variante is None:
            raise ValueError(f"{source.id} : variante {self.nom} {site.variante} non lue")
        return variante.lire(robot, source, site, conseil, depuis)

    def mesurer(self, pages: PagesLues, page_du_conseil: str, declare: Site) -> Mesure:
        """Pour le script de préparation des sources : la plateforme réelle, la variante et les pages du site d'une
        commune, d'après sa page du conseil (déjà lue) et ses pages déjà déclarées. Le niveau et les requêtes sont
        l'affaire du script."""
        return self.mesure(pages, page_du_conseil, declare, self)

    def requetes(self, pages: PagesLues, source: Source, depuis: date | None) -> int | None:
        """Pour le script de préparation des sources : les requêtes que la lecture de `source` coûterait au passage
        ordinaire dont la fenêtre part de `depuis`, rejouée sur les pages déjà lues, sans `robots.txt` ni la sonde ;
        `None` si la lecture échoue."""
        return requetes(self.lire, self.robot_de_mesure(pages), source, depuis)

    def declaration(self) -> dict:
        """La plateforme telle que la section `plateformes` de `sources.json` la recopie."""
        return {
            "id": self.id,
            "nom": self.nom,
            "editeur": self.editeur,
            "variantes": [
                {"id": v.id, "marqueur": v.marqueur, "niveaux": [list(n) for n in v.niveaux]} for v in self.variantes
            ],
        }


# --- Journal et requêtes ------------------------------------------------------------------------------------------


def journal(nom: str, message: str) -> None:
    """Note dans le journal du passage un élément sauté du conseil `nom` (le nom de sa source)."""
    print(f"{nom} : élément sauté, {message}", file=sys.stderr)


def requetes(
    lire: Callable[[Robot, Source, date | None], Bruts],
    robot: RobotCompteur,
    source: Source,
    depuis: date | None,
) -> int | None:
    """Les requêtes que `robot` a comptées pendant `lire(robot, source, depuis)`, le journal tu ; `None` si la lecture
    échoue. Le module de lecture choisit son robot : celui des seules pages déjà lues (`RobotSansReseau`), ou celui
    qui lit les pages qui manquent (`RobotCompteur`)."""
    try:
        sans_journal(lambda: lire(robot, source, depuis))  # type: ignore[arg-type]
    except (ValueError, PageNonLue):
        return None
    return robot.requetes


# --- Dates et heures ----------------------------------------------------------------------------------------------

DATE_CHIFFRES = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")  # « 10.09.2026 », « 5.02.2026 »
HEURE = re.compile(r"\b(\d{1,2})\s*h\s*(\d{2})\b")  # « 19h30 », « 19 h 30 »


def jour_en_chiffres(m: re.Match[str]) -> date:
    """Le jour d'une date trouvée par `DATE_CHIFFRES`. Lève `ValueError` pour une date impossible (« 31.02.2026 »)."""
    return date(int(m[3]), int(m[2]), int(m[1]))


def heure_de(texte: str) -> str | None:
    """La première heure de `texte` (« 19h30 », « 9 h 05 »), en « HH:MM » ; `None` s'il n'en donne pas."""
    m = HEURE.search(texte)
    return f"{int(m[1]):02d}:{m[2]}" if m else None


# --- Forme d'OpenParlData -----------------------------------------------------------------------------------------


def meeting(
    nom: str,
    jour: date,
    documents: list[dict],
    *,
    heure: str | None = None,
    lien: str | None = None,
    points: list[dict] | None = None,
) -> dict:
    """Une Séance à la forme d'un *meeting* d'OpenParlData, sans identifiant (ADR 0010) : son nom brut, son jour et
    son heure (« 19:30 ») si le site la donne, sa page propre si elle en a une, les points de son ordre du jour s'il
    est structuré (`point`), et ses documents (`document`)."""
    return {
        "id": None,
        "name": {"fr": nom},
        "begin_date": jour.isoformat() + (f"T{heure}:00" if heure else ""),
        "url_external": {"fr": lien} if lien else None,
        "agendas": {"data": points or []},
        "docs": {"data": documents},
    }


def point(titre: str, *, numero: str | None = None, objet: str | None = None) -> dict:
    """Un point de l'ordre du jour d'une Séance, à la forme d'OpenParlData : son titre, son numéro tel que le site
    l'affiche (« 9.1 ») s'il en a un, et le numéro de l'Objet qu'il cite s'il est importé."""
    return {"item_number_display": numero or None, "item_title": titre, "item_affair_number": objet}


def document(nom: str, lien: str, *, publie: date | None = None, type_: str | None = None) -> dict:
    """Un document, à la forme d'un document d'OpenParlData : son nom, son lien, sa publication et son type si le
    site les donne."""
    return {"name": nom, "url": lien, "date": publie.isoformat() if publie else None, "category": type_}
