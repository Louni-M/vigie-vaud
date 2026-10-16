"""L'échantillon réel d'OpenParlData (`echantillon-openparldata/`, rafraîchi par `echantillon_openparldata.py`) :
son import produit des fichiers d'archive valides, avec les champs attendus. C'est le seul test qui le lit.

Le transport sert chaque fichier de l'échantillon à toute requête de son point d'accès et de son conseil, sans
tenir compte des autres paramètres : le Conseil d'État y figure, l'import doit l'écarter de lui-même.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import jsonschema

from conseils import OpenParlData, importer_conseils
from faux_openparldata import HorlogeFactice
from schema import DOSSIER_SCHEMA, RACINE, lire_sources

ECHANTILLON = Path(__file__).parent / "echantillon-openparldata"


def _servir(requete: httpx.Request) -> httpx.Response:
    entite = requete.url.path.strip("/").split("/")[-1]
    fichier = ECHANTILLON / f"{entite}-{requete.url.params['body_key'].lower()}.json"
    return httpx.Response(200, content=fichier.read_bytes()) if fichier.exists() else httpx.Response(404)


def test_l_import_de_l_echantillon_reel_produit_des_fichiers_d_archive_valides(tmp_path):
    horloge = HorlogeFactice(datetime(2026, 10, 16, 7, 5, tzinfo=UTC))
    with httpx.Client(transport=httpx.MockTransport(_servir)) as http:
        opd = OpenParlData(http, horloge, horloge.attendre)
        importer_conseils(tmp_path, lire_sources(RACINE / "sources.json"), opd, horloge)

    ecrits = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*.json"))
    archive = [c for c in ecrits if "/objets/" in c or "/seances/" in c or c == "conseils/import.json"]
    assert archive == [
        "conseils/5586/objets/POS25-008.json",
        "conseils/5586/seances/2026-10-06.json",
        "conseils/5938/seances/2026-10-01.json",
        "conseils/import.json",
        "conseils/vd/objets/24_LEG_152.json",
        "conseils/vd/objets/26_INT_140.json",
        "conseils/vd/objets/26_POS_54.json",
        "conseils/vd/seances/2026-10-06.json",
    ]
    schemas = {n: json.loads((DOSSIER_SCHEMA / f"{n}.schema.json").read_text()) for n in ("objet", "seance")}
    for chemin in ecrits:
        if "/objets/" in chemin or "/seances/" in chemin:
            schema = schemas["objet" if "/objets/" in chemin else "seance"]
            jsonschema.validate(json.loads((tmp_path / chemin).read_text()), schema)

    empl = json.loads((tmp_path / "conseils/vd/objets/24_LEG_152.json").read_text())
    assert (empl["type"], empl["statut"]["libelle"], empl["depose"]) == ("Décret/Loi", "Adopté", "2026-09-29")
    assert empl["contributeurs"][0] == {
        "nom": "Laurence Cretegny",
        "parti": "PLR",
        "role": "Rapporteur(s) de commission",
        "sorte": "personne",
    }
    assert empl["documents"][0]["lien"].startswith("https://sieldocs.vd.ch/")
    assert empl["etapes"][0] == {"date": "2025-05-28", "libelle": "Déposé"}
    assert empl["lien"].startswith("https://www.vd.ch/gc/")

    interpellation = json.loads((tmp_path / "conseils/vd/objets/26_INT_140.json").read_text())
    assert interpellation["statut"]["libelle"] == interpellation["etapes"][-1]["libelle"]

    lausanne = json.loads((tmp_path / "conseils/5586/objets/POS25-008.json").read_text())
    assert (lausanne["numero"], lausanne["contributeurs"][0]["nom"]) == ("POS25/008", "Loris Socchi")
    assert "Décision : Renvoi en Municipalité" in [e["libelle"] for e in lausanne["etapes"]]

    seance = json.loads((tmp_path / "conseils/vd/seances/2026-10-06.json").read_text())
    assert [(p["numero"], p["objet"]) for p in seance["ordre_du_jour"]] == [
        ("2", None),
        ("11", "vd/26_POS_54"),
        ("18", "vd/24_LEG_152"),
    ]
    point = json.loads((tmp_path / "conseils/5586/seances/2026-10-06.json").read_text())["ordre_du_jour"][0]
    assert (point["objet"], point["categorie"], point["resultat"]) == (
        "5586/POS25-008",
        "OPÉRATIONS PRÉLIMINAIRES",
        "Reporté",
    )
    # « M. Loris SOCCHI » est un élu connu (auteur du postulat) : le masquage l'épargne.
    assert point["titre"] == "Postulat de M. Loris SOCCHI : « Nos beaux murs gris». (FIM)"
    yverdon = json.loads((tmp_path / "conseils/5938/seances/2026-10-01.json").read_text())
    assert (yverdon["date"], [p["numero"] for p in yverdon["ordre_du_jour"]]) == ("2026-10-01T20:00", ["1", "7"])
