"""Partie terrestre des communes : leurs limites moins les lacs de swissTLMRegio (© swisstopo, OGD).

Sert au repli de l'hôtel de ville (un point garanti en terre ferme) et, plus tard, au cadrage de la carte.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import httpx
from shapely import union_all
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import polylabel

import reference
from telechargement import telecharger

COUCHE_LACS = "tlmregio_hydrography_lake"


def edition_lacs() -> str:
    return f"swisstlmregio_{reference.EDITION_LACS}"


def url_lacs() -> str:
    edition = edition_lacs()
    return f"https://data.geo.admin.ch/ch.swisstopo.swisstlmregio/{edition}/{edition}_2056.gpkg.zip"


def charger_lacs(client: httpx.Client, cache: Path) -> gpd.GeoSeries:
    """Les lacs de swissTLMRegio en LV95 (téléchargés une fois dans `cache`, rangés par édition)."""
    dossier = cache / edition_lacs()
    produits = list(dossier.glob("swissTLMRegio_Product*.gpkg"))
    if not produits:
        archive = telecharger(client, url_lacs(), dossier / "swisstlmregio.gpkg.zip")
        with zipfile.ZipFile(archive) as z:
            for nom in z.namelist():
                if Path(nom).name.startswith("swissTLMRegio_Product"):
                    z.extract(nom, dossier)
                    (dossier / nom).rename(dossier / Path(nom).name)
        archive.unlink()
        produits = list(dossier.glob("swissTLMRegio_Product*.gpkg"))
    lacs = gpd.read_file(produits[0], layer=COUCHE_LACS).geometry.force_2d()
    return lacs.set_crs(2056, allow_override=True)


def partie_terrestre(limites: BaseGeometry, lacs: gpd.GeoSeries) -> BaseGeometry:
    touches = lacs.iloc[lacs.sindex.query(limites, predicate="intersects")]
    return limites.difference(union_all(touches.values)) if len(touches) else limites


def point_repli(limites: BaseGeometry, lacs: gpd.GeoSeries) -> Point:
    """Le pôle d'inaccessibilité du plus grand morceau de la partie terrestre : jamais dans un lac."""
    terre = partie_terrestre(limites, lacs)
    morceaux = getattr(terre, "geoms", [terre])
    plus_grand = max((m for m in morceaux if m.geom_type == "Polygon"), key=lambda m: m.area)
    return polylabel(plus_grand, tolerance=1)
