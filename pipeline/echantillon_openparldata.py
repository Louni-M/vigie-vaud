"""Télécharge à nouveau l'échantillon réel d'OpenParlData des tests (`tests/echantillon-openparldata/`).

Quelques enregistrements bruts par point d'accès, sur des identifiants fixés, choisis sans particulier : un EMPD avec
document, une interpellation avec étapes et un postulat du Grand Conseil, un postulat de Lausanne ; une Séance du
Grand Conseil, une du Conseil d'État (que l'import doit écarter), une de Lausanne et une d'Yverdon. Les requêtes
sont celles de l'import (mêmes champs, mêmes relations développées), filtrées par `id` ; la réponse est gardée
entière, enveloppe de pagination comprise, sauf deux coupes : seuls les points d'ordre du jour listés ci-dessous
restent (les autres peuvent nommer un particulier), et le texte des documents, s'il est demandé, est tronqué.

À relancer quand la sonde signale des champs absents ou qu'OpenParlData annonce un changement ; le diff montre ce
qui a changé. Après un changement des identifiants ou des points gardés, relire l'échantillon : aucun particulier
ne doit y figurer.

Usage (depuis `pipeline/`) : `uv run python echantillon_openparldata.py`
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from conseils import API, INTERVALLE, USER_AGENT, parametres_objets, parametres_seances
from schema import Conseil

DOSSIER = Path(__file__).resolve().parent / "tests" / "echantillon-openparldata"
LONGUEUR_TEXTE = 500

OBJETS = {
    "VD": [203260, 341083, 340225],  # 24_LEG_152 (EMPL avec document), 26_INT_140, 26_POS_54
    "5586": [120534],  # POS25/008
}
# Par conseil : identifiant de la Séance → numéros des points gardés.
SEANCES = {
    "VD": {33895: ["2", "11", "18"], 33926: []},  # Grand Conseil du 6 octobre 2026, Conseil d'État du 7 octobre
    "5586": {33891: ["15"]},
    "5938": {33831: ["1", "7"]},
}


def telecharger(http: httpx.Client) -> list[Path]:
    ecrits = []
    for entite, choix in (("affairs", OBJETS), ("meetings", SEANCES)):
        for body_key, ids in choix.items():
            conseil = Conseil(body_key=body_key, donne=["objets", "seances"])  # sans groupe : le Conseil d'État vient
            parametres = parametres_objets(conseil, None) if entite == "affairs" else parametres_seances(conseil, None)
            parametres |= {"id": ",".join(str(i) for i in ids), "client": "vigie-vaud"}
            reponse = http.get(f"{API}/{entite}/", params=parametres, headers={"User-Agent": USER_AGENT}, timeout=60)
            reponse.raise_for_status()
            page = reponse.json()
            for enregistrement in page["data"]:
                _couper(enregistrement, ids)
            chemin = DOSSIER / f"{entite}-{conseil.cle}.json"
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(json.dumps(page, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            ecrits.append(chemin)
            time.sleep(INTERVALLE)
    return ecrits


def _couper(enregistrement: dict, ids: list[int] | dict[int, list[str]]) -> None:
    if isinstance(ids, dict) and enregistrement.get("agendas"):
        gardes = ids[enregistrement["id"]]
        agendas = enregistrement["agendas"]
        agendas["data"] = [p for p in agendas["data"] if p.get("item_number_display") in gardes]
    for document in (enregistrement.get("docs") or {}).get("data") or []:
        if isinstance(document.get("text"), str):
            document["text"] = document["text"][:LONGUEUR_TEXTE]


if __name__ == "__main__":
    with httpx.Client() as http:
        for chemin in telecharger(http):
            print(f"{chemin.relative_to(DOSSIER.parent.parent)} : {chemin.stat().st_size // 1024} Ko")
