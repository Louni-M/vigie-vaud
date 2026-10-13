"""Limites et index des communes vaudoises pour le site en mode « API en direct ».

Source : swissBOUNDARIES3D (swisstopo, données ouvertes). Aucune donnée CAMAC n'est lue ni écrite ici :
le navigateur interroge lui-même le service du canton et rattache chaque dossier à sa commune
grâce à ces limites simplifiées.

Fichiers écrits (versionnés) :
  web/static/communes.json          index : n° OFS, nom, slug, habitants, emprise
  web/static/communes-limites.json  polygones simplifiés (WGS84, ~1 m de précision)
"""

from __future__ import annotations

import json

import httpx

from fetch import ROOT, USER_AGENT, load_communes, slugify

OUT = ROOT / "web" / "static"
# Tolérance de simplification (m, LV95) : invisible à l'échelle d'une commune, fichier ~5 fois plus léger.
TOLERANCE = 10


def arrondi(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 5), round(coords[1], 5)]
    return [arrondi(c) for c in coords]


def main() -> None:
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        communes = load_communes(client)
    communes = communes.dissolve(by=["bfs_nummer", "name"], aggfunc={"einwohnerzahl": "max"}).reset_index()
    communes["geometry"] = communes.geometry.simplify(TOLERANCE, preserve_topology=True)
    wgs = communes.to_crs(4326)
    index, limites = [], {}
    for _, c in wgs.iterrows():
        bfs = int(c.bfs_nummer)
        b = c.geometry.bounds
        index.append(
            {
                "bfs": bfs,
                "nom": c["name"],
                "slug": slugify(c["name"]),
                "habitants": int(c.einwohnerzahl) if c.einwohnerzahl == c.einwohnerzahl else None,
                "bbox": [round(b[0], 4), round(b[1], 4), round(b[2], 4), round(b[3], 4)],
            }
        )
        geo = c.geometry.__geo_interface__
        polys = [geo["coordinates"]] if geo["type"] == "Polygon" else list(geo["coordinates"])
        limites[bfs] = arrondi(polys)
    index.sort(key=lambda c: c["slug"])
    dump = lambda name, obj: (OUT / name).write_text(  # noqa: E731
        json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    )
    dump("communes.json", index)
    dump("communes-limites.json", limites)
    print(f"{len(index)} communes écrites dans {OUT}")


if __name__ == "__main__":
    main()
