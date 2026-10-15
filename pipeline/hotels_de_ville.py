"""Outil d'initialisation des hôtels de ville : écrit `hotels-de-ville.csv` et la liste des cas à revoir.

Lancé une fois, puis seulement pour une nouvelle commune (décisions des issues #4 et #12, ticket #25).

Ordre de position, pour chaque commune actuelle (swissBOUNDARIES3D) :
  1. une ligne `manuel` déjà présente dans le CSV, qui n'est jamais déplacée ;
  2. l'adresse du siège tirée de l'annuaire de l'UCV, géocodée par le répertoire officiel des adresses de
     bâtiments de swisstopo en appariant sur le n° OFS (pas sur le NPA) ;
  3. à défaut, le repli : un point de la partie terrestre de la commune.

OpenStreetMap (`amenity=townhall`) ne sert qu'au contrôle : rien d'OSM n'est écrit dans le CSV.
"""

from __future__ import annotations

import csv
import html
import io
import re
import sys
import time
import unicodedata
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin

import httpx
from pyproj import Transformer
from shapely.geometry import Point

from communes import CACHE, USER_AGENT, charger_communes
from telechargement import telecharger
from terre import charger_lacs, point_repli

ICI = Path(__file__).resolve().parent
CSV_HDV = ICI / "hotels-de-ville.csv"
REVUE = ICI / "hotels-de-ville-a-revoir.csv"
CACHE_HDV = CACHE / "hotels-de-ville"

UCV_LISTE = "https://www.ucv.ch/annuaire/recherche-par-localite"
ADRESSES_URL = (
    "https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/"
    "amtliches-gebaeudeadressverzeichnis_ch/amtliches-gebaeudeadressverzeichnis_ch_2056.csv.zip"
)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

ECART_MAX = 150  # mètres
# Les coordonnées UCV sont arrondies à 100 m : un `townhall` OSM bien nommé à moins de CONFIRMATION_OSM m du siège
# géocodé suffit à le confirmer, et l'écart avec l'UCV n'est alors que du bruit (ticket #26).
CONFIRMATION_OSM = 80  # mètres
# En deçà, le marqueur reste sur l'adresse officielle du bon village : assez pour une carte (ticket #26).
ECART_UCV_MIN = 1000  # mètres

COLONNES = ["ofs", "nom", "adresse", "E", "N", "origine", "note"]
COLONNES_REVUE = ["ofs", "nom", "motif", "detail", "carte"]
CARTE = "https://map.geo.admin.ch/#/map?lang=fr&center={e},{n}&z=12&crosshair=marker,{e},{n}"


# --- Annuaire de l'UCV -------------------------------------------------------------------------------


@dataclass
class FicheUCV:
    nom: str
    ofs: int
    lignes: list[str]  # bloc d'adresse de la page commune
    coordonnees: tuple[float, float] | None  # « Coordonnées CH » de l'annuaire, passées de LV03 en LV95


@dataclass
class Siege:
    rue: str
    numero: str
    npa: str | None


def lire_ucv(client: httpx.Client, cache: Path) -> dict[int, FicheUCV]:
    liste = client.get(UCV_LISTE, timeout=60)
    liste.raise_for_status()
    liens = dict.fromkeys(re.findall(r'href="(/annuaire/recherche-par-localite/commune/[^"]+)"', liste.text))
    # L'annuaire met plusieurs secondes à servir chaque page : quatre à la fois, chacune gardée en cache.
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = list(pool.map(lambda lien: _page(client, urljoin(UCV_LISTE, lien), cache), liens))
    fiches = [_fiche(p) for p in pages]
    return {f.ofs: f for f in fiches}


def _page(client: httpx.Client, url: str, cache: Path) -> str:
    chemin = cache / "ucv" / (re.sub(r"[^\w-]+", "_", unquote(url.rsplit("/", 1)[1])) + ".html")
    if chemin.exists():
        return chemin.read_text(encoding="utf-8")
    r = client.get(url, timeout=120)
    r.raise_for_status()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(r.text, encoding="utf-8")
    return r.text


def _texte(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def _fiche(page: str) -> FicheUCV:
    nom = _texte(re.search(r"<h1>(.*?)</h1>", page, re.S)[1])
    ofs = int(re.search(r"No OFS:\s*</div>\s*</div>\s*<div[^>]*>\s*(\d+)", page)[1])
    bloc = re.search(r'<div class="col-md-4 col-sm-4 col-xs-6">(.*?)<div class="col-md-5', page, re.S)[1]
    lignes = [t for t in (_texte(x) for x in re.findall(r"<div[^>]*>(.*?)</div>", bloc, re.S)) if t]
    co = re.search(r"Coordonnées CH :\s*</div>\s*</div>\s*<div[^>]*>\s*(\d+)\s*-\s*(\d+)", page)
    # LV03 vers LV95 par simple translation : moins de 2 m d'erreur, pour des coordonnées arrondies à 100 m.
    coordonnees = (int(co[1]) + 2_000_000, int(co[2]) + 1_000_000) if co and int(co[1]) else None
    return FicheUCV(nom, ofs, lignes, coordonnees)


def siege(fiche: FicheUCV) -> Siege | None:
    """La rue et le numéro du siège, ou None si l'annuaire ne donne pas de rue (« Hôtel de Ville », case postale)."""
    npa, lignes = None, []
    for ligne in fiche.lignes:
        if re.match(r"(Tél|Fax|www|http)", ligne, re.I) or "(at)" in ligne:
            break
        if m := re.match(r"(\d{4})\s+\S", ligne):
            npa = m[1]
            break
        lignes.append(ligne)
    # Une ligne mêle parfois le bâtiment, la rue et la case postale : « Hôtel de Ville, Place Pestalozzi 2 »,
    # « Commune de Villarzel - route de Romont 9 », « Rue du Village 39 / CP 14 ».
    mentions = [m for ligne in lignes for m in re.split(r"\s+[-/]\s+|,\s*", re.sub(r"\(.*?\)", "", ligne))]
    for mention in mentions:
        mention = re.sub(r"^p\.?\s*a\.?\s+", "", mention, flags=re.I)
        mention = " ".join(mention.strip(' "«»').split())
        if re.match(r"(case postale|cp)\b", mention, re.I):
            continue
        if m := re.fullmatch(r"(.*\D)\s+(\d+\s?[a-z]?)", mention, re.I):
            return Siege(m[1].strip(), m[2].replace(" ", ""), npa)
    return None


# --- Répertoire officiel des adresses de bâtiments --------------------------------------------------


@dataclass
class AdresseOfficielle:
    rue: str
    numero: str
    localite: str
    egid: str
    e: float
    n: float

    @property
    def libelle(self) -> str:
        return f"{self.rue} {self.numero}, {self.localite}"


def lire_adresses(client: httpx.Client, cache: Path) -> dict[int, list[AdresseOfficielle]]:
    """Les adresses vaudoises existantes, rangées par n° OFS de commune."""
    archive = telecharger(client, ADRESSES_URL, cache / "adresses.csv.zip")
    index: dict[int, list[AdresseOfficielle]] = {}
    with zipfile.ZipFile(archive) as z, z.open(z.namelist()[0]) as brut:
        for r in csv.DictReader(io.TextIOWrapper(brut, encoding="utf-8-sig"), delimiter=";"):
            if r["COM_CANTON"] != "VD" or r["ADR_STATUS"] != "real":
                continue
            index.setdefault(int(r["COM_FOSNR"]), []).append(
                AdresseOfficielle(
                    r["STN_LABEL"], r["ADR_NUMBER"], r["ZIP_LABEL"], r["BDG_EGID"],
                    float(r["ADR_EASTING"]), float(r["ADR_NORTHING"]),
                )
            )
    return index


ABREVIATIONS = {"rte": "route", "ch": "chemin", "av": "avenue", "pl": "place", "st": "saint", "ste": "sainte",
                "gd": "grand", "gde": "grande", "r": "rue"}
MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "l", "d"}


def _cle_rue(rue: str) -> tuple[str, ...]:
    s = unicodedata.normalize("NFKD", rue)
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    mots = re.sub(r"[^a-z0-9]+", " ", s).split()
    return tuple(ABREVIATIONS.get(m, m) for m in mots if m not in MOTS_VIDES)


def geocoder(s: Siege, adresses: list[AdresseOfficielle]) -> AdresseOfficielle | None:
    cle, numero = _cle_rue(s.rue), s.numero.lower()
    trouvees = [a for a in adresses if a.numero.lower() == numero and _cle_rue(a.rue) == cle]
    if len({a.egid for a in trouvees}) > 1 and s.npa:
        trouvees = [a for a in trouvees if a.localite.startswith(s.npa)]
    return trouvees[0] if len({a.egid for a in trouvees}) == 1 else None


# --- Contrôle par OpenStreetMap ----------------------------------------------------------------------

REQUETE_OVERPASS = """[out:json][timeout:120];
area["ISO3166-2"="CH-VD"]["boundary"="administrative"]->.vd;
nwr["amenity"="townhall"](area.vd);
out tags center;"""
# Un `townhall` ne sert au contrôle que s'il est nommé comme une administration (pas une grande salle ni la
# préfecture) : recherche de l'issue #4.
BIEN_NOMME = re.compile(
    r"administration|h[ôo]tel de ville|maison de (commune|ville)|mairie|greffe|secr[ée]tariat|municipalit|"
    r"commune|ville de|si[èe]ge communal|b[âa]timent communal",
    re.I,
)


def lire_townhalls(client: httpx.Client, essais: int = 4, attente: float = 30) -> list[tuple[str, Point]]:
    """Les `amenity=townhall` bien nommés du canton, en LV95 (Overpass répond souvent 504 au premier essai)."""
    for essai in range(essais):
        r = client.post(OVERPASS_URL, data={"data": REQUETE_OVERPASS}, timeout=180)
        if r.status_code not in (429, 502, 503, 504) or essai == essais - 1:
            break
        print(f"  Overpass : {r.status_code}, nouvel essai…", file=sys.stderr)
        time.sleep(attente * (essai + 1))
    r.raise_for_status()
    vers_lv95 = Transformer.from_crs(4326, 2056, always_xy=True)
    townhalls = []
    for el in r.json()["elements"]:
        nom = el.get("tags", {}).get("name", "")
        centre = el.get("center", el)
        if BIEN_NOMME.search(nom):
            townhalls.append((nom, Point(vers_lv95.transform(centre["lon"], centre["lat"]))))
    return townhalls


def ecarts(position: Point, fiche: FicheUCV | None, townhalls: list[tuple[str, Point]]) -> list[str]:
    """Écarts de plus de ECART_MAX m avec le `townhall` OSM bien nommé le plus proche, et d'au moins ECART_UCV_MIN m
    avec les coordonnées UCV quand OSM ne confirme pas le siège (pas de `townhall` à CONFIRMATION_OSM m).
    """
    constats = []
    nom, d_osm = None, None
    if townhalls:
        nom, plus_proche = min(townhalls, key=lambda t: t[1].distance(position))
        if (d_osm := plus_proche.distance(position)) > ECART_MAX:
            constats.append(f"à {d_osm:.0f} m du townhall OSM « {nom} »")
    confirme_par_osm = d_osm is not None and d_osm <= CONFIRMATION_OSM
    if fiche and fiche.coordonnees and (d := Point(fiche.coordonnees).distance(position)) >= ECART_UCV_MIN:
        if not confirme_par_osm:
            constats.append(f"à {d:.0f} m des coordonnées UCV")
            if d_osm is None:
                constats.append("aucun townhall OSM bien nommé dans la commune")
            elif d_osm <= ECART_MAX:
                constats.append(f"townhall OSM « {nom} » à {d_osm:.0f} m")
    return constats


# --- Exécution ---------------------------------------------------------------------------------------


def initialiser(client: httpx.Client, csv_hdv: Path = CSV_HDV, revue: Path = REVUE, cache: Path = CACHE_HDV) -> None:
    communes = charger_communes(client, cache)
    communes = communes.dissolve(by=["bfs_nummer", "name"]).reset_index()
    fiches = lire_ucv(client, cache)
    adresses = lire_adresses(client, cache)
    lacs = charger_lacs(client, cache)
    townhalls = lire_townhalls(client)

    existantes = _lire(csv_hdv)
    lignes, cas = [], []
    for _, c in communes.iterrows():
        ofs, nom = int(c.bfs_nummer), c["name"]
        avant = existantes.pop(ofs, {})
        if avant.get("origine") == "manuel":
            lignes.append(avant)
            continue
        note = avant.get("note", "")
        fiche = fiches.get(ofs)
        s = siege(fiche) if fiche else None
        a = geocoder(s, adresses.get(ofs, [])) if s else None
        if a:
            lignes.append({"ofs": ofs, "nom": nom, "adresse": a.libelle, "E": round(a.e), "N": round(a.n),
                           "origine": f"adresse:{a.egid}", "note": note})
            dans_la_commune = [t for t in townhalls if c.geometry.contains(t[1])]
            if constats := ecarts(Point(a.e, a.n), fiche, dans_la_commune):
                cas.append({"ofs": ofs, "nom": nom, "motif": "écart", "detail": " ; ".join(constats),
                            "carte": CARTE.format(e=round(a.e), n=round(a.n))})
            continue
        p = point_repli(c.geometry, lacs)
        lignes.append({"ofs": ofs, "nom": nom, "adresse": "", "E": round(p.x), "N": round(p.y),
                       "origine": "repli", "note": note})
        if s:
            motif, detail = "adresse non appariée", f"UCV : {s.rue} {s.numero} introuvable dans la commune"
        elif fiche:
            motif, detail = "repli", "UCV sans rue : " + " / ".join(fiche.lignes[:3])
        else:
            motif, detail = "repli", "commune absente de l'annuaire de l'UCV"
        cas.append({"ofs": ofs, "nom": nom, "motif": motif, "detail": detail,
                    "carte": CARTE.format(e=round(p.x), n=round(p.y))})
    for ofs, disparue in existantes.items():
        print(f"  Avertissement : {disparue['nom']} ({ofs}) n'est plus une commune, ligne retirée", file=sys.stderr)
    lignes.sort(key=lambda l: int(l["ofs"]))
    cas.sort(key=lambda l: int(l["ofs"]))
    _ecrire(csv_hdv, COLONNES, lignes)
    _ecrire(revue, COLONNES_REVUE, cas)
    origines = Counter(str(l["origine"]).split(":")[0] for l in lignes)
    print(f"{len(lignes)} communes ({dict(origines)}), {len(cas)} cas à revoir ({dict(Counter(c['motif'] for c in cas))})",
          file=sys.stderr)


def _lire(chemin: Path) -> dict[int, dict]:
    if not chemin.exists():
        return {}
    with chemin.open(newline="", encoding="utf-8") as f:
        return {int(r["ofs"]): r for r in csv.DictReader(f)}


def _ecrire(chemin: Path, colonnes: list[str], lignes: list[dict]) -> None:
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, lineterminator="\n")
        w.writeheader()
        w.writerows(lignes)


if __name__ == "__main__":
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        initialiser(client)
    print(f"Écrit : {CSV_HDV.name}, {REVUE.name}", file=sys.stderr)
