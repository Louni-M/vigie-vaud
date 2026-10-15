"""Téléchargement des fichiers des sources Préparées, une seule fois dans le cache."""

from __future__ import annotations

from pathlib import Path

import httpx


def telecharger(client: httpx.Client, url: str, chemin: Path) -> Path:
    """Télécharge `url` dans `chemin`, sauf s'il y est déjà. Le fichier n'apparaît qu'une fois complet : un
    téléchargement interrompu est repris de zéro au lancement suivant."""
    if not chemin.exists():
        chemin.parent.mkdir(parents=True, exist_ok=True)
        partiel = chemin.with_suffix(".partiel")
        with client.stream("GET", url, timeout=600) as r:
            r.raise_for_status()
            with partiel.open("wb") as f:
                for morceau in r.iter_bytes():
                    f.write(morceau)
        partiel.rename(chemin)
    return chemin
