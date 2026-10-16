"""Rattachement par le nom (ADR 0016) : les communes qu'un texte nomme, d'après `communes.json`.

Un élément d'une source qui porte sur le canton (en J1, les Objets du Grand Conseil) est rattaché aux communes dont
le nom apparaît dans son texte : communes actuelles, anciennes communes et anciens noms, qui mènent tous à la commune
actuelle. Les Objets et les Séances d'un conseil communal n'appartiennent qu'à leur commune ; les Séances du Grand
Conseil ne sont rattachées à aucune.

- `rattacher(texte, origine)` est le point pur : les communes d'un texte, hors contextes exclus (données plus bas,
  communes à toutes les sources) ;
- `rattacher_objet(titre, documents)` l'applique au titre masqué d'un Objet et au texte de ses documents, avec la
  règle des 10 communes ;
- `corriger` et `lire_corrections` appliquent `corrections.json`, écrit à la main dans le dépôt de données.

Un changement de règle, comme une fusion (`communes.json` mis à jour), se recalcule en relançant le rattrapage.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from schema import RACINE, CommuneRattachee, Conseil, Correction, Corrections, Objet, OrigineCommune

COMMUNES_JSON = RACINE / "web" / "static" / "communes.json"

# --- Données : noms bannis, formes usuelles, formes courtes ambiguës -------------------------------------------

# Aucun nom de commune n'est banni, sauf l'ancienne commune Mur (« Mur de soutènement », « Mur Blanc »).
BANNIS = frozenset({"Mur"})
# Formes courtes usuelles, sans ambiguïté, tenues à la main : forme → nom actuel dans `communes.json`.
FORMES_USUELLES = {
    "Cheseaux": "Cheseaux-sur-Lausanne",
    "Saint-Légier": "Blonay - Saint-Légier",
}
# Formes courtes qu'aucune règle ne peut départager : jamais reconnues, même si `communes.json` venait à les donner.
FORMES_AMBIGUES = frozenset({"Chavannes", "Belmont", "Corcelles", "Romanel", "Mont"})

# --- Données : contextes exclus, communs à toutes les sources ----------------------------------------------------
# Les motifs portent sur le texte lu (`lire`) : sans accents, « St- » développé. Une correction qui revient dans
# `corrections.json` devient un contexte exclu ici.

_MOIS = "janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|novembre|decembre"
_DE = r"\s+(?:(?:de|du|des)\s+|d')?(?:la\s+|l')?"  # « district de », « route d' », « avenue de la »…

# Formules retirées avant l'appariement : elles nomment une commune sans parler d'elle.
FORMULES = [
    r"(?i:en seance du Conseil d'Etat),?\s+(?i:a)\s+[A-Z][\w'-]*",  # signature des réponses du Conseil d'État
    r"(?i:place du Chateau)\s+6,?\s+(?:a\s+|1014\s+)?Lausanne",  # lieu de séance des commissions
    # Raisons sociales : LEB, MBC, TRAVYS.
    r"Lausanne\s*-\s*Echallens\s*-\s*Bercher",
    r"Morges[\s-]+Biere[\s-]+Cossonay",
    r"Vallee de Joux[\s,-]+Yverdon-les-Bains[\s,-]+(?:et\s+)?Sainte-Croix",
    # Lieux qui portent le nom d'une commune sans en être.
    r"Gymnase de Provence",  # à Lausanne
    r"La Chaux(?=\s+de\s+Sainte-Croix)",  # lieu-dit de Sainte-Croix, pas La Chaux (Cossonay)
]

# Motifs juste avant le nom. Ceux de `CHAINES` excluent aussi les noms qu'on leur accole par une virgule, un tiret
# ou « et » (« districts de Nyon et Morges », « RC 601 Lausanne - Berne »).
CHAINES = [
    rf"(?i:\bdistricts?){_DE}$",
    rf"(?i:\bregions?){_DE}$",
    rf"(?i:\bagglomerations?){_DE}$",
    r"\b(?:Ouest|Est|Nord|Sud)\s+$",  # « Districts Ouest Lausanne »
    r"\bRC\s*\d+[a-z]?\s+$",  # route cantonale
]
AVANT = [
    rf"(?i:\b(?:plaine|riviere|vallee|gorges|bassin)){_DE}$",
    (
        r"(?i:\b(?:rue|ruelle|avenue|av\.|route|rte|chemin|ch\.|place|boulevard|bd|quai|allee|impasse|passage"
        rf"|sentier|promenade|esplanade|rampe)){_DE}$"
    ),
    r"(?i:\b(?:universite|ecole polytechnique federale|haute ecole[^.;:()]{0,60}?))\s+(?:de\s+|d')$",
    r"\b[1-9]\d{3}\s+$",  # adresse postale (« 1014 Lausanne »)
    r"(?i:\barticle)\s+$",  # « Article Premier »
    r"(?i:\b(?:le|la|un|une)\s+(?:nouvel|nouveau|nouvelle|petit|petite|futur|future|grand|grande))\s+$",
]
# Un nom de commune sans article, précédé d'un article : « l'Orbe » (la rivière), « du Fey » (l'avenue, à Moudon).
AVANT_SANS_ARTICLE = r"(?:\b(?i:le|la|les|du|des|au|aux)\s+|\b(?i:l)')$"
# Motifs juste après le nom.
APRES = [
    r"^\s*[(/]?\s*(?:FR|NE|VS|GE|BE|JU|SO)\b",  # homonyme d'un autre canton (« Ecublens (FR) »)
    rf"^,?\s+(?:le\s+)?\d{{1,2}}(?:er)?\s+(?i:{_MOIS})\s+\d{{4}}",  # lieu et date de signature
    r"^\s+\d{1,3}[a-z]?\s*(?:,|\ba\b)",  # adresse (« Provence 4 à Lausanne »)
]
# Noms qui sont aussi des mots courants : exclus dans ce contexte après eux.
MOTS_COURANTS = {
    "Premier": r"^\s+(?!(?:et|ou|a|au|aux|en|est|sont)\b)[a-z]",  # « Premier débat », « Premier semestre »
}


def plier(texte: str) -> str:
    """`texte` sans accents ni ligatures, apostrophes, tirets et espaces normalisés, lettre pour lettre (sauf
    « œ », qui en donne deux)."""
    sortie = []
    for ch in texte:
        if ch in "’‘ʼ`´":
            sortie.append("'")
        elif ch in "–—‑‐−":
            sortie.append("-")
        elif ch in "   ":
            sortie.append(" ")
        elif ch in "œŒ":
            sortie.append("oe" if ch == "œ" else "Oe")
        else:
            base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
            sortie.append(base[:1] if base else ch)
    return "".join(sortie)


# Un nom à article se lit avec son article ou sa contraction, selon le genre (« du Lieu », mais pas « aux Chaux »
# pour La Chaux) ; sans article seulement si le reste a un trait d'union (« Mont-sur-Lausanne »).
ARTICLES = {
    "Le ": r"(?:[Ll]e|[Dd]u|[Aa]u)\s+",
    "La ": r"[Ll]a\s+",
    "Les ": r"(?:[Ll]es|[Dd]es|[Aa]ux)\s+",
    "L'": r"[Ll]'\s*",
}
SAINT = re.compile(r"(?<!\w)St(e?)(?:\.\s*-?|-|\s)(?=[A-Z])")
# Un nom coupé en fin de ligne par l'extraction d'un PDF (« Montagny-près- Yverdon ») : le trait d'union suit une
# lettre et précède un nom propre, contrairement au tiret qui sépare deux noms (« Lausanne - Morges »).
MOT_COUPE = re.compile(r"(?<=\w)-\s+(?=[A-Z])")
_FORMULES = re.compile("|".join(f"(?:{f})" for f in FORMULES))
_CHAINES = [re.compile(c) for c in CHAINES]
_AVANT = [re.compile(c) for c in AVANT]
_AVANT_SANS_ARTICLE = re.compile(AVANT_SANS_ARTICLE)
_APRES = [re.compile(c) for c in APRES]
_MOTS_COURANTS = {plier(nom): re.compile(c) for nom, c in MOTS_COURANTS.items()}
_SEPARATEUR = re.compile(r"\s*(?:,|;|/|-|\bet\b)\s*")
_CONTEXTE = 80  # caractères lus de part et d'autre d'un nom


@dataclass(frozen=True)
class _Nom:
    forme: str  # le nom plié, sans le suffixe « (VD) »
    ofs: int
    article: bool
    indice: str  # un mot du nom, cherché tel quel avant le motif (bien plus rapide)
    motif: re.Pattern


def _nom(forme: str, ofs: int) -> _Nom:
    article = next((a for a in ARTICLES if forme.startswith(a)), None)
    reste = forme[len(article) :] if article else forme
    coeur = re.escape(reste).replace(r"\ \-\ ", r"\s*-\s*").replace(r"\ ", r"\s+")
    if article:
        coeur = f"(?:{ARTICLES[article]}){'?' if '-' in reste else ''}{coeur}"
    motif = re.compile(r"(?<![\w-])" + coeur + r"(?![\w-])")
    return _Nom(forme, ofs, article is not None, max(reste.split(" "), key=len), motif)


def _forme(nom: str) -> str:
    return plier(re.sub(r"\s*\([^)]*\)$", "", nom))


class Repertoire:
    """Les noms que le rattachement reconnaît, tirés de `communes.json` : communes actuelles, anciennes communes et
    anciens noms (qui mènent à la commune actuelle), plus les formes usuelles ; sans les noms bannis, les formes
    courtes ambiguës, ni un nom que deux communes partagent."""

    def __init__(self, communes: Iterable[dict]) -> None:
        noms: dict[str, set[int]] = {}
        actuelles: dict[str, int] = {}
        for commune in communes:
            actuelles[commune["nom"]] = commune["bfs"]
            for nom in [commune["nom"], *(a["nom"] for a in commune.get("anciens", []))]:
                noms.setdefault(_forme(nom), set()).add(commune["bfs"])
        for forme, nom in FORMES_USUELLES.items():
            if nom in actuelles:
                noms.setdefault(plier(forme), set()).add(actuelles[nom])
        ecartes = {plier(n) for n in BANNIS | FORMES_AMBIGUES}
        self._noms = [_nom(f, ofs) for f, (ofs, *autres) in noms.items() if not autres and f not in ecartes]

    @classmethod
    def lire(cls, chemin: Path = COMMUNES_JSON) -> Repertoire:
        return cls(json.loads(chemin.read_text(encoding="utf-8")))

    def mentions(self, texte: str) -> list[tuple[int, int, _Nom]]:
        """Les noms trouvés dans `texte` (lu par `lire`) : (début, fin, nom), sans chevauchement, le plus long
        l'emportant."""
        trouvees = []
        for nom in self._noms:
            if nom.indice in texte:
                trouvees += [(m.start(), m.end(), nom) for m in nom.motif.finditer(texte)]
        trouvees.sort(key=lambda t: (t[0], t[0] - t[1]))
        gardees, fin = [], -1
        for debut, f, nom in trouvees:
            if debut >= fin:
                gardees.append((debut, f, nom))
                fin = f
        return gardees


@cache
def _repertoire_par_defaut() -> Repertoire:
    return Repertoire.lire()


def lire(texte: str) -> str:
    """Le texte tel que le rattachement le lit : plié, « St- » et « Ste- » lus « Saint- » et « Sainte- », et les
    formules retirées."""
    texte = MOT_COUPE.sub("-", plier(texte))
    texte = SAINT.sub(lambda m: "Sainte-" if m[1] else "Saint-", texte)
    return _FORMULES.sub(" ¦ ", texte)


def _exclu(nom: _Nom, avant: str, apres: str) -> bool:
    if any(c.search(avant) for c in _AVANT) or any(c.search(apres) for c in _APRES):
        return True
    if not nom.article and _AVANT_SANS_ARTICLE.search(avant):
        return True
    courant = _MOTS_COURANTS.get(nom.forme)
    return courant is not None and courant.search(apres) is not None


def rattacher(texte: str, origine: OrigineCommune, repertoire: Repertoire | None = None) -> list[CommuneRattachee]:
    """Les communes que `texte` nomme, chacune une fois, avec `origine`, hors contextes exclus. Dans l'ordre
    d'apparition pour un titre ; de la plus à la moins mentionnée pour un document (à égalité, dans l'ordre
    d'apparition)."""
    repertoire = repertoire or _repertoire_par_defaut()
    texte = lire(texte)
    comptes: dict[int, int] = {}
    chaine = None  # fin du dernier nom exclu par un motif de `CHAINES`
    for debut, fin, nom in repertoire.mentions(texte):
        avant, apres = texte[max(0, debut - _CONTEXTE) : debut], texte[fin : fin + _CONTEXTE]
        if chaine is not None and _SEPARATEUR.fullmatch(texte[chaine:debut]):
            chaine = fin
            continue
        chaine = fin if any(c.search(avant) for c in _CHAINES) else None
        if chaine is None and not _exclu(nom, avant, apres):
            comptes[nom.ofs] = comptes.get(nom.ofs, 0) + 1
    ordre = list(comptes)
    if origine == "document":
        ordre.sort(key=lambda ofs: -comptes[ofs])
    return [CommuneRattachee(ofs=ofs, origine=origine) for ofs in ordre]


# --- Objets du Grand Conseil -----------------------------------------------------------------------------------

# Au-delà, les documents énumèrent (communes d'un district, tableau de routes) : seul le titre compte.
MAX_COMMUNES_DOCUMENTS = 10
FICHIER_CORRECTIONS = "corrections.json"
_ENTRE_DOCUMENTS = "\n¦\n"  # ni un nom, ni une virgule : rien ne se lit à cheval sur deux documents


def porte_sur_le_canton(conseil: Conseil) -> bool:
    """Le Grand Conseil (`VD`) porte sur le canton ; un conseil communal (son n° OFS) sur sa seule commune."""
    return conseil.commune is None


def rattacher_objet(
    titre: str, documents: Iterable[str], repertoire: Repertoire | None = None
) -> list[CommuneRattachee]:
    """Les communes d'un Objet : celles de son titre (déjà masqué), dans leur ordre, puis celles du texte de ses
    documents, de la plus à la moins citée ; seulement le titre si les documents en citent plus de 10."""
    du_titre = rattacher(titre, "titre", repertoire)
    des_documents = rattacher(_ENTRE_DOCUMENTS.join(documents), "document", repertoire)
    if len(des_documents) > MAX_COMMUNES_DOCUMENTS:
        des_documents = []
    deja = {c.ofs for c in du_titre}
    return du_titre + [c for c in des_documents if c.ofs not in deja]


def corriger(communes: list[CommuneRattachee], correction: Correction | None) -> list[CommuneRattachee]:
    """`communes` avec `correction` : les communes retirées enlevées, les ajoutées en fin de liste (origine
    `correction`). Une correction déjà appliquée est d'abord défaite, pour qu'elle s'applique à nouveau sans
    s'empiler ; une commune qu'elle retirait ne revient qu'au prochain rattrapage."""
    regle = [c for c in communes if c.origine != "correction"]
    if correction is None:
        return regle
    gardees = [c for c in regle if c.ofs not in correction.retirer]
    presentes = {c.ofs for c in gardees}
    ajoutees = [o for o in dict.fromkeys(correction.ajouter) if o not in presentes]
    return gardees + [CommuneRattachee(ofs=ofs, origine="correction") for ofs in ajoutees]


def corriger_archive(objets: Mapping[str, Objet], corrections: Mapping[str, Correction]) -> dict[str, Objet]:
    """Les Objets déjà archivés dont `corrections` change les communes, corrigés : une correction écrite ou retirée
    vaut dès l'import suivant, sans attendre que l'Objet change chez la source."""
    corriges = {}
    for cle, objet in objets.items():
        communes = corriger(objet.communes, corrections.get(cle))
        if communes != objet.communes:
            corriges[cle] = objet.model_copy(update={"communes": communes})
    return corriges


def lire_corrections(depot: Path) -> dict[str, Correction]:
    """`corrections.json` du dépôt de données, par clé d'Objet (deux corrections d'un même Objet se cumulent) ; vide
    si le fichier n'existe pas. Un fichier invalide lève `pydantic.ValidationError` : mieux vaut un import en échec
    qu'une correction perdue en silence."""
    try:
        texte = (depot / FICHIER_CORRECTIONS).read_bytes()
    except FileNotFoundError:
        return {}
    par_objet: dict[str, Correction] = {}
    for c in Corrections.model_validate_json(texte).root:
        avant = par_objet.get(c.objet)
        if avant is not None:
            c = c.model_copy(
                update={"retirer": avant.retirer + c.retirer, "ajouter": avant.ajouter + c.ajouter,
                        "note": f"{avant.note} ; {c.note}"}
            )
        par_objet[c.objet] = c
    return par_objet
