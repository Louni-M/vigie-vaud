"""Dépendances du pipeline : le cron n'installe que ce qu'il importe (#196).

La pile géographique (groupe `geo` de `pyproject.toml`) ne sert qu'aux scripts de préparation des communes (voie
d'accès Préparée) ; le cron s'installe sans elle (`uv sync --no-dev`), à chaque passage.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ICI = Path(__file__).resolve().parents[1]
PROJET = tomllib.loads((ICI / "pyproject.toml").read_text(encoding="utf-8"))

PILE_GEO = {"geopandas", "pyogrio", "pyproj", "shapely", "pandas", "numpy"}


def _noms(exigences: list[str]) -> set[str]:
    """Le nom de chaque exigence (`geopandas>=1.2.0` → `geopandas`), normalisé comme le fait uv."""
    return {re.split(r"[<>=!~\[;\s]", e, maxsplit=1)[0].lower().replace("_", "-") for e in exigences}


def test_la_pile_geographique_est_hors_des_dependances_du_projet():
    assert _noms(PROJET["project"]["dependencies"]) & PILE_GEO == set()
    assert {"geopandas", "pyogrio", "pyproj", "shapely"} <= _noms(PROJET["dependency-groups"]["geo"])


def test_les_dependances_importees_directement_sont_declarees():
    assert {"typing-extensions", "pydantic-core"} <= _noms(PROJET["project"]["dependencies"])


def test_la_base_des_fuseaux_horaires_est_declaree():
    # `zoneinfo` (schema.py, Europe/Zurich) lit la base du système ; Windows n'en a pas, et elle n'arrivait que par
    # pandas, avant que la pile géographique ne sorte des dépendances du projet.
    assert "tzdata" in _noms(PROJET["project"]["dependencies"])


def test_le_cron_et_ses_modules_n_importent_pas_la_pile_geographique():
    # Un interpréteur neuf où chaque module de la pile géographique est introuvable : l'import du cron et des modules
    # qu'il lance doit passer quand même, comme dans l'environnement installé par le cron.
    code = (
        "import sys\n"
        f"for m in {sorted(PILE_GEO)!r}:\n"
        "    sys.modules[m] = None\n"
        "import cron, conseils, retraits, schema, preparation_sources\n"
    )
    resultat = subprocess.run([sys.executable, "-c", code], check=False, cwd=ICI, capture_output=True, text=True, encoding="utf-8")

    assert resultat.returncode == 0, resultat.stderr
