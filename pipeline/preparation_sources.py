"""Préparation des sources communales de `sources.json` (spec de J3, « Scripts de préparation » ; ADR 0010).

Les déclarations des communes scrapées ne changent que par une PR, jamais par le cron. Ce script aide à les écrire et à
les tenir justes :

- `verifier_declarations` : les règles de déclaration, sans réseau (les tests de CI les passent sur le fichier réel).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError

from schema import FichierSources, lire_sources


def verifier_declarations(chemin_sources: Path, chemin_communes: Path) -> list[str]:
    """Les écarts de `sources.json` aux règles de déclaration, sans réseau : chaque n° OFS déclaré existe dans
    `communes.json` ; un conseil n'a qu'une source ; la plateforme et la variante citées sont déclarées et permettent
    le niveau ; une commune non couverte a une raison et pas de conseil ; une commune couverte d'une plateforme a un
    conseil, une variante et une page `seances`. Liste vide : tout est juste."""
    try:
        fichier = lire_sources(chemin_sources)
    except ValidationError as e:
        return [f"sources.json invalide : {e}"]
    communes = {c["bfs"] for c in json.loads(chemin_communes.read_text(encoding="utf-8"))}
    return _ecarts(fichier, communes)


def _ecarts(fichier: FichierSources, communes: set[int]) -> list[str]:
    ecarts: list[str] = []
    conseils: dict[str, list[str]] = defaultdict(list)
    plateformes = {p.id: p for p in fichier.plateformes}
    for s in fichier.sources:
        declares = []
        if s.couverture is not None and s.couverture.communes != "canton":
            declares += s.couverture.communes
        if s.conseil is not None:
            conseils[s.conseil.cle].append(s.id)
            if s.conseil.commune is not None:
                declares.append(s.conseil.commune)
        ecarts += [f"{s.id} : n° OFS {o} absent de communes.json" for o in dict.fromkeys(declares) if o not in communes]
        non_couverte = s.couverture is not None and s.couverture.mode == "non_couvert"
        if non_couverte and (s.couverture.raison is None or s.conseil is not None):
            ecarts.append(f"{s.id} : une commune non couverte a une raison et pas de conseil")
        if s.site is None:
            continue
        plateforme = plateformes.get(s.site.plateforme)
        if plateforme is None:
            ecarts.append(f"{s.id} : plateforme {s.site.plateforme} non déclarée")
            continue
        if non_couverte:
            continue
        if s.conseil is None:
            ecarts.append(f"{s.id} : une commune couverte déclare son conseil")
            continue
        if s.site.variante is None or s.site.seances is None:
            ecarts.append(f"{s.id} : une commune couverte déclare sa variante et sa page des Séances")
            continue
        variante = next((v for v in plateforme.variantes if v.id == s.site.variante), None)
        if variante is None:
            ecarts.append(f"{s.id} : variante {s.site.variante} non déclarée dans {plateforme.id}")
        elif sorted(s.conseil.donne) not in [sorted(n) for n in variante.niveaux]:
            ecarts.append(
                f"{s.id} : la variante {plateforme.id}/{variante.id} ne permet pas le niveau "
                + " + ".join(sorted(s.conseil.donne))
            )
    ecarts += [
        f"conseil {cle} déclaré par plusieurs sources : {', '.join(ids)}" for cle, ids in conseils.items() if len(ids) > 1
    ]
    return ecarts
