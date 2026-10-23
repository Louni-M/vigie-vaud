"""Retraits (ADR 0007) : les corrections par élément de `retraits.json`, réappliquées à chaque import.

Un nom retiré à la demande d'une personne reviendrait dès que le cron relit l'élément : un Objet qu'OpenParlData
modifie, une page de liste qu'un scraper relit chaque jour, un rattrapage. `retraits.json`, écrit à la main dans le
dépôt de données, donne pour un champ d'un élément le texte corrigé ; `appliquer_retraits` le remet sur toute
l'archive après chaque import, pour tous les conseils, et renvoie les éléments qu'il change. Le nom retiré n'y figure
jamais : il disparaît de l'historique par une réécriture à la main (docs/retrait.md).
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path

from schema import Objet, Retrait, Retraits, Seance

FICHIER_RETRAITS = "retraits.json"


def lire_retraits(depot: Path) -> dict[str, list[Retrait]]:
    """`retraits.json` du dépôt de données, par clé d'élément ; vide si le fichier n'existe pas. Un fichier invalide
    lève `pydantic.ValidationError` : mieux vaut un import en échec qu'un nom retiré qui revient en silence."""
    try:
        texte = (depot / FICHIER_RETRAITS).read_bytes()
    except FileNotFoundError:
        return {}
    par_element: dict[str, list[Retrait]] = {}
    for r in Retraits.model_validate_json(texte).root:
        par_element.setdefault(r.element, []).append(r)
    return par_element


def _corriger(element: Objet | Seance, retrait: Retrait) -> Objet | Seance | None:
    """`element` avec le champ que vise `retrait` remplacé, ou `None` si la cible n'existe pas dans cet élément."""
    cible = retrait.cible
    if cible == "titre" and isinstance(element, Objet):
        return element.model_copy(update={"titre": retrait.texte})
    if cible == "nom" and isinstance(element, Seance):
        return element.model_copy(update={"nom": retrait.texte})
    if cible.startswith("point:") and isinstance(element, Seance):
        rang = int(cible.removeprefix("point:")) - 1
        if rang >= len(element.ordre_du_jour):
            return None
        points = list(element.ordre_du_jour)
        points[rang] = points[rang].model_copy(update={"titre": retrait.texte})
        return element.model_copy(update={"ordre_du_jour": points})
    if cible.startswith("document:"):
        lien = cible.removeprefix("document:")
        documents = getattr(element, "documents", None)
        if not documents or not any(d.lien == lien for d in documents):
            return None
        corriges = [d.model_copy(update={"titre": retrait.texte}) if d.lien == lien else d for d in documents]
        return element.model_copy(update={"documents": corriges})
    return None


def appliquer_retraits(archive: Mapping[str, object], retraits: Mapping[str, list[Retrait]]) -> dict[str, object]:
    """Les éléments de `archive` que `retraits` change, corrigés. Un retrait dont l'élément n'est pas (encore) dans
    l'archive attend son import ; un retrait dont la cible n'existe pas dans l'élément est signalé, sans faire
    échouer l'import."""
    corriges: dict[str, object] = {}
    for cle, liste in retraits.items():
        element = archive.get(cle)
        if not isinstance(element, Objet | Seance):
            continue
        nouveau = element
        for retrait in liste:
            corrige = _corriger(nouveau, retrait)
            if corrige is None:
                print(f"Retrait sans effet : {cle}, cible « {retrait.cible} » introuvable", file=sys.stderr)
                continue
            nouveau = corrige
        if nouveau != element:
            corriges[cle] = nouveau
    return corriges
