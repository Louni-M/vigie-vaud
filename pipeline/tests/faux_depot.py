"""Faux dépôt de données pour la couche git du cron : un dépôt nu local tient lieu de GitHub, et des clones y
poussent comme le workflow et, en concurrence, un autre passage. Aucun réseau : le dépôt nu est un chemin.

Le fixture `depot_nu` (dans `conftest.py`) isole git de la configuration de la machine (identité du workflow, ni
configuration globale ni système) et rend un `DepotNu` amorcé d'un premier commit sur `main`.
"""

import subprocess
from pathlib import Path

IDENTITE = {
    "GIT_AUTHOR_NAME": "github-actions[bot]",
    "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
    "GIT_COMMITTER_NAME": "github-actions[bot]",
    "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
}


def git(depot: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(depot), *args], check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def crochet(depot_git: Path, nom: str, script: str) -> None:
    """Écrit le crochet `nom` (`pre-commit`, `pre-receive`…) dans le dossier git `depot_git` (`.git` d'un clone,
    ou le dépôt nu lui-même)."""
    chemin = depot_git / "hooks" / nom
    chemin.parent.mkdir(exist_ok=True)
    chemin.write_text("#!/bin/sh\n" + script + "\n", encoding="utf-8", newline="\n")
    chemin.chmod(0o755)


class DepotNu:
    """Le dépôt nu `origine.git` sous `racine`, amorcé d'un commit sur `main`."""

    def __init__(self, racine: Path):
        self.racine = racine
        self.chemin = racine / "origine.git"
        git(racine, "init", "--quiet", "--bare", "--initial-branch=main", str(self.chemin))
        amorce = self.cloner("amorce")
        (amorce / "README.md").write_text("Dépôt de données\n", encoding="utf-8")
        git(amorce, "add", "README.md")
        git(amorce, "commit", "--quiet", "-m", "Amorce")
        git(amorce, "push", "--quiet")

    def cloner(self, nom: str) -> Path:
        clone = self.racine / nom
        git(self.racine, "clone", "--quiet", str(self.chemin), str(clone))
        return clone

    def pousser_depuis(self, clone: Path, chemin: str, contenu: str, message: str) -> None:
        """Un autre passage qui committe `contenu` dans `chemin` et pousse : le prochain push d'un clone en retard
        est refusé."""
        git(clone, "pull", "--quiet")
        (clone / chemin).parent.mkdir(parents=True, exist_ok=True)
        (clone / chemin).write_text(contenu, encoding="utf-8")
        git(clone, "add", "--", chemin)
        git(clone, "commit", "--quiet", "-m", message)
        git(clone, "push", "--quiet")

    def journal(self) -> list[str]:
        """Les messages des commits de `main`, du plus récent au plus ancien."""
        return git(self.chemin, "log", "--format=%s", "main").splitlines()

    def fichier(self, chemin: str) -> str:
        return git(self.chemin, "show", f"main:{chemin}")

    def refuser_les_push(self) -> None:
        crochet(self.chemin, "pre-receive", "echo 'push refusé par le dépôt' >&2\nexit 1")
