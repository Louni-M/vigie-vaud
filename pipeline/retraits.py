"""Retraits (ADR 0007) : les corrections par élément de `retraits.json`, réappliquées à chaque import.

Un nom retiré à la demande d'une personne reviendrait dès que le cron relit l'élément : un Objet qu'OpenParlData
modifie, une page de liste qu'un scraper relit chaque jour, un rattrapage. `retraits.json`, écrit à la main dans le
dépôt de données, donne pour un champ d'un élément le texte corrigé ; `appliquer_retraits` le remet sur toute
l'archive après chaque import, pour tous les conseils, et renvoie les éléments qu'il change. Le nom retiré n'y figure
jamais : il disparaît de l'historique par une réécriture à la main (docs/retrait.md).

Un point d'ordre du jour se vise par son rang, que la source peut décaler en insérant un point, et par l'empreinte
de son titre d'origine, tel que l'archive le garde (masqué) : un HMAC-SHA256 sous la clé secrète du dépôt de données
(`RETRAITS_CLE`), que personne ne peut recalculer pour essayer des noms sans cette clé. L'empreinte d'un point se
calcule depuis le clone du dépôt de données, sans écrire le titre ni la clé sur la ligne de commande (depuis
`pipeline/`, `RETRAITS_CLE` exportée) ; avec `--stdin`, le titre de la source, collé tel quel, est d'abord masqué
comme l'import le masque, avec les élu·e·s connu·e·s du conseil de la Séance :

    uv run python retraits.py --depot ../../vigie-vaud-donnees 5607/2026-06-11 point:4
    uv run python retraits.py --depot ../../vigie-vaud-donnees --stdin 5607/2026-06-11   # coller, puis Ctrl-D
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import re
import sys
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from masquage import elus_connus, masquer
from schema import MembresConseil, Objet, Retrait, Retraits, Seance

FICHIER_RETRAITS = "retraits.json"
# La clé des empreintes : un secret du dépôt de données, passé au cron par l'environnement (ADR 0007).
VARIABLE_CLE = "RETRAITS_CLE"
# Au moins 32 caractères : une clé courte se retrouverait par essais, et avec elle les noms.
LONGUEUR_MIN_CLE = 32


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


def cle_des_retraits(environ: Mapping[str, str] = os.environ) -> bytes | None:
    """La clé des empreintes, lue dans `RETRAITS_CLE` ; `None` si la variable est absente ou vide (un secret non
    défini arrive vide dans un workflow). Une clé trop courte lève `ValueError`."""
    valeur = environ.get(VARIABLE_CLE, "").strip()
    if not valeur:
        return None
    if len(valeur) < LONGUEUR_MIN_CLE:
        raise ValueError(f"{VARIABLE_CLE} trop courte : {LONGUEUR_MIN_CLE} caractères au moins (docs/retrait.md)")
    return valeur.encode("utf-8")


def empreinte(titre: str, cle: bytes) -> str:
    """HMAC-SHA256 hexadécimal du titre, en Unicode NFC et espaces réduits à un seul, sous `cle`."""
    normalise = " ".join(unicodedata.normalize("NFC", titre).split())
    return hmac.new(cle, normalise.encode("utf-8"), hashlib.sha256).hexdigest()


def _rangs(seance: Seance, retrait: Retrait, cle: bytes | None) -> list[int] | None:
    """Les rangs (à partir de 0) des points que `retrait` corrige, `[]` s'il a déjà corrigé le sien, `None` s'il est
    sans effet. Avec une empreinte et la clé, chaque point qui a cette empreinte, quel que soit son rang : le même
    titre deux fois porte deux fois le nom. Sans empreinte, ou sans la clé pour la vérifier, le point du rang ; mais
    un retrait à empreinte dont un point porte déjà le texte corrigé ne touche à rien, même sans la clé."""
    points = seance.ordre_du_jour
    # Un point qui porte déjà le texte corrigé : un passage précédent l'a corrigé, la Séance n'a pas été relue.
    deja_corrige = any(p.titre == retrait.texte for p in points)
    if retrait.empreinte is not None:
        if cle is not None:
            vises = [
                i for i, p in enumerate(points) if hmac.compare_digest(empreinte(p.titre, cle), retrait.empreinte)
            ]
            if vises:
                return vises
            return [] if deja_corrige else None
        if deja_corrige:
            # Sans la clé, le point corrigé, peut-être déplacé, reste où il est : le rang écraserait un autre point.
            return []
    rang = int(retrait.cible.removeprefix("point:")) - 1
    return [rang] if rang < len(points) else None


def _non_verifie(retrait: Retrait, cle: bytes | None) -> bool:
    """Un retrait à empreinte, sans la clé pour la vérifier : il vaut pour le point de son rang."""
    return retrait.empreinte is not None and cle is None


def _corriger(element: Objet | Seance, retrait: Retrait, cle: bytes | None) -> Objet | Seance | None:
    """`element` avec le champ que vise `retrait` remplacé, ou `None` si la cible n'existe pas dans cet élément."""
    cible = retrait.cible
    if cible == "titre" and isinstance(element, Objet):
        return element.model_copy(update={"titre": retrait.texte})
    if cible == "nom" and isinstance(element, Seance):
        return element.model_copy(update={"nom": retrait.texte})
    if cible.startswith("point:") and isinstance(element, Seance):
        rangs = _rangs(element, retrait, cle)
        if rangs is None:
            return None
        points = [
            p.model_copy(update={"titre": retrait.texte}) if i in rangs else p
            for i, p in enumerate(element.ordre_du_jour)
        ]
        return element.model_copy(update={"ordre_du_jour": points})
    if cible.startswith("document:"):
        lien = cible.removeprefix("document:")
        documents = getattr(element, "documents", None)
        if not documents or not any(d.lien == lien for d in documents):
            return None
        corriges = [d.model_copy(update={"titre": retrait.texte}) if d.lien == lien else d for d in documents]
        return element.model_copy(update={"documents": corriges})
    return None


def cible_affichee(retrait: Retrait) -> str:
    """La cible d'un retrait telle que le journal et les issues la montrent : sans le lien d'un document, dont le nom
    de fichier peut porter le nom retiré."""
    return "document" if retrait.cible.startswith("document:") else retrait.cible


def appliquer_retraits(
    archive: Mapping[str, object], retraits: Mapping[str, list[Retrait]], cle: bytes | None = None
) -> dict[str, object]:
    """Les éléments de `archive` que `retraits` change, corrigés. Un retrait dont l'élément n'est pas (encore) dans
    l'archive attend son import ; un retrait dont la cible n'existe pas dans l'élément est signalé, sans faire
    échouer l'import (le cron en ouvre l'issue, `constat_des_retraits`). Sans `cle`, un retrait à empreinte vaut
    pour le point de son rang, comme un retrait sans empreinte, et il est signalé comme non vérifié."""
    corriges: dict[str, object] = {}
    for cle_element, liste in retraits.items():
        element = archive.get(cle_element)
        if not isinstance(element, Objet | Seance):
            continue
        nouveau = element
        for retrait in liste:
            cible = cible_affichee(retrait)
            if _non_verifie(retrait, cle):
                print(
                    f"Retrait non vérifié : {cle_element}, « {cible} » corrigé au rang, {VARIABLE_CLE} absente",
                    file=sys.stderr,
                )
            corrige = _corriger(nouveau, retrait, cle)
            if corrige is None:
                print(f"Retrait sans effet : {cle_element}, cible « {cible} » introuvable", file=sys.stderr)
                continue
            nouveau = corrige
        if nouveau != element:
            corriges[cle_element] = nouveau
    return corriges


@dataclass(frozen=True)
class ConstatRetraits:
    """Ce que le cron signale des retraits, sans jamais leur texte : ceux qui sont sans effet sur l'élément de
    l'archive (cible introuvable, empreinte qu'aucun point n'a), et ceux à empreinte qu'il n'a pas pu vérifier, faute
    de clé."""

    sans_effet: list[Retrait]
    non_verifies: list[Retrait]


def _lire_element(depot: Path, cle_element: str) -> Objet | Seance | None:
    conseil, nom = cle_element.split("/", 1)
    for dossier, modele in (("objets", Objet), ("seances", Seance)):
        chemin = depot / "conseils" / conseil / dossier / f"{nom}.json"
        if chemin.is_file():
            return modele.model_validate_json(chemin.read_bytes())
    return None


def constat_des_retraits(depot: Path, cle: bytes | None) -> ConstatRetraits:
    """Les retraits de `retraits.json` sans effet sur l'élément tel qu'il est dans `depot`, et ceux qui ne peuvent
    être vérifiés sans `cle`. Un élément pas encore importé attend son import : il n'est pas sans effet. Lève
    `pydantic.ValidationError` pour un `retraits.json` invalide."""
    sans_effet: list[Retrait] = []
    non_verifies: list[Retrait] = []
    for cle_element, liste in lire_retraits(depot).items():
        element = _lire_element(depot, cle_element)
        for retrait in liste:
            if _non_verifie(retrait, cle):
                non_verifies.append(retrait)
            if element is not None and _corriger(element, retrait, cle) is None:
                sans_effet.append(retrait)
    return ConstatRetraits(sans_effet=sans_effet, non_verifies=non_verifies)


def masquer_comme_l_import(titre: str, depot: Path, conseil: str) -> str:
    """`titre`, tel que la source le donne, masqué comme l'import le masque (ADR 0007) : en épargnant les élu·e·s
    connu·e·s du conseil que le clone `depot` connaît, contributeur·rice·s de ses Objets et `membres.json`. Les
    pétitionnaires, que seule la source connaît, n'y sont pas."""
    objets = [Objet.model_validate_json(f.read_bytes()) for f in sorted(depot.glob(f"conseils/{conseil}/objets/*.json"))]
    try:
        membres = MembresConseil.model_validate_json((depot / f"conseils/{conseil}/membres.json").read_bytes()).membres
    except FileNotFoundError:
        membres = []
    return masquer(titre.strip(), elus_connus(objets) | frozenset(membres))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=f"Empreinte du titre d'origine d'un point d'ordre du jour, sous la clé {VARIABLE_CLE} (ADR 0007)."
    )
    parser.add_argument("--depot", type=Path, help="clone local du dépôt de données")
    parser.add_argument("element", nargs="?", help="clé de la Séance, `5607/2026-06-11`")
    parser.add_argument("cible", nargs="?", help="le point, `point:<n>`")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="lire sur l'entrée standard le titre de la source, tel quel : il est masqué comme à l'import",
    )
    args = parser.parse_args(argv)

    try:
        cle = cle_des_retraits()
    except ValueError as e:
        raise SystemExit(str(e)) from None
    if cle is None:
        raise SystemExit(f"{VARIABLE_CLE} absente : l'exporter d'abord (docs/retrait.md)")
    if args.stdin:
        # Le masquage dépend du conseil (ses élu·e·s connu·e·s) : sans lui, l'empreinte serait fausse en silence.
        if args.depot is None or args.element is None:
            parser.error("--stdin avec --depot et la clé de la Séance")
        depot = args.depot.resolve()
        if not isinstance(_lire_element(depot, args.element), Seance):
            raise SystemExit(f"Aucune Séance {args.element} dans le dépôt de données")
        conseil = args.element.split("/", 1)[0]
        print(empreinte(masquer_comme_l_import(sys.stdin.read(), depot, conseil), cle))
        return
    if args.depot is None or args.element is None or not re.fullmatch(r"point:[1-9][0-9]*", args.cible or ""):
        parser.error("--depot, la clé de la Séance et `point:<n>`, ou --stdin")
    seance = _lire_element(args.depot.resolve(), args.element)
    if not isinstance(seance, Seance):
        raise SystemExit(f"Aucune Séance {args.element} dans le dépôt de données")
    rang = int(args.cible.removeprefix("point:")) - 1
    if not 0 <= rang < len(seance.ordre_du_jour):
        raise SystemExit(f"La Séance {args.element} n'a que {len(seance.ordre_du_jour)} point(s)")
    print(empreinte(seance.ordre_du_jour[rang].titre, cle))


if __name__ == "__main__":
    main()
