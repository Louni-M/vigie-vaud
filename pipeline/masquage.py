"""Masquage des noms de particuliers par le cron (ADR 0007), avant tout commit dans le dépôt de données.

C'est la version du cron de `web/src/lib/masquage.ts` (`masquerNoms`), elle-même portage de `mask_names` (étiquette
`chantiers-hebergee`) : mêmes expressions, mêmes cas. Elle n'y ajoute que deux choses, pour les conseils :

- les **élu·e·s connu·e·s** du conseil, nommé·e·s en vertu de leur mandat, sont épargné·e·s. Une personne n'est
  épargnée que si son nom entier est celui d'un·e élu·e (à la casse et aux accents près) : un homonyme partiel est
  masqué ;
- les **auteur·e·s d'une pétition** sont masqué·e·s même sans civilité, comme Lausanne les nomme (« Pétition de
  Gaber Mark et crts », « Pétition déposée le 7 mai 2024 de Lya Blanc et crts : »), sauf élu·e connu·e ou entité ;
- les **pétitionnaires que la source connaît** (prénom et nom des contributeurs d'une pétition) sont masqué·e·s dans
  les textes de leur pétition sous toutes leurs formes : nom de fichier en snake_case
  (« 2025_08_rp_petition_paul_exemple_parc.pdf »), sans civilité ni « Pétition de » (« par Exemple Paul et crts »,
  « (Paul Exemple) »), nom de famille seul (« rapport pétition Exemple.pdf »), sauf élu·e connu·e ;
- les **coordonnées** deviennent « [coordonnées] » : tout téléphone suisse et tout courriel, partout, et l'adresse
  postale (voie et numéro, NPA et localité) qui suit un particulier masqué (« de [particulier] - Chemin des
  Lilas 46 - 1004 Lausanne - 079 … : »). Ailleurs, une adresse est celle d'une entité ou d'un immeuble, sujet de
  l'Objet (« Préavis N° 2023/44 - Chemin de la Colline 6-8 - Vente… ») : elle reste.

Approche prudente, comme sur le site : en cas de doute, on masque.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from schema import Objet

MASQUE = "[particulier]"
COORDONNEES = "[coordonnées]"
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
# L'auteur·e d'une pétition, sans civilité : une suite de noms propres, les particules comprises (« Jean de
# Montmollin »), après « Pétition [au CC] [déposée le <date>] de » ; plusieurs auteur·e·s séparé·e·s par « et » ou une
# virgule. La suite n'est prise que si un séparateur la termine (« et crts », « : », « - », « déposée »…) : « Pétition
# de Montelly vit ! » n'est pas un nom.
PARTICULE = r"(?:(?:de|du|des|von|van|der|da|dos|di|le|la)\s+|d[’'])"
PERSONNE = rf"(?!{CIVILITE}\s){NOM}(?:\s+{PARTICULE}?{NOM})*"
DATE = r"\d{1,2}(?:er)?\s+\w+\s+\d{4}"
PETITION_RE = re.compile(
    rf"(\b[Pp][ée]tition(?:\s+au\s+CC)?(?:\s+d[ée]pos[ée]e?\s+le\s+{DATE})?\s+de\s+)"
    rf"({PERSONNE}(?:(?:\s+et|,)\s+{PERSONNE})*)"
    r"(?=\s+et\s+(?:crts|consorts)\b|\s*[-:,;.(«\"“]|\s+d[ée]pos[ée]e?\b|\s*$)"
)
ENTRE_PETITIONNAIRES = re.compile(r"((?:\s+et|,)\s+)")
# Un collectif qui signe une pétition reste nommé, comme une entité.
COLLECTIF_RE = re.compile(r"^(?:Collectif|Comité|Habitant[e·]*s|Riverain[e·]*s|Parents|Amis|Groupement|Mouvement|Pro)\b")
# Entre le prénom et le nom d'un·e pétitionnaire connu·e, ou dans un nom composé : espace, tiret ou souligné.
ENTRE_LES_NOMS = r"[\s_-]+"
# Un nom de famille plus court n'est masqué qu'avec le prénom : seul, ce serait un mot (« Do », « Py »).
NOM_SEUL_MIN = 3
# Un téléphone suisse, sous toutes ses formes : « 079 000 00 00 », « 021/000.00.00 », « +41 79 000 00 00 », « 0041 21… ».
TELEPHONE_RE = re.compile(
    r"(?<![\d.])(?:(?:\+|00)\s?41\s?(?:\(0\)\s?)?\d{2}|0\d{2})\s?[/.-]?\s?\d{3}\s?[.-]?\s?\d{2}\s?[.-]?\s?\d{2}(?!\d)"
)
COURRIEL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Une partie d'adresse postale, que « - » ou une virgule séparent de la suivante : voie et numéro (« Chemin des
# Lilas 46 », « av. de la Gare 4b »), NPA et localité (« 1004 Lausanne »), case postale.
VOIE = (
    r"(?i:chemin|ch\.|rue|ruelle|avenue|av\.|route|rte|place|pl\.|boulevard|bd|quai|all[ée]e|sentier|impasse|"
    r"passage|promenade|escaliers|mont[ée]e|chauss[ée]e|esplanade|clos|square|faubourg|grand-rue)"
)
FIN_DE_PARTIE = r"(?=\s+[-–]\s|\s*[,:;«»()\"“]|\s*$)"
DANS_LA_PARTIE = r"(?:(?!\s[-–]\s)[^,:;«»()\"“])"
PARTIE_D_ADRESSE = (
    rf"(?:{VOIE}\s{DANS_LA_PARTIE}*?\d+\s?[a-zA-Z]?|(?:CH-?)?[1-9]\d{{3}}\s+[A-ZÀ-Ý]{DANS_LA_PARTIE}*?"
    rf"|(?i:case\s+postale|CP)\s+\d+){FIN_DE_PARTIE}"
)
# Les coordonnées qui suivent un particulier masqué : une ou plusieurs parties, réunies en une seule.
COORDONNEES_APRES_RE = re.compile(
    rf"({re.escape(MASQUE)}\s*[-–,]\s*)(?:{PARTIE_D_ADRESSE}|{re.escape(COORDONNEES)})"
    rf"(?:\s*[-–,]\s*(?:{PARTIE_D_ADRESSE}|{re.escape(COORDONNEES)}))*"
)


def masquer(titre: str, elus: Iterable[str] = (), petitionnaires: Iterable[tuple[str, str]] = ()) -> str:
    """`titre`, les noms de particuliers remplacés par « [particulier] ». Les noms de `elus` (noms complets, tels
    que les contributeurs des Objets les donnent) restent. `petitionnaires` (prénom, nom de famille) : les
    pétitionnaires que la source connaît, masqué·e·s où qu'ils ou elles soient nommé·e·s, sauf élu·e connu·e."""
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

    def petition(m: re.Match) -> str:
        parties = ENTRE_PETITIONNAIRES.split(m[2])
        garde = [_cle(p) in connus or bool(ENTITE_RE.search(p) or COLLECTIF_RE.search(p)) for p in parties[0::2]]
        if not any(garde):
            return m[1] + MASQUE
        return m[1] + "".join(p if i % 2 or garde[i // 2] else MASQUE for i, p in enumerate(parties))

    s = TELEPHONE_RE.sub(COORDONNEES, titre)
    s = COURRIEL_RE.sub(COORDONNEES, s)
    # Formes juridiques avec points (« S.A. », « A.G. », « S.à r.l. ») : sinon le point coupe le segment.
    s = re.sub(r"\bS\.\s?A\.?(?!\w)", "SA", s)
    s = re.sub(r"\bA\.\s?G\.?(?!\w)", "AG", s)
    s = re.sub(r"\bS\.?\s?à\s?r\.?\s?l\.?(?!\w)", "Sàrl", s, flags=re.I)
    # Civilités d'abord (« M. Dupont ») : le point de « M. » couperait sinon le segment « pour le compte de ».
    s = CIVILITE_RE.sub(personne, s)
    s = PETITION_RE.sub(petition, s)
    s = COMPTE_RE.sub(compte, s)
    s = _masquer_petitionnaires(s, petitionnaires, connus)
    return COORDONNEES_APRES_RE.sub(lambda m: m[1] + COORDONNEES, s)


def _masquer_petitionnaires(s: str, petitionnaires: Iterable[tuple[str, str]], connus: set[str]) -> str:
    """`s`, chaque pétitionnaire masqué·e : prénom et nom dans un ordre ou dans l'autre, puis nom de famille seul,
    à la casse et aux accents près. Un·e élu·e connu·e reste, et un nom de famille que porte un·e élu·e connu·e
    n'est masqué qu'avec le prénom."""
    mots_des_elus = {mot for e in connus for mot in re.split(r"[\s-]+", e)}
    motifs = []
    for prenom, nom in petitionnaires:
        if not nom.strip() or _cle(f"{prenom} {nom}") in connus:
            continue
        if prenom.strip():
            motifs += [_motif(f"{prenom} {nom}"), _motif(f"{nom} {prenom}")]
        mots = _cle(nom).replace("-", " ").split()
        if len("".join(mots)) >= NOM_SEUL_MIN and not mots_des_elus & set(mots):
            motifs.append(_motif(nom))
    if not motifs:
        return s
    # Le plus long d'abord : « Paul Exemple » avant « Exemple ». Un nom est entouré de non-lettres (« _ » compris).
    motif = re.compile(rf"(?<![^\W_])(?:{'|'.join(sorted(motifs, key=len, reverse=True))})(?![^\W_])")
    plie = _plier(s)
    morceaux, fin = [], 0
    for m in motif.finditer(plie):
        morceaux += [s[fin : m.start()], MASQUE]
        fin = m.end()
    return "".join(morceaux) + s[fin:]


def _motif(nom: str) -> str:
    return ENTRE_LES_NOMS.join(re.escape(mot) for mot in re.split(ENTRE_LES_NOMS, _plier(nom.strip())))


def _plier(s: str) -> str:
    """`s` sans accents ni casse, caractère pour caractère : une position de `_plier(s)` est la même dans `s`."""
    plie = []
    for c in s.replace("’", "'"):
        sans_accent = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x)).lower()
        plie.append(sans_accent if len(sans_accent) == 1 else c)
    return "".join(plie)


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
