"""Les cas de test partagés avec le site (`cas-partages/` à la racine du dépôt) : les règles écrites deux fois, en
Python pour le cron et en TypeScript pour le site, sont vérifiées par les mêmes fichiers dans les deux suites."""

import json
from pathlib import Path

DOSSIER = Path(__file__).resolve().parents[2] / "cas-partages"


def cas_partages(nom: str) -> list[dict]:
    """Les cas du fichier partagé `cas-partages/<nom>.json`."""
    return json.loads((DOSSIER / f"{nom}.json").read_text(encoding="utf-8"))["cas"]
