"""La README ne renvoie qu'à des fichiers du dépôt qui existent : liens relatifs et chemins cités entre accents graves.

Les chemins du dépôt de données (`conseils/index.json`, `etat-sources.json`) et du cache (`data/cache/`) n'existent pas
ici : seuls comptent ceux qui commencent par un dossier du dépôt (`RACINES`).
"""

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

RACINES = ("web/", "pipeline/", "docs/", ".github/", "schema/", "scripts/")
LIEN = re.compile(r"\]\(([^)\s]+)\)")
CODE = re.compile(r"`([^`\n]+)`")
BLOC = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def references(texte: str) -> list[str]:
    """Les fichiers du dépôt que cite un texte Markdown : cibles des liens relatifs, et chemins entre accents graves
    sous un dossier du dépôt, sans gabarit (`<slug>`, `*`). Les blocs de code ne comptent pas."""
    texte = BLOC.sub("", texte)
    liens = [c.split("#")[0] for c in LIEN.findall(texte) if not re.match(r"[a-z]+:|#", c)]
    chemins = [
        c
        for c in CODE.findall(texte)
        if c.startswith(RACINES) and not re.search(r"[\s<>*{}]", c)
    ]
    return [r for r in liens + chemins if r]


def test_references_lit_les_liens_relatifs_et_les_chemins_du_depot():
    texte = (
        "Voir [l'ADR](docs/adr/0001-x.md#statut), [le site](https://exemple.ch), [plus bas](#structure),\n"
        "`pipeline/cron.py`, `conseils/index.json`, `web/src/routes/(carte)/`, `/commune/<slug>`,\n"
        "`docs/<n>.md` et `pnpm dev`.\n"
        "```bash\ncd pipeline/absent && uv run pytest\n```\n"
    )
    assert references(texte) == ["docs/adr/0001-x.md", "pipeline/cron.py", "web/src/routes/(carte)/"]


def test_les_fichiers_cites_par_la_readme_existent():
    cites = references((RACINE / "README.md").read_text(encoding="utf-8"))

    assert cites, "la README ne cite aucun fichier du dépôt"
    assert [c for c in cites if not (RACINE / c).exists()] == []
