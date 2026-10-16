"""Masquage des noms de particuliers par le cron (ADR 0007), avant tout commit dans le dépôt de données.

C'est la version du cron de `web/src/lib/masquage.ts` (`masquerNoms`), elle-même portage de `mask_names` (étiquette
`chantiers-hebergee`) : mêmes expressions, mêmes cas. Elle n'y ajoute qu'une chose, pour les conseils : les
**élu·e·s connu·e·s** du conseil, nommé·e·s en vertu de leur mandat, sont épargné·e·s. Une personne n'est épargnée
que si son nom entier est celui d'un·e élu·e (à la casse et aux accents près) : un homonyme partiel est masqué.
Approche prudente, comme sur le site : en cas de doute, on masque.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from schema import Objet

MASQUE = "[particulier]"
ENTITE_RE = re.compile(
    r"\b(?:S\.?A\.?|Sàrl|S\.à\.r\.l\.?|SARL|GmbH|AG|SNC|SCI|Ltd|Inc|"
    r"Swisscom|Sunrise|Salt|Orange|UPC|CFF|SBB|Migros|Coop|Banque|BCV|Raiffeisen|Poste|"
    r"Commune|Ville|Municipalit[ée]|[ÉE]tat|Canton|Conf[ée]d[ée]ration|Paroisse|[ÉE]glise|"
    r"Fondation|Association|Soci[ée]t[ée]|Coop[ée]rative|Communaut[ée]|PPE|Hoirie|Consortage|"
    r"Groupe|Holding|Immobili[eè]re?|Caisse|Assurances?|Fonds|Hôpital|H[ôo]pitaux|[ÉE]cole|Club|"
    r"Romande Energie|Services?|Infra|SI\b|Syndicat|Entreprise|Cave|Domaine|Hôtel|Restaurant)(?!\w)",
    re.I,
)
CIVILITE = r"(?:M\.|MM\.|Mme|Mmes|Mlle|Monsieur|Madame|Messieurs|Mesdames)"
COMPTE_RE = re.compile(
    r"(pour\s+(?:le\s+)?compte\s+(?:de\s+(?:la\s+|l[’'´]\s*|de\s+)?|d[’'´]\s*|des\s+|du\s+))"
    r"([^.,;:()/\n]+?)(?=\s*(?:[.,;:()/]|\savec\s|\set\s(?:de\s|d[’'´])|$))",
    re.I,
)
NOM = r"[A-ZÀ-Ý](?:\.(?:-[A-ZÀ-Ý]\.)?|[\w’'´-]*)"  # « Dupont », « J. », « J.-P. »
# Les mêmes correspondances que `CIVILITE_RE` du site, la ou les civilités (groupe 1) séparées des noms (groupe 2).
CIVILITE_RE = re.compile(rf"\b({CIVILITE}(?:\s+(?:et|&)\s+{CIVILITE})*\s+)({NOM}(?:\s+(?:et\s+|&\s+)?{NOM})*)")
ENTRE_PERSONNES = re.compile(r"(\s+(?:et|&)\s+)")
LIAISONS = {"et", "&", "de", "du", "des", "da", "dos", "von", "van", "der", "le", "la"}


def masquer(titre: str, elus: Iterable[str] = ()) -> str:
    """`titre`, les noms de particuliers remplacés par « [particulier] ». Les noms de `elus` (noms complets, tels
    que les contributeurs des Objets les donnent) restent."""
    connus = {_cle(e) for e in elus if e.strip()}

    def personne(m: re.Match) -> str:
        parties = ENTRE_PERSONNES.split(m[2])
        noms = parties[0::2]
        if all(_cle(n) in connus for n in noms):
            return m[0]
        if not any(_cle(n) in connus for n in noms):
            return MASQUE
        return m[1] + "".join(p if i % 2 or _cle(p) in connus else MASQUE for i, p in enumerate(parties))

    def compte(m: re.Match) -> str:
        parties = re.split(r"(\s-\s)", m[2])
        for i in range(0, len(parties), 2):
            p = parties[i]
            if _cle(p) in connus:
                continue
            if re.search(CIVILITE, p) or (not ENTITE_RE.search(p) and _ressemble_a_un_nom(p)):
                parties[i] = MASQUE
        return m[1] + "".join(parties)

    s = titre
    # Formes juridiques avec points (« S.A. », « A.G. », « S.à r.l. ») : sinon le point coupe le segment.
    s = re.sub(r"\bS\.\s?A\.?(?!\w)", "SA", s)
    s = re.sub(r"\bA\.\s?G\.?(?!\w)", "AG", s)
    s = re.sub(r"\bS\.?\s?à\s?r\.?\s?l\.?(?!\w)", "Sàrl", s, flags=re.I)
    # Civilités d'abord (« M. Dupont ») : le point de « M. » couperait sinon le segment « pour le compte de ».
    s = CIVILITE_RE.sub(personne, s)
    return COMPTE_RE.sub(compte, s)


def _ressemble_a_un_nom(segment: str) -> bool:
    """Suite de 2 à 8 mots tous à majuscule initiale (hors liaisons), sans chiffre : « Occipinti Santo »."""
    mots = [m for m in re.split(r"\s+", segment.strip()) if m]
    noms = [m for m in mots if m.lower() not in LIAISONS]
    return 2 <= len(noms) <= 8 and not any(c.isdigit() for c in segment) and all(m[0].isupper() for m in noms)


def _cle(nom: str) -> str:
    """Le nom à comparer : sans accents ni casse, les espaces resserrés (« Loris SOCCHI » = « Loris Socchi »)."""
    sans_accents = "".join(c for c in unicodedata.normalize("NFKD", nom) if not unicodedata.combining(c))
    return " ".join(re.sub(r"\s*-\s*", "-", sans_accents.replace("’", "'")).casefold().split())


# --- Conseils ----------------------------------------------------------------------------------------------------

# Une pétition n'a pas d'auteur·e dans le dépôt : on ne sait pas qui l'a déposée, et ce n'est pas un·e élu·e.
TYPES_SANS_AUTEUR = frozenset({"Pétition"})
# Un point d'ordre du jour qui renvoie à une demande de grâce, à défaut de numéro d'Objet : par son titre.
GRACE_RE = re.compile(r"\b(?:demandes?|recours)\s+(?:de|en)\s+gr[âa]ces?\b|^\W*gr[âa]ces?\b(?!\s+(?:à|au|aux)\b)", re.I)
# Au Grand Conseil, le numéro d'une demande de grâce : `26_GRA_1`.
NUMERO_GRACE_RE = re.compile(r"_GRA_", re.I)


def elus_connus(objets: Iterable[Objet]) -> frozenset[str]:
    """Les élu·e·s connu·e·s d'un conseil, tiré·e·s de ses Objets (archive et import en cours) : toute personne
    contributrice d'un Objet autre qu'une pétition."""
    return frozenset(
        c.nom for o in objets if o.type not in TYPES_SANS_AUTEUR for c in o.contributeurs if c.sorte == "personne"
    )


def est_point_de_grace(titre: str, numero_objet: str | None, numeros_de_grace: Iterable[str]) -> bool:
    """Le point renvoie-t-il à une demande de grâce : par le numéro de son Objet (`numeros_de_grace`, ceux des
    demandes de grâce lues chez la source, ou la forme `_GRA_` du Grand Conseil), ou par son titre ?"""
    if numero_objet and (numero_objet in set(numeros_de_grace) or NUMERO_GRACE_RE.search(numero_objet)):
        return True
    return bool(GRACE_RE.search(titre))
