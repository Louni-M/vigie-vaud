"""Le socle des modules de lecture des plateformes (ADR 0010) : ce que chaque module écrirait sinon pour lui-même, sans
rien d'une plateforme. Un nouveau module de lecture s'y appuie pour :

- noter dans le journal du passage un élément sauté (`journal`) ;
- ouvrir `lire` : la source a ses blocs `site` et `conseil`, et une variante que le module lit (`site_et_conseil`) ;
- compter les requêtes de `lire` pour le script de préparation des sources (`requetes`), avec le robot qu'il choisit
  (`mesure_sites`) ;
- lire une date en chiffres (« 10.09.2026 ») et une heure (« 19h30 », « 19 h 30 ») ;
- rendre une Séance, un point de son ordre du jour et un document à la forme d'OpenParlData (`meeting`, `point`,
  `document`), réduits aux champs que l'import lit, sans identifiant.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from datetime import date

from bruts import Bruts
from mesure_sites import RobotCompteur, sans_journal
from robot_communal import PageNonLue, Robot
from schema import Conseil, Site, Source


def journal(nom: str, message: str) -> None:
    """Note dans le journal du passage un élément sauté du conseil `nom` (le nom de sa source)."""
    print(f"{nom} : élément sauté, {message}", file=sys.stderr)


def site_et_conseil(source: Source, plateforme: str, variantes: tuple[str, ...]) -> tuple[Site, Conseil]:
    """Les blocs `site` et `conseil` de `source`, que lit le module de la plateforme `plateforme` (son nom, pour le
    message). Lève `ValueError` s'il en manque un, ou pour une variante hors de `variantes`, celles que le module lit."""
    site, conseil = source.site, source.conseil
    if site is None or conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    if site.variante not in variantes:
        raise ValueError(f"{source.id} : variante {plateforme} {site.variante} non lue")
    return site, conseil


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
