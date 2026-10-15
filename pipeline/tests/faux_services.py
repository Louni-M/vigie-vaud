"""Faux services HTTP pour l'outil d'initialisation des hôtels de ville.

Un `Monde` décrit en quelques lignes ce que renverraient swissBOUNDARIES3D, swissTLMRegio, le répertoire
des adresses de bâtiments, l'annuaire de l'UCV et Overpass ; `transport()` le sert à `httpx` sans réseau.
"""

from __future__ import annotations

import csv
import io
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import geopandas as gpd
import httpx
from pyproj import Transformer
from shapely.geometry import Polygon, box

import fetch
import hotels_de_ville as hdv
import terre

COLONNES_ADRESSES = (
    "ADR_EGAID;STR_ESID;BDG_EGID;ADR_EDID;STN_LABEL;ADR_NUMBER;BDG_CATEGORY;BDG_NAME;ZIP_LABEL;COM_FOSNR;"
    "COM_NAME;COM_CANTON;ADR_STATUS;ADR_OFFICIAL;ADR_MODIFIED;ADR_EASTING;ADR_NORTHING"
).split(";")


def carre(e: float, n: float, cote: float = 2000) -> Polygon:
    """Un carré LV95 dont le coin sud-ouest est (e, n)."""
    return box(e, n, e + cote, n + cote)


@dataclass
class Commune:
    ofs: int
    nom: str
    limites: Polygon


@dataclass
class Adresse:
    ofs: int
    rue: str
    numero: str
    localite: str  # « 1123 Aclens »
    egid: int
    e: float
    n: float
    statut: str = "real"


@dataclass
class Fiche:
    """Une page commune de l'annuaire de l'UCV."""

    nom: str
    ofs: int
    lignes: list[str]  # bloc d'adresse, tel qu'affiché
    coordonnees: str = "0 - 0"  # « Coordonnées CH » en LV03, « 528800 - 157800 »


@dataclass
class Townhall:
    nom: str | None
    e: float
    n: float


@dataclass
class Monde:
    communes: list[Commune]
    fiches: list[Fiche] = field(default_factory=list)
    adresses: list[Adresse] = field(default_factory=list)
    lacs: list[Polygon] = field(default_factory=list)
    townhalls: list[Townhall] = field(default_factory=list)
    requetes: list[httpx.Request] = field(default_factory=list)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._repondre)

    def _repondre(self, requete: httpx.Request) -> httpx.Response:
        self.requetes.append(requete)
        url = str(requete.url)
        if url == fetch.BOUNDARIES_URL:
            return httpx.Response(200, content=self._limites())
        if url == terre.LACS_URL:
            return httpx.Response(200, content=self._lacs())
        if url == hdv.ADRESSES_URL:
            return httpx.Response(200, content=self._adresses())
        if url == hdv.UCV_LISTE:
            return httpx.Response(200, text=self._liste_ucv())
        if url.startswith(hdv.UCV_LISTE + "/commune/"):
            for f in self.fiches:
                if requete.url.path.endswith("/commune/" + f.nom):
                    return httpx.Response(200, text=_page_ucv(f))
            return httpx.Response(404)
        if url == hdv.OVERPASS_URL and requete.method == "POST":
            return httpx.Response(200, json=self._overpass())
        return httpx.Response(404)

    def _limites(self) -> bytes:
        gdf = gpd.GeoDataFrame(
            {
                "kantonsnummer": [22] * len(self.communes),
                "objektart": ["Gemeindegebiet"] * len(self.communes),
                "bfs_nummer": [c.ofs for c in self.communes],
                "name": [c.nom for c in self.communes],
                "einwohnerzahl": [1000] * len(self.communes),
            },
            geometry=[c.limites for c in self.communes],
            crs=2056,
        )
        return _gpkg_zip(gdf, "tlm_hoheitsgebiet", "swissBOUNDARIES3D_1_5_LV95_LN02.gpkg")

    def _lacs(self) -> bytes:
        gdf = gpd.GeoDataFrame({"objval": ["See"] * len(self.lacs)}, geometry=self.lacs, crs=2056)
        return _gpkg_zip(gdf, "tlmregio_hydrography_lake", "swissTLMRegio_Product_LV95.gpkg")

    def _adresses(self) -> bytes:
        texte = io.StringIO()
        w = csv.writer(texte, delimiter=";", lineterminator="\n")
        w.writerow(COLONNES_ADRESSES)
        for i, a in enumerate(self.adresses):
            nom = next((c.nom for c in self.communes if c.ofs == a.ofs), "Ailleurs")
            w.writerow(
                [100000 + i, 200000 + i, a.egid, 0, a.rue, a.numero, "residential", "", a.localite, a.ofs,
                 nom, "VD", a.statut, "true", "15.11.2024", a.e, a.n]
            )
        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w") as z:
            z.writestr("amtliches-gebaeudeadressverzeichnis_ch_2056.csv", "﻿" + texte.getvalue())
        return tampon.getvalue()

    def _liste_ucv(self) -> str:
        liens = "".join(
            f'<li><a href="/annuaire/recherche-par-localite/commune/{quote(f.nom)}">{f.nom}</a></li>'
            for f in self.fiches
        )
        return f'<html><body><a href="/annuaire/fusions">Fusions</a><ul>{liens}</ul></body></html>'

    def _overpass(self) -> dict:
        vers_wgs = Transformer.from_crs(2056, 4326, always_xy=True)
        elements = []
        for i, t in enumerate(self.townhalls):
            lon, lat = vers_wgs.transform(t.e, t.n)
            tags = {"amenity": "townhall"} | ({"name": t.nom} if t.nom else {})
            elements.append({"type": "node", "id": i + 1, "lat": lat, "lon": lon, "tags": tags})
        return {"osm3s": {"timestamp_osm_base": "2026-10-14T20:51:34Z"}, "elements": elements}


def _gpkg_zip(gdf: gpd.GeoDataFrame, couche: str, nom: str) -> bytes:
    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / nom
        gdf.to_file(chemin, layer=couche, driver="GPKG")
        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w") as z:
            z.write(chemin, nom)
        return tampon.getvalue()


def _page_ucv(f: Fiche) -> str:
    bloc = "\n".join(f"            <div>{ligne}</div>" for ligne in f.lignes)
    return f"""<html><body>
<div class="container_annaire"  >
    <div class="row">
        <h1>{f.nom}</h1>
    </div>
    <div class="row section">
        <div class="col-md-3 col-sm-4 col-xs-6">
            <img id="armoirie" src="armoiries.png" alt="" />
        </div>
        <div class="col-md-4 col-sm-4 col-xs-6">
{bloc}
            <div>Tél: 021 000 00 00</div>
            <div></div>
            <div><a target="_blank" href="https://www.exemple.ch">www.exemple.ch</a></div>
            <div class="social-media-commune">  </div>
        </div>
        <div class="col-md-5 col-sm-4">
            <iframe src="https://www.google.com/maps/embed"></iframe>
        </div>
    </div>
    <div class="row section">
        <div class="col-md-7 col-xs-12">
            <div  class="commune_info_block row" >
                <div class="col-md-5 col-xs-6">
                    <div class="AnnuLabel">Coordonnées CH :</div>
                </div>
                <div class="col-md-7 col-xs-6">
                    {f.coordonnees}
                </div>
            </div>
            <div  class="commune_info_block row" >
                <div class="col-md-5 col-xs-6">
                    <div class="AnnuLabel">No OFS:</div>
                </div>
                <div class="col-md-7 col-xs-6">
                    {f.ofs}
                </div>
            </div>
        </div>
    </div>
</div>
</body></html>"""


def executer(monde: Monde, dossier: Path) -> tuple[list[dict], list[dict]]:
    """Lance l'outil contre le monde factice ; renvoie (lignes du CSV, cas à revoir)."""
    csv_hdv, revue = dossier / "hotels-de-ville.csv", dossier / "a-revoir.csv"
    with httpx.Client(transport=monde.transport()) as client:
        hdv.initialiser(client, csv_hdv, revue, cache=dossier / "cache")
    return lire_csv(csv_hdv), lire_csv(revue)


def lire_csv(chemin: Path) -> list[dict]:
    with chemin.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ecrire_csv(chemin: Path, lignes: list[dict]) -> None:
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0]))
        w.writeheader()
        w.writerows(lignes)

