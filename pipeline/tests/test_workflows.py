"""Chaque action tierce des workflows est épinglée par SHA de commit (40 caractères), sa version complète en
commentaire (`@<sha> # v7.0.1`), y compris dans le déclencheur modèle du dépôt de données : une étiquette se déplace,
un SHA non. Dependabot (`.github/dependabot.yml`) tient ces épingles et leur commentaire à jour.

Seules exceptions : les actions locales (`./…`) et l'appel du workflow réutilisable de ce dépôt par le déclencheur
modèle (`Louni-M/vigie-vaud/…@main`), dont la référence relève de #187.
"""

import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

DOSSIERS = (
    RACINE / ".github" / "workflows",
    RACINE / "pipeline" / "depot-donnees" / ".github" / "workflows",
)
CE_DEPOT = "Louni-M/vigie-vaud/"
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)(.*)$")
EPINGLE = re.compile(r"^[\w.-]+/[\w.-]+(?:/[^@\s]+)?@[0-9a-f]{40}$")
VERSION = re.compile(r"^\s*# v\d+\.\d+\.\d+\s*$")


def references(texte: str) -> list[tuple[str, str]]:
    """Les `uses:` d'un workflow, avec ce qui les suit sur la ligne (le commentaire de version)."""
    return [(m[1], m[2]) for ligne in texte.splitlines() if (m := USES.match(ligne))]


def mal_epinglees(texte: str) -> list[str]:
    """Les `uses:` tierces qui ne sont pas épinglées par SHA avec leur version complète en commentaire."""
    return [
        cible
        for cible, suite in references(texte)
        if not cible.startswith(("./", CE_DEPOT))
        and not (EPINGLE.match(cible) and VERSION.match(suite))
    ]


def workflows() -> list[Path]:
    return sorted(f for d in DOSSIERS for f in [*d.glob("*.yml"), *d.glob("*.yaml")])


def test_mal_epinglees_ne_retient_que_les_actions_tierces_sans_sha_ni_version():
    sha = "3d3c42e5aac5ba805825da76410c181273ba90b1"
    texte = (
        f"      - uses: actions/checkout@{sha} # v7.0.1\n"
        "      - uses: actions/setup-node@v7\n"
        f"        uses: actions/deploy-pages@{sha}\n"
        f"      - uses: astral-sh/setup-uv@{sha} # v10\n"
        f"      - uses: github/codeql-action/init@{sha} # v4.31.2\n"
        f"      - uses: actions/checkout@{sha[:7]} # v7.0.1\n"
        "      - uses: ./.github/actions/locale\n"
        "    uses: Louni-M/vigie-vaud/.github/workflows/cron.yml@main\n"
        "      # uses: actions/cache@v5\n"
    )
    assert mal_epinglees(texte) == [
        "actions/setup-node@v7",
        f"actions/deploy-pages@{sha}",
        f"astral-sh/setup-uv@{sha}",
        f"actions/checkout@{sha[:7]}",
    ]


def test_chaque_workflow_a_des_uses_lues():
    lus = {
        f.relative_to(RACINE).as_posix(): len(references(f.read_text(encoding="utf-8")))
        for f in workflows()
    }

    assert set(lus) >= {
        ".github/workflows/ci.yml",
        ".github/workflows/cron.yml",
        ".github/workflows/publier.yml",
        "pipeline/depot-donnees/.github/workflows/cron.yml",
    }
    assert [f for f, n in lus.items() if n == 0] == []


def test_les_actions_tierces_sont_epinglees_par_sha():
    fautes = {
        f.relative_to(RACINE).as_posix(): m
        for f in workflows()
        if (m := mal_epinglees(f.read_text(encoding="utf-8")))
    }
    assert fautes == {}
