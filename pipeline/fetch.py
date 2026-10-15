"""Récupère les demandes de permis de construire du canton de Vaud et génère les données du site.

Source : couche « vd.demande_permis_construire » (CAMAC / DGTL), Géodonnées Etat de Vaud.
Les données n'ont pas de foi publique : seule la FAO fait foi.

Étapes :
  1. télécharge la couche ArcGIS (pagination par 2000) en LV95 ;
  2. rattache chaque point à sa commune actuelle (swissBOUNDARIES3D, swisstopo) ;
  3. normalise les champs et compare avec l'instantané précédent (historique des statuts) ;
  4. écrit les fichiers statiques consommés par le site (web/static/data) et les tuiles PMTiles.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import geopandas as gpd
import httpx
from pyproj import Transformer
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CACHE = DATA / "cache"
SNAPSHOT = DATA / "snapshot.json"
CHANGES = DATA / "changes.jsonl"
OUT = ROOT / "web" / "static" / "data"

LAYER_URL = "https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/537/query"
BOUNDARIES_URL = (
    "https://data.geo.admin.ch/ch.swisstopo.swissboundaries3d/swissboundaries3d_2026-01/"
    "swissboundaries3d_2026-01_2056_5728.gpkg.zip"
)
PAGE = 2000
USER_AGENT = "vigie-vaud/0.1 (projet citoyen non commercial)"

# Garde-fou : refuse la mise à jour si le nombre de dossiers chute trop.
MAX_DROP = 0.05
# Fiches pré-générées (aperçu de partage) pour les dossiers récents.
PRERENDER_MONTHS = 24
ACTIVE_PROCEDURE_YEARS = 3
COMMUNE_RECENTS = 60

STATUS = {
    "Enquête publique en cours": "enquete",
    "Procédure en cours": "procedure",
    "Permis délivré": "delivre",
    "Réalisé": "realise",
    "Abandonné/refusé": "abandonne",
}

NATURE = {
    "Construction nouvelle": "construction",
    "Transformation": "transformation",
    "Transformation(s)": "transformation",
    "Adjonction": "adjonction",
    "Agrandissement": "agrandissement",
    "Changement ou nouvelle destination des locaux": "changement",
    "Reconstruction après démolition": "reconstruction",
    "Reconstruction après incendie": "reconstruction_incendie",
    "Rénovation totale": "renovation",
    "Démolition totale": "demolition",
    "Démolition partielle": "demolition_partielle",
}

DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"\(vd\)", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


C1_RE = re.compile(r"[\x80-\x9f]")


def clean_text(s: str | None) -> str:
    """Corrige les caractères Windows-1252 mal décodés (ex. \x92 → ’) et les espaces superflus."""

    def fix(m: re.Match) -> str:
        try:
            return m[0].encode("latin-1").decode("cp1252")
        except UnicodeDecodeError:
            return ""

    s = C1_RE.sub(fix, s or "")
    s = "".join(ch for ch in s if ch >= " " or ch in "\t\n")
    return " ".join(s.split())


# Masquage des noms de particuliers dans les descriptions libres (« pour le compte de M. X »).
# Les personnes morales (opérateurs, sociétés, collectivités…) restent affichées : c'est une information utile,
# par exemple pour les antennes de téléphonie mobile. Approche prudente : en cas de doute, on masque.
MASQUE = "[particulier]"
ENTITE_RE = re.compile(
    r"\b(?:S\.?A\.?|Sàrl|S\.à\.r\.l\.?|SARL|GmbH|AG|SNC|SCI|Ltd|Inc|"
    r"Swisscom|Sunrise|Salt|Orange|UPC|CFF|SBB|Migros|Coop|Banque|BCV|Raiffeisen|Poste|"
    r"Commune|Ville|Municipalit[ée]|[ÉE]tat|Canton|Conf[ée]d[ée]ration|Paroisse|[ÉE]glise|"
    r"Fondation|Association|Soci[ée]t[ée]|Coop[ée]rative|Communaut[ée]|PPE|Hoirie|Consortage|"
    r"Groupe|Holding|Immobili[eè]re?|Caisse|Assurances?|Fonds|Hôpital|H[ôo]pitaux|[ÉE]cole|Club|"
    r"Romande Energie|Services?|Infra|SI\b|Syndicat|Entreprise|Cave|Domaine|Hôtel|Restaurant)(?!\w)",
    re.I,
)
CIVILITE = r"(?:M\.|MM\.|Mme|Mmes|Mlle|Monsieur|Madame|Messieurs|Mesdames)"
COMPTE_RE = re.compile(
    r"(pour\s+(?:le\s+)?compte\s+(?:de\s+(?:la\s+|l[’'´]\s*|de\s+)?|d[’'´]\s*|des\s+|du\s+))"
    r"([^.,;:()/\n]+?)(?=\s*(?:[.,;:()/]|\savec\s|\set\s(?:de\s|d[’'´])|$))",
    re.I,
)
NOM = r"[A-ZÀ-Ý](?:\.(?:-[A-ZÀ-Ý]\.)?|[\w’'´-]*)"  # « Dupont », « J. », « J.-P. »
CIVILITE_RE = re.compile(
    rf"\b{CIVILITE}(?:\s+(?:et|&)\s+{CIVILITE})*\s+{NOM}(?:\s+(?:et\s+|&\s+)?{NOM})*"
)
LIAISONS = {"et", "&", "de", "du", "des", "da", "dos", "von", "van", "der", "le", "la"}


def ressemble_a_un_nom(segment: str) -> bool:
    """Suite de 2 à 8 mots tous à majuscule initiale (hors liaisons), sans chiffre : « Occipinti Santo »."""
    mots = [m for m in re.split(r"\s+", segment.strip()) if m]
    noms = [m for m in mots if m.lower() not in LIAISONS]
    return (
        2 <= len(noms) <= 8
        and not any(c.isdigit() for c in segment)
        and all(m[0].isupper() for m in noms)
    )


def mask_names(s: str) -> str:
    def compte(m: re.Match) -> str:
        parties = re.split(r"(\s-\s)", m[2])
        for i in range(0, len(parties), 2):
            p = parties[i]
            if re.search(CIVILITE, p) or (not ENTITE_RE.search(p) and ressemble_a_un_nom(p)):
                parties[i] = MASQUE
        return m[1] + "".join(parties)

    # Formes juridiques avec points (« S.A. », « A.G. », « S.à r.l. ») : sinon le point coupe le segment.
    s = re.sub(r"\bS\.\s?A\.?(?!\w)", "SA", s)
    s = re.sub(r"\bA\.\s?G\.?(?!\w)", "AG", s)
    s = re.sub(r"\bS\.?\s?à\s?r\.?\s?l\.?(?!\w)", "Sàrl", s, flags=re.I)
    # Civilités d'abord (« M. Dupont ») : le point de « M. » couperait sinon le segment « pour le compte de ».
    s = CIVILITE_RE.sub(MASQUE, s)
    return COMPTE_RE.sub(compte, s)


def parse_date(s: str | None) -> str | None:
    if not s:
        return None
    m = DATE_RE.search(s)
    return f"{m[3]}-{m[2]}-{m[1]}" if m else None


def parse_period(s: str | None) -> tuple[str | None, str | None]:
    dates = DATE_RE.findall(s or "")
    to_iso = lambda d: f"{d[2]}-{d[1]}-{d[0]}"  # noqa: E731
    start = to_iso(dates[0]) if dates else None
    end = to_iso(dates[1]) if len(dates) > 1 else None
    return start, end


def fetch_layer(client: httpx.Client) -> list[dict]:
    features: list[dict] = []
    offset = 0
    while True:
        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "2056",
            "orderByFields": "OBJECTID",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "f": "json",
        }
        for attempt in range(5):
            try:
                r = client.get(LAYER_URL, params=params, timeout=120)
                r.raise_for_status()
                page = r.json()
                if "error" in page:
                    raise RuntimeError(page["error"])
                break
            except (httpx.HTTPError, RuntimeError, json.JSONDecodeError) as e:
                if attempt == 4:
                    raise
                print(f"  erreur page {offset} ({e}), nouvel essai…", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
        batch = page.get("features", [])
        features.extend(batch)
        print(f"  {len(features)} dossiers", file=sys.stderr)
        if not page.get("exceededTransferLimit") and len(batch) < PAGE:
            break
        offset += PAGE
        time.sleep(0.5)
    return features


def load_communes(client: httpx.Client, cache: Path = CACHE) -> gpd.GeoDataFrame:
    cache.mkdir(parents=True, exist_ok=True)
    gpkgs = list(cache.glob("swissBOUNDARIES3D*.gpkg"))
    if not gpkgs:
        zpath = cache / "sb3d.gpkg.zip"
        with client.stream("GET", BOUNDARIES_URL, timeout=600) as r:
            r.raise_for_status()
            with open(zpath, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
        with zipfile.ZipFile(zpath) as z:
            z.extractall(cache)
        gpkgs = list(cache.glob("swissBOUNDARIES3D*.gpkg"))
    gdf = gpd.read_file(gpkgs[0], layer="tlm_hoheitsgebiet")
    gdf = gdf[(gdf.kantonsnummer == 22) & (gdf.objektart == "Gemeindegebiet")]
    gdf = gdf[["bfs_nummer", "name", "einwohnerzahl", "geometry"]].copy()
    gdf["geometry"] = gdf.geometry.force_2d()
    return gdf.set_crs(2056, allow_override=True)


def normalize(features: list[dict], communes: gpd.GeoDataFrame) -> list[dict]:
    pts = gpd.GeoDataFrame(
        {"i": range(len(features))},
        geometry=[Point(f["geometry"]["x"], f["geometry"]["y"]) for f in features],
        crs=2056,
    )
    joined = gpd.sjoin(pts, communes, how="left", predicate="within")
    joined = joined[~joined.index.duplicated()]
    # Points hors commune (lacs, imprécisions) : commune la plus proche.
    missing = joined[joined.bfs_nummer.isna()]
    if len(missing):
        near = gpd.sjoin_nearest(pts.loc[missing.index], communes, how="left")
        near = near[~near.index.duplicated()]
        joined.loc[missing.index, ["bfs_nummer", "name"]] = near[["bfs_nummer", "name"]]

    to_wgs = Transformer.from_crs(2056, 4326, always_xy=True)
    out = []
    for i, f in enumerate(features):
        a = f["attributes"]
        x, y = f["geometry"]["x"], f["geometry"]["y"]
        lon, lat = to_wgs.transform(x, y)
        start, end = parse_period(a.get("DATE_ENQUETE"))
        commune = joined.at[i, "name"]
        out.append(
            {
                "id": a["NO_CAMAC"],
                "fao": a.get("NO_FAO"),
                "debut": start,
                "fin": end,
                "nature": NATURE.get(a.get("NATURE") or "", "autre"),
                "description": mask_names(clean_text(a.get("DESCRIPTION"))),
                "decision": a.get("DECISION_COMMUNALE"),
                "date_decision": parse_date(a.get("DATE_DECISION")),
                "statut": STATUS.get(a.get("ETAT") or "", "autre"),
                "url": a.get("URL"),
                "lon": round(lon, 5),
                "lat": round(lat, 5),
                "bfs": int(joined.at[i, "bfs_nummer"]),
                "commune": commune,
            }
        )
    out.sort(key=lambda d: d["id"])
    return out


def diff_snapshot(records: list[dict], today: str) -> dict[int, list[dict]]:
    """Compare avec l'instantané précédent, journalise les changements de statut/décision."""
    previous: dict[int, dict] = {}
    if SNAPSHOT.exists():
        previous = {d["id"]: d for d in json.loads(SNAPSHOT.read_text())}
        if len(records) < len(previous) * (1 - MAX_DROP):
            sys.exit(
                f"Garde-fou : {len(records)} dossiers contre {len(previous)} précédemment. "
                "Mise à jour refusée."
            )
    tracked = ("statut", "decision", "date_decision")
    new_changes = []
    for d in records:
        p = previous.get(d["id"])
        if p is None:
            if previous:
                new_changes.append({"date": today, "id": d["id"], "type": "nouveau", "statut": d["statut"]})
        elif any(p.get(k) != d.get(k) for k in tracked):
            new_changes.append(
                {"date": today, "id": d["id"], "type": "changement",
                 **{f"{k}_avant": p.get(k) for k in tracked}, **{k: d.get(k) for k in tracked}}
            )
    if new_changes:
        with CHANGES.open("a") as f:
            for c in new_changes:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    SNAPSHOT.write_text(json.dumps(records, ensure_ascii=False, indent=0))
    print(f"  {len(new_changes)} changements depuis le dernier passage", file=sys.stderr)

    history: dict[int, list[dict]] = {}
    if CHANGES.exists():
        for line in CHANGES.read_text().splitlines():
            c = json.loads(line)
            history.setdefault(c["id"], []).append(
                {"date": c["date"], "statut": c.get("statut"), "decision": c.get("decision")}
            )
    return history


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def write_site_data(records: list[dict], communes: gpd.GeoDataFrame, history: dict, today: str) -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    slugs = {}
    for _, c in communes.iterrows():
        slugs[int(c.bfs_nummer)] = slugify(c["name"])

    def public(d: dict) -> dict:
        r = {k: v for k, v in d.items() if v not in (None, "")}
        r["slug"] = slugs[d["bfs"]]
        if d["id"] in history:
            r["historique"] = history[d["id"]]
        return r

    # 1. Dossiers actifs (enquête en cours + procédure en cours) : chargés à l'ouverture.
    # Beaucoup de « procédures en cours » anciennes ne sont jamais clôturées dans la couche :
    # on ne garde que celles dont l'enquête date de moins de ACTIVE_PROCEDURE_YEARS ans.
    proc_cutoff = f"{date.today().year - ACTIVE_PROCEDURE_YEARS}{date.today().isoformat()[4:]}"
    active = [
        public(d)
        for d in records
        if d["statut"] == "enquete" or (d["statut"] == "procedure" and (d["debut"] or "") >= proc_cutoff)
    ]
    dump(OUT / "active.json", active)
    active_ids = {d["id"] for d in active}

    # 2. Un fichier par commune.
    by_commune: dict[int, list[dict]] = {}
    for d in records:
        by_commune.setdefault(d["bfs"], []).append(d)
    communes_index = []
    bounds = communes.to_crs(4326).bounds
    for idx, c in communes.iterrows():
        bfs = int(c.bfs_nummer)
        items = sorted(by_commune.get(bfs, []), key=lambda d: d["debut"] or "", reverse=True)
        counts = {s: 0 for s in STATUS.values()}
        for d in items:
            counts[d["statut"]] = counts.get(d["statut"], 0) + 1
        b = bounds.loc[idx]
        communes_index.append(
            {
                "bfs": bfs,
                "nom": c["name"],
                "slug": slugs[bfs],
                "habitants": int(c.einwohnerzahl) if c.einwohnerzahl == c.einwohnerzahl else None,
                "bbox": [round(b.minx, 4), round(b.miny, 4), round(b.maxx, 4), round(b.maxy, 4)],
                "total": len(items),
                "statuts": counts,
            }
        )
        # Résumé intégré à la page de commune (actifs, récents, chiffres par année) ;
        # l'historique complet est un fichier séparé chargé à la demande.
        actifs = [public(d) for d in items if d["id"] in active_ids]
        recents = [public(d) for d in items if d["id"] not in active_ids][:COMMUNE_RECENTS]
        par_annee: dict[str, int] = {}
        for d in items:
            if d["debut"]:
                par_annee[d["debut"][:4]] = par_annee.get(d["debut"][:4], 0) + 1
        dump(
            OUT / "communes" / f"{slugs[bfs]}.json",
            {"actifs": actifs, "recents": recents, "par_annee": par_annee},
        )
        dump(OUT / "communes" / "tout" / f"{slugs[bfs]}.json", [public(d) for d in items])
    communes_index.sort(key=lambda c: c["slug"])
    dump(OUT / "communes.json", communes_index)

    # 3. Dossiers par tranches de numéro CAMAC (fiches /dossier/:id).
    shards: dict[int, list[dict]] = {}
    for d in records:
        shards.setdefault(d["id"] // 1000, []).append(public(d))
    for k, items in shards.items():
        dump(OUT / "dossiers" / f"{k}.json", items)

    # 4. Liste des fiches à pré-générer (dossiers récents).
    cutoff = date.today().replace(day=1)
    y, m = cutoff.year, cutoff.month - PRERENDER_MONTHS
    while m <= 0:
        y, m = y - 1, m + 12
    cutoff_iso = f"{y:04d}-{m:02d}-01"
    prerender = [d["id"] for d in records if (d["debut"] or "") >= cutoff_iso or d["id"] in active_ids]
    dump(OUT / "prerender.json", prerender)

    # 5. Métadonnées.
    counts = {s: 0 for s in STATUS.values()}
    for d in records:
        counts[d["statut"]] = counts.get(d["statut"], 0) + 1
    dump(
        OUT / "meta.json",
        {
            "mise_a_jour": today,
            "genere_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": len(records),
            "statuts": counts,
            "derniere_enquete": max((d["debut"] for d in records if d["debut"]), default=None),
            "source": "Source : Géodonnées Etat de Vaud (CAMAC), " + today,
        },
    )

    # 6. Tuiles vectorielles de tout l'historique (attributs minimaux).
    build_tiles(records)


def build_tiles(records: list[dict]) -> None:
    if not shutil.which("tippecanoe"):
        print("  tippecanoe introuvable : tuiles non générées", file=sys.stderr)
        return
    seq = CACHE / "permits.geojsonl"
    with seq.open("w") as f:
        for d in records:
            year = int(d["debut"][:4]) if d["debut"] else 0
            f.write(
                json.dumps(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [d["lon"], d["lat"]]},
                        "properties": {"id": d["id"], "s": d["statut"], "n": d["nature"], "y": year},
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
    subprocess.run(
        [
            "tippecanoe", "-q", "-f", "-o", str(OUT / "permits.pmtiles"),
            "-l", "permits", "-z14", "-Z7", "-r1", "--no-feature-limit", "--no-tile-size-limit",
            "-P", str(seq),
        ],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="réutilise data/cache/raw.json.gz")
    args = ap.parse_args()

    DATA.mkdir(exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    raw_path = CACHE / "raw.json.gz"
    today = date.today().isoformat()

    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        if args.offline and raw_path.exists():
            features = json.loads(gzip.decompress(raw_path.read_bytes()))
        else:
            print("Téléchargement de la couche CAMAC…", file=sys.stderr)
            features = fetch_layer(client)
            raw_path.write_bytes(gzip.compress(json.dumps(features).encode()))
        print("Limites communales…", file=sys.stderr)
        communes = load_communes(client)

    print("Normalisation…", file=sys.stderr)
    records = normalize(features, communes)
    history = diff_snapshot(records, today)
    print("Écriture des données du site…", file=sys.stderr)
    write_site_data(records, communes, history, today)
    print(f"Terminé : {len(records)} dossiers.", file=sys.stderr)


if __name__ == "__main__":
    main()
