"""Préparation des communes vaudoises : index et limites publiés avec le site.

Préparée une fois, et relancée à chaque fusion. Aucune donnée CAMAC n'est lue ni écrite ici : le navigateur
interroge lui-même le service du canton et rattache chaque dossier à sa commune grâce à ces limites.

Sources :
  - swissBOUNDARIES3D (swisstopo, OGD) : limites, noms et habitants des communes actuelles ;
  - swissTLMRegio (swisstopo, OGD) : les lacs, soustraits des limites pour la partie terrestre ;
  - hotels-de-ville.csv (outil d'initialisation hotels_de_ville.py), qui fait foi : position et adresse de chaque
    hôtel de ville. Chaque position doit tomber dans la partie terrestre de sa commune, sinon la préparation
    échoue ; une commune absente du CSV (fusion au 1ᵉʳ janvier) passe en repli, avec un avertissement ;
  - répertoire historisé des communes de l'OFS (OGD, depuis 1960) : anciennes communes et anciens noms.

Fichiers écrits (versionnés) :
  web/static/communes.json          index : n° OFS, nom, slug, habitants, `bbox` (emprise complète, lac compris,
                                    pour le rattachement des dossiers), `cadre` (emprise de la partie terrestre,
                                    pour cadrer la carte), `hotel` [lon, lat], `adresse` (vide pour une position
                                    approximative) et `anciens` (nom, slug, type, année)
  web/static/communes-limites.json  polygones simplifiés (WGS84, ~1 m de précision)
  web/src/lib/millesimes.json       édition de chaque source Préparée lue ici, importée par le site pour le badge
                                    de fraîcheur de ces sources
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import unicodedata
import zipfile
from collections import defaultdict
from datetime import date
from pathlib import Path

import geopandas as gpd
import httpx
from pyproj import Transformer
from shapely.geometry import Point

from telechargement import telecharger
from terre import LACS_URL, charger_lacs, partie_terrestre, point_repli

ICI = Path(__file__).resolve().parent
ROOT = ICI.parent
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "web" / "static"
MILLESIMES = ROOT / "web" / "src" / "lib" / "millesimes.json"
CSV_HDV = ICI / "hotels-de-ville.csv"

USER_AGENT = "vigie-vaud/0.1 (projet citoyen non commercial)"
BOUNDARIES_URL = (
    "https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2026-01/"
    "swissboundaries3d_2026-01_2056_5728.gpkg.zip"
)
MUTATIONS_URL = "https://www.agvchapp.bfs.admin.ch/api/communes/mutations"
# Le répertoire historisé des communes commence en 1960.
DEPUIS = 1960
# Année où l'outil d'initialisation (hotels_de_ville.py) a lu l'annuaire de l'UCV et le répertoire des adresses
# pour écrire hotels-de-ville.csv : à mettre à jour quand on le relance.
EDITION_HOTELS = 2026

# Tolérance de simplification (m, LV95) : invisible à l'échelle d'une commune, fichier ~5 fois plus léger.
TOLERANCE = 10

VERS_WGS84 = Transformer.from_crs(2056, 4326, always_xy=True)


def slugify(name: str) -> str:
    """Slug d'une commune : il sert d'adresse (`/commune/<slug>`) et ne doit jamais changer."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"\(vd\)", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def charger_communes(client: httpx.Client, cache: Path = CACHE) -> gpd.GeoDataFrame:
    """Les communes vaudoises de swissBOUNDARIES3D en LV95 (téléchargées une fois dans `cache`)."""
    cache.mkdir(parents=True, exist_ok=True)
    gpkgs = list(cache.glob("swissBOUNDARIES3D*.gpkg"))
    if not gpkgs:
        with zipfile.ZipFile(telecharger(client, BOUNDARIES_URL, cache / "sb3d.gpkg.zip")) as z:
            z.extractall(cache)
        gpkgs = list(cache.glob("swissBOUNDARIES3D*.gpkg"))
    gdf = gpd.read_file(gpkgs[0], layer="tlm_hoheitsgebiet")
    gdf = gdf[(gdf.kantonsnummer == 22) & (gdf.objektart == "Gemeindegebiet")]
    gdf = gdf[["bfs_nummer", "name", "einwohnerzahl", "geometry"]].copy()
    gdf["geometry"] = gdf.geometry.force_2d()
    return gdf.set_crs(2056, allow_override=True)


def lire_anciens(client: httpx.Client, jusqu_au: date, actuelles: dict[int, str]) -> dict[int, list[dict]]:
    """Anciennes communes et anciens noms de chaque commune actuelle, d'après le répertoire historisé de l'OFS.

    Chaque mutation remplace des états d'une commune par un nouvel état (n° d'historisation). On suit ces états
    jusqu'à la commune actuelle à laquelle ils aboutissent. Un nom qui disparaît dans une mutation est un « Ancien
    nom » s'il portait le n° OFS de la commune actuelle (Yverdon, Bussigny-près-Lausanne), une « Ancienne commune »
    sinon (Cully) ; l'année est celle de sa disparition.
    """
    r = client.get(
        MUTATIONS_URL,
        params={"startPeriod": f"01-01-{DEPUIS}", "endPeriod": jusqu_au.strftime("%d-%m-%Y")},
        timeout=120,
    )
    r.raise_for_status()
    etats: dict[str, tuple[int, str]] = {}
    suivants: dict[str, set[str]] = defaultdict(set)
    disparitions: list[tuple[str, int]] = []  # (état dont le nom disparaît, année)
    for m in csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))):
        initial, terminal = m["InitialHistoricalCode"], m["TerminalHistoricalCode"]
        etats[initial] = (int(m["InitialCode"]), m["InitialName"])
        etats[terminal] = (int(m["TerminalCode"]), m["TerminalName"])
        if initial != terminal:
            suivants[initial].add(terminal)
            if m["InitialName"] != m["TerminalName"]:
                disparitions.append((initial, int(m["MutationDate"][-4:])))

    aboutissements: dict[str, set[str]] = {}

    def aboutit(etat: str) -> set[str]:
        if etat not in aboutissements:
            aboutissements[etat] = (
                set().union(*(aboutit(s) for s in suivants[etat])) if etat in suivants else {etat}
            )
        return aboutissements[etat]

    noms_actuels = set(actuelles.values())
    anciens: dict[int, dict[str, dict]] = defaultdict(dict)
    for etat, annee in disparitions:
        fins = {etats[f][0] for f in aboutit(etat)} & actuelles.keys()
        if not fins:
            continue  # autre canton
        ofs, nom = etats[etat]
        if len(fins) > 1:
            print(f"  Avertissement : {nom} ({ofs}) a été partagée entre plusieurs communes, ignorée", file=sys.stderr)
            continue
        [actuelle] = fins
        if nom == actuelles[actuelle] or nom in noms_actuels:
            continue
        avant = anciens[actuelle].get(nom)
        if avant is None or avant["annee"] < annee:
            anciens[actuelle][nom] = {
                "nom": nom,
                "slug": slugify(nom),
                "type": "Ancien nom" if ofs == actuelle else "Ancienne commune",
                "annee": annee,
            }
    return {ofs: sorted(parnom.values(), key=lambda a: a["slug"]) for ofs, parnom in anciens.items()}


class HotelsHorsTerre(Exception):
    """Des hôtels de ville du CSV ne tombent pas dans la partie terrestre de leur commune."""

    def __init__(self, cas: list[str]):
        super().__init__(
            "Hôtels de ville hors de la partie terrestre de leur commune, à corriger dans hotels-de-ville.csv "
            "(origine `manuel`) :\n" + "\n".join(f"  - {c}" for c in cas)
        )


def lire_hotels(chemin: Path) -> dict[int, dict]:
    with chemin.open(newline="", encoding="utf-8") as f:
        return {int(r["ofs"]): r for r in csv.DictReader(f)}


def millesimes(jusqu_au: date) -> dict[str, int]:
    """Édition de chaque source Préparée lue ici, par identifiant de sources.json (badge de fraîcheur du site)."""
    annee = lambda url: int(re.search(r"_(\d{4})", url)[1])  # noqa: E731
    return {
        "swisstopo-limites": annee(BOUNDARIES_URL),
        "swisstopo-lacs": annee(LACS_URL),
        "ucv-annuaire": EDITION_HOTELS,
        "swisstopo-adresses": EDITION_HOTELS,
        "ofs-communes-historique": jusqu_au.year,
    }


def arrondi(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [arrondi(c) for c in coords]


def emprise(b) -> list[float]:
    return [round(b[0], 4), round(b[1], 4), round(b[2], 4), round(b[3], 4)]


def preparer(
    client: httpx.Client,
    csv_hdv: Path = CSV_HDV,
    sortie: Path = OUT,
    millesimes_json: Path = MILLESIMES,
    cache: Path = CACHE,
    jusqu_au: date | None = None,
) -> None:
    """Écrit communes.json et communes-limites.json dans `sortie`, puis `millesimes_json`, ou lève
    `HotelsHorsTerre` sans rien écrire."""
    jusqu_au = jusqu_au or date.today()
    communes = charger_communes(client, cache)
    communes = communes.dissolve(by=["bfs_nummer", "name"], aggfunc={"einwohnerzahl": "max"}).reset_index()
    hotels = lire_hotels(csv_hdv)
    lacs = charger_lacs(client, cache)
    actuelles = {int(c.bfs_nummer): c["name"] for _, c in communes.iterrows()}
    anciens = lire_anciens(client, jusqu_au, actuelles)
    for ofs in hotels.keys() - actuelles.keys():
        print(f"  Avertissement : {hotels[ofs]['nom']} ({ofs}) n'est plus une commune, ligne ignorée", file=sys.stderr)

    simplifiees = communes.geometry.simplify(TOLERANCE, preserve_topology=True).to_crs(4326)
    index, limites, hors_terre = [], {}, []
    for i, c in communes.iterrows():
        bfs, nom = int(c.bfs_nummer), c["name"]
        terre = partie_terrestre(c.geometry, lacs)
        h = hotels.get(bfs)
        if h is None:
            # Une commune née d'une fusion n'a pas encore sa ligne : repli, en attendant l'outil d'initialisation.
            print(f"  Avertissement : {nom} ({bfs}) absente de {csv_hdv.name}, hôtel de ville en repli",
                  file=sys.stderr)
            p = point_repli(c.geometry, lacs)
            h = {"E": p.x, "N": p.y, "adresse": ""}
        elif not terre.contains(p := Point(float(h["E"]), float(h["N"]))):
            ou = "dans un lac" if c.geometry.contains(p) else "hors de la commune"
            hors_terre.append(f"{nom} ({bfs}) : E {h['E']}, N {h['N']} ({h['origine']}) est {ou}")
        lon, lat = VERS_WGS84.transform(float(h["E"]), float(h["N"]))
        wgs = simplifiees.loc[i]
        index.append(
            {
                "bfs": bfs,
                "nom": nom,
                "slug": slugify(nom),
                "habitants": int(c.einwohnerzahl) if c.einwohnerzahl == c.einwohnerzahl else None,
                "bbox": emprise(wgs.bounds),
                "cadre": emprise(gpd.GeoSeries([terre], crs=2056).to_crs(4326).total_bounds),
                "hotel": [round(lon, 5), round(lat, 5)],
                "adresse": h["adresse"],
                "anciens": anciens.get(bfs, []),
            }
        )
        geo = wgs.__geo_interface__
        polys = [geo["coordinates"]] if geo["type"] == "Polygon" else list(geo["coordinates"])
        limites[bfs] = arrondi(polys)
    if hors_terre:
        raise HotelsHorsTerre(hors_terre)
    index.sort(key=lambda c: c["slug"])
    sortie.mkdir(parents=True, exist_ok=True)
    fichiers = {sortie / "communes.json": index, sortie / "communes-limites.json": limites,
                millesimes_json: millesimes(jusqu_au)}
    for chemin, contenu in fichiers.items():
        chemin.write_text(json.dumps(contenu, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(index)} communes écrites dans {sortie}", file=sys.stderr)


def main() -> None:
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        try:
            preparer(client, jusqu_au=date.today())
        except HotelsHorsTerre as e:
            sys.exit(str(e))


if __name__ == "__main__":
    main()
