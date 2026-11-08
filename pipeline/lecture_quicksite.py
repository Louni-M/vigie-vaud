"""Module de lecture de la plateforme Quicksite d'eAdmin Solutions (ADR 0010) : une seule opération publique pour
l'import, `lire`, qui lit le conseil d'une commune Quicksite par le robot communal et rend ses `Bruts`, à la forme
d'OpenParlData ; et, pour le script de préparation des sources seulement, `mesurer` et `requetes`
(`mesure_sites.py`).

Variante **ancienne génération** (thème « Powered by quicksite v 5.5.3 », Aigle) : la page des documents
(`site.seances`) est une bibliothèque rendue côté serveur, 20 documents par page (`?Page_0=<n>`), du plus récent au
plus ancien par mise en ligne. Chaque document (`div.tplDocumentSummaryItem`) donne son titre, son type
(`#doctype` : Préavis, Annexes aux préavis, Ordre du jour, PV du conseil, Décision…), la référence de son Objet s'il
en a une (`strBusinessID`, « 2026-14: »), une description, son lien stable (`Home.asp?N=<id>&DocAction=Download`) et
sa mise en ligne (« 04.11.2026 07:22:22 »). Les Séances n'ont pas de liste : un ordre du jour, un procès-verbal ou
une décision donne la sienne par la date de son titre ou de sa description (« Ordre du jour du Conseil Communal du
29 octobre 2026 », « Séance du Conseil du 1er octobre 2026 ») ; un tel document sans date est sauté. Un préavis
est un document de type « Préavis » ; il est daté de sa mise en ligne, et ses documents sont ceux qui citent son
numéro (annexe, extrait de décision, rapport de commission).

Variante **`coreapi`** (nouvelle génération, thème eAdmin de 2023) : la page des documents du conseil
(`site.seances`, celle que la sonde lit) est vide ; le navigateur la remplit par la recherche `coreapi`, dont les
paramètres sont déclarés (`site.coreapi`). Le cron demande ce fragment HTML page par page (`&page=<n>`), du plus
récent au plus ancien, sans ouvrir la page des documents. Chaque document (`div.qs-edit`) donne son lien stable
`/n<id>`, son titre, son type s'il en a un (Décisions, Préavis, Procès-verbaux…), sa Séance et sa date de
publication. Deux vues :

- `documentconseildates` (Founex) : les documents sont groupés par Séance (« Séance du 28 septembre 2026 ») ; un
  préavis cite son Objet (« Objet n° 005: … »), dont le texte est le titre du préavis ;
- `documentconseil` (Ropraz) : chaque document porte sa Séance, dont des fausses « Séance du 1 janvier 2025 » qui
  rassemblent les préavis d'une année ; elles sont importées telles quelles (spec, « Les plateformes »).

**Séances** : une par Séance citée, à la date de son libellé, sans lien propre (le site n'a pas de page de Séance)
ni ordre du jour structuré ; ses documents sont tous ceux de la Séance, préavis compris. **Préavis** (niveau
« séances et préavis ») : un document dont le titre commence par « Préavis <numéro> » ; le numéro brut est pris là
seulement (`005_2026-2031`, `06/2025`), le type est « Préavis », la date celle de sa Séance ; ses documents sont le
préavis et ceux de la même Séance qui citent le même Objet (« 072: … »). Un préavis sans numéro n'est pas importé ; de deux
préavis de même numéro, le premier du site (le plus récent) l'emporte ; l'un et l'autre sont notés dans le journal.

**Dates** : celle de la Séance que le site donne, même fictive ; un document est daté de sa publication quand le
site l'affiche. Les dates des noms de fichiers et de `Content-Disposition` ne servent pas : chaque document de ces
vues a sa Séance (choix à relire, #175).

**Fenêtre** : au passage ordinaire, la lecture s'arrête à la première page de résultats dont toutes les Séances sont
plus vieilles que la fenêtre, et seules les Séances de la fenêtre sont importées ; le rattrapage lit toutes les
pages. Un document illisible (sans lien ou sans Séance datée) est sauté et noté dans le journal ; un fragment sans
liste de documents, ou dont aucun document ne se lit, lève `ValueError`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode, urljoin, urlsplit

from bruts import Bruts
from mesure_sites import Mesure, PagesLues, RobotSansReseau, sans_journal
from pages_html import Noeud, arbre, espaces
from robot_communal import PageNonLue, Robot
from schema import Plateforme, Site, Source, niveau_de

VARIANTES = ("ancienne", "coreapi")
TYPE_PREAVIS = "Préavis"  # le type d'un préavis lu dans une liste de documents
PAGES_MAX = 200  # pages de résultats lues au plus pour une commune, même au rattrapage


def lire(robot: Robot, source: Source, depuis: date | None) -> Bruts:
    """Le conseil de `source`, une commune Quicksite, lu sur son site : les Séances datées de `depuis` ou après
    (toutes sans `depuis`), et, si son niveau en donne, ses préavis."""
    site, conseil = source.site, source.conseil
    if site is None or conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    if site.variante not in VARIANTES:
        raise ValueError(f"{source.id} : variante Quicksite {site.variante} pas encore lue")
    niveau = niveau_de(conseil.donne)
    avec_preavis = bool(niveau and niveau.objets)
    if site.variante == "ancienne":
        seances, objets = _bibliotheque(source.nom, _documents_bibliotheque(robot, source, depuis), depuis, avec_preavis)
    else:
        documents = _documents_coreapi(robot, source, depuis)
        seances, objets = _seances_et_preavis(source.nom, documents, depuis, avec_preavis)
    return Bruts(conseil, objets=objets, seances=seances, membres=[])


def _journal(nom: str, message: str) -> None:
    """Note dans le journal du passage un élément sauté du conseil `nom` (le nom de sa source)."""
    print(f"{nom} : élément sauté, {message}", file=sys.stderr)


# --- Bibliothèque (ancienne génération) ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _Piece:
    """Un document de la bibliothèque de l'ancienne génération."""

    lien: str  # lien stable `Home.asp?N=<id>&DocAction=Download`, absolu
    titre: str
    type: str | None
    reference: str | None  # la référence de son Objet (`strBusinessID`, « 2026-14 »)
    description: str
    publie: date | None  # sa mise en ligne


TYPES_DE_SEANCE = ("Ordre du jour", "PV du conseil", "Décision")
_TITRES_DE_SEANCE = re.compile(r"^(ordre du jour|proc[èe]s[- ]verbal|extrait de d[ée]cision)", re.I)
_CITE_UN_PREAVIS = re.compile(r"pr[ée]avis\s+(?:n[°o]\.?\s*)?(\d[\w/-]*\d)", re.I)


def url_de_page(site: Site, page: int) -> str:
    """La page `page` de la bibliothèque des documents (la première est `site.seances` elle-même)."""
    if site.seances is None:
        raise ValueError("variante ancienne sans page `seances`")
    if page == 1:
        return site.seances
    return f"{site.seances}{'&' if '?' in site.seances else '?'}Page_0={page}"


def _documents_bibliotheque(robot: Robot, source: Source, depuis: date | None) -> list[_Piece]:
    """Les documents de la bibliothèque, dans l'ordre du site, page après page : jusqu'à une page vide ou qui ne
    donne rien de nouveau, et, au passage ordinaire, jusqu'à la première page mise en ligne avant la fenêtre."""
    site = source.site
    assert site is not None
    pieces: list[_Piece] = []
    vus: set[str] = set()
    for page in range(1, PAGES_MAX + 1):
        reponse = robot.lire(url_de_page(site, page), "import")
        lues = _page_de_bibliotheque(source.nom, reponse.texte, reponse.url)
        nouvelles = [p for p in lues if p.lien not in vus]
        if not nouvelles:
            break
        vus.update(p.lien for p in nouvelles)
        pieces += nouvelles
        if depuis is not None and all(p.publie is not None and p.publie < depuis for p in nouvelles):
            break
    return pieces


def _page_de_bibliotheque(nom: str, texte: str, url: str) -> list[_Piece]:
    """Les documents d'une page de la bibliothèque. Lève `ValueError` pour une page sans bibliothèque, ou dont
    aucun document ne se lit."""
    racine = arbre(texte)
    liste = next((n for n in racine.elements() if "tplListDocumentSummary" in _classes(n)), None)
    if liste is None:
        raise ValueError(f"{url} : aucune bibliothèque de documents (tplListDocumentSummary)")
    pieces: list[_Piece] = []
    illisibles = 0
    for noeud in (n for n in liste.elements() if "tplDocumentSummaryItem" in _classes(n)):
        piece = _piece(noeud, url)
        if isinstance(piece, str):
            illisibles += 1
            _journal(nom, f"document illisible ({piece})")
        else:
            pieces.append(piece)
    if illisibles and not pieces:
        raise ValueError(f"{url} : aucun document lisible dans la bibliothèque")
    return pieces


def _piece(noeud: Noeud, url: str) -> _Piece | str:
    def texte_de(condition) -> str:
        return next((espaces(n.texte()) for n in noeud.elements() if condition(n)), "")

    titre = texte_de(lambda n: "strNodeName" in _classes(n))
    lien = next(
        (a.attr("href") or "" for a in noeud.elements() if a.tag == "a" and "DocAction=Download" in (a.attr("href") or "")),
        None,
    )
    if not lien:
        return f"sans lien vers le document : {titre or url}"
    reference = texte_de(lambda n: "strBusinessID" in _classes(n)).rstrip(": ")
    return _Piece(
        lien=urljoin(url, lien),
        titre=titre or "Document",
        type=texte_de(lambda n: n.attr("id") == "doctype") or None,
        reference=reference or None,
        description=texte_de(lambda n: "strDescription" in _classes(n)),
        publie=date_ecrite(texte_de(lambda n: "dtmDocLastUpdate" in _classes(n))),
    )


def _bibliotheque(
    nom: str, pieces: list[_Piece], depuis: date | None, avec_preavis: bool
) -> tuple[list[dict], list[dict]]:
    """Les Séances, tirées des ordres du jour, procès-verbaux et décisions datés, et les préavis de la bibliothèque,
    dans l'ordre du site, ceux de la fenêtre seulement."""
    par_seance: dict[date, list[_Piece]] = {}
    for p in pieces:
        if p.type not in TYPES_DE_SEANCE and not (p.type is None and _TITRES_DE_SEANCE.match(p.titre)):
            continue
        jour = date_ecrite(p.titre) or date_ecrite(p.description)
        if jour is None:
            _journal(nom, f"document de Séance sans date : {p.titre}")
            continue
        if depuis is None or jour >= depuis:
            par_seance.setdefault(jour, []).append(p)
    seances = [
        {
            "id": None,
            "name": {"fr": f"Séance du {jour_en_lettres(jour)}"},
            "begin_date": jour.isoformat(),
            "url_external": None,
            "agendas": {"data": []},
            "docs": {"data": [_doc_de_piece(p) for p in docs]},
        }
        for jour, docs in par_seance.items()
    ]
    if not avec_preavis:
        return seances, []
    preavis: list[dict] = []
    for p in pieces:
        if p.type != TYPE_PREAVIS or (depuis is not None and p.publie is not None and p.publie < depuis):
            continue
        numero = _numero(p.titre)
        if numero is None:
            _journal(nom, f"Objet sans numéro, non importé : {p.titre}")
            continue
        if any(o["number"] == numero for o in preavis):
            _journal(nom, f"Objet {numero} en double, le premier du site gardé : {p.titre}")
            continue
        lies = [p] + [x for x in pieces if x is not p and x.type != TYPE_PREAVIS and numero in _cites(x)]
        suite = p.titre[p.titre.index(numero) + len(numero) :].strip(" -–—:")
        preavis.append(
            {
                "id": None,
                "number": numero,
                "title": {"fr": suite or p.titre},
                "type_name": {"fr": TYPE_PREAVIS},
                "state_name": None,
                "begin_date": p.publie.isoformat() if p.publie else None,
                "url_external": None,
                "contributors": {"data": []},
                "docs": {"data": [_doc_de_piece(x) for x in lies]},
            }
        )
    return seances, preavis


def _cites(p: _Piece) -> set[str]:
    """Les numéros d'Objet qu'un document cite : sa référence, et les préavis que son titre nomme."""
    cites = set(_CITE_UN_PREAVIS.findall(p.titre))
    return cites | {p.reference} if p.reference else cites


def _doc_de_piece(p: _Piece) -> dict:
    return {"name": p.titre, "url": p.lien, "date": p.publie.isoformat() if p.publie else None, "category": p.type}


def jour_en_lettres(jour: date) -> str:
    """« 1er octobre 2026 », « 29 octobre 2026 »."""
    return f"{'1er' if jour.day == 1 else jour.day} {_MOIS[jour.month - 1]} {jour.year}"


# --- Recherche `coreapi` ------------------------------------------------------------------------------------------


def url_de_recherche(site: Site, page: int = 1) -> str:
    """Le fragment de la recherche `coreapi` que le navigateur demande pour remplir la page `site.seances`, avec les
    paramètres déclarés, à la page de résultats `page`."""
    c = site.coreapi
    if c is None or site.seances is None:
        raise ValueError("variante coreapi sans bloc `coreapi` ni page `seances`")
    origine = urlsplit(site.seances)
    parametres = {
        "q": "",
        "elasticsearchProject": "",
        "elasticsearchNode": c.noeud,
        "elasticsearchPagesize": c.taille,
        "elasticsearchNodetype": "",
        "elasticsearchParentnode": c.noeud,
        "elasticsearchSort": c.tri,
        "elasticsearchView": c.vue,
        "elasticsearchQuery": "input.query-full",
        "elasticsearchResult": "#search-result-list-full",
        "elasticsearchFiltertags": "",
        "elasticsearchInitresult": "true",
        "query": "",
        "date_from": "",
        "date_to": "",
    }
    if page > 1:
        parametres["page"] = page
    chemin = f"/coreapi/elasticsearch/projects/{c.projet}/{c.vue}/search"
    return f"{origine.scheme}://{origine.netloc}{chemin}?{urlencode(parametres)}"


@dataclass(frozen=True)
class _Document:
    lien: str  # lien stable `/n<id>`, absolu
    titre: str
    type: str | None  # le type du site (« Préavis », « Décisions »), s'il en donne un
    seance: str  # le libellé de sa Séance, tel quel (« Séance du 1 janvier 2025 »)
    jour: date  # le jour de sa Séance
    publie: date | None
    objet: str | None  # l'Objet que le document cite (« 005: Demande de crédit… »)


_TOTAL = re.compile(r"(\d+)\s*à\s*(\d+)\s*sur\s*(\d+)\s*éléments?")


def _documents_coreapi(robot: Robot, source: Source, depuis: date | None) -> list[_Document]:
    """Les documents de la recherche `coreapi`, dans l'ordre du site, page de résultats après page de résultats."""
    site = source.site
    assert site is not None
    documents: list[_Document] = []
    for page in range(1, PAGES_MAX + 1):
        reponse = robot.lire(url_de_recherche(site, page), "import")
        lus, fin, total = _page_de_resultats(source.nom, reponse.texte, reponse.url)
        documents += lus
        if not lus or fin >= total:
            break
        if depuis is not None and all(d.jour < depuis for d in lus):
            break
    return documents


def _page_de_resultats(nom: str, texte: str, url: str) -> tuple[list[_Document], int, int]:
    """Les documents d'une page de résultats, et la position de sa fin dans le total (« 1 à 60 sur 399 éléments
    trouvés »). Lève `ValueError` pour un fragment sans liste de documents, ou dont aucun document ne se lit."""
    racine = arbre(texte)
    liste = next((n for n in racine.elements() if "tplDocumentConseil" in _classes(n)), None)
    if liste is None:
        raise ValueError(f"{url} : aucune liste de documents (tplDocumentConseil)")
    position = _TOTAL.search(espaces(liste.texte()))
    debut, fin, total = (int(x) for x in position.groups()) if position else (0, 0, 0)
    documents: list[_Document] = []
    illisibles = 0
    groupes = [n for n in liste.elements() if "accordion-item" in _classes(n)]
    for groupe, seance in [(g, _libelle_du_groupe(g)) for g in groupes] or [(liste, None)]:
        for noeud in groupe.elements():
            if "qs-edit" not in _classes(noeud) or noeud.attr("data-qsedit-editnode") is None:
                continue
            document = _document(noeud, seance, url)
            if isinstance(document, str):
                illisibles += 1
                _journal(nom, f"document illisible ({document})")
            else:
                documents.append(document)
    if illisibles and not documents:
        raise ValueError(f"{url} : aucun document lisible dans la page {debut}–{fin}")
    return documents, fin, total


def _libelle_du_groupe(groupe: Noeud) -> str | None:
    """Le libellé de la Séance d'un groupe de documents : l'en-tête du groupe (son bouton), « Séance du … »."""
    entete = next((n for n in groupe.elements() if "accordion-header" in _classes(n) or n.tag == "button"), None)
    return espaces(entete.texte()) if entete else None


def _classes(noeud: Noeud) -> list[str]:
    return (noeud.attr("class") or "").split()


_LIEN_NOEUD = re.compile(r"/n\d+$")


def _document(noeud: Noeud, seance: str | None, url: str) -> _Document | str:
    """Un document de la recherche, ou la raison pour laquelle il ne se lit pas."""
    liens = [a for a in noeud.elements() if a.tag == "a" and _LIEN_NOEUD.search(a.attr("href") or "")]
    titre = next((espaces(n.texte()) for n in noeud.elements() if n.tag in ("h5", "h6")), "")
    if not liens:
        return f"sans lien vers le document : {titre or url}"
    filtres = {
        (a.attr("data-filter-type") or ""): a
        for a in noeud.elements()
        if a.tag == "a" and a.attr("data-filter-type")
    }
    type_ = espaces(filtres["t"].texte()) if "t" in filtres else ""
    if seance is None and "sortdate" in filtres:
        seance = espaces(filtres["sortdate"].texte())
    jour = date_ecrite(seance or "")
    if seance is None or jour is None:
        return f"sans Séance datée : {titre}"
    publie = re.search(r"Publié le\s+(.+)", espaces(noeud.texte()))
    objet = filtres["ext_id"].attr("data-filter-value") if "ext_id" in filtres else None
    return _Document(
        lien=liens[0].attr("href") or "",
        titre=titre or (liens[0].attr("href") or "").rsplit("/", 1)[-1],
        type=type_ or None,
        seance=seance,
        jour=jour,
        publie=date_ecrite(publie[1]) if publie else None,
        objet=espaces(objet) if objet else None,
    )


# --- Séances et préavis -------------------------------------------------------------------------------------------

# « Préavis 005_2026-2031 », « Préavis n° 06/2025 » : le numéro est le premier mot qui suit « Préavis », quand il
# porte un chiffre et n'est pas une date.
_NUMERO_PREAVIS = re.compile(r"^préavis(?:\s+municipal)?\s+(?:n[°o]\.?\s*)?(?P<numero>\S*\d\S*)", re.I)
_DATE_CHIFFRES = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
_DATE_LETTRES = re.compile(rf"\b(\d{{1,2}})(?:er)?\s+({'|'.join(_MOIS)})\s+(\d{{4}})\b", re.I)


def date_ecrite(texte: str) -> date | None:
    """La première date d'un texte, en chiffres (« 09.11.2026 ») ou en lettres (« 1er octobre 2026 »)."""
    chiffres, lettres = _DATE_CHIFFRES.search(texte), _DATE_LETTRES.search(texte)
    try:
        if chiffres and (not lettres or chiffres.start() < lettres.start()):
            return date(int(chiffres[3]), int(chiffres[2]), int(chiffres[1]))
        if lettres:
            return date(int(lettres[3]), _MOIS.index(lettres[2].lower()) + 1, int(lettres[1]))
    except ValueError:
        return None
    return None


def _seances_et_preavis(
    nom: str, documents: list[_Document], depuis: date | None, avec_preavis: bool
) -> tuple[list[dict], list[dict]]:
    """Les Séances (*meetings*) et les préavis (*affairs*) des documents, dans l'ordre du site, ceux de la fenêtre
    seulement."""
    dans_la_fenetre = [d for d in documents if depuis is None or d.jour >= depuis]
    par_seance: dict[tuple[date, str], list[_Document]] = {}
    for d in dans_la_fenetre:
        par_seance.setdefault((d.jour, d.seance), []).append(d)
    seances = [
        {
            "id": None,
            "name": {"fr": libelle},
            "begin_date": jour.isoformat(),
            "url_external": None,
            "agendas": {"data": []},
            "docs": {"data": [_doc(d) for d in docs]},
        }
        for (jour, libelle), docs in par_seance.items()
    ]
    if not avec_preavis:
        return seances, []
    preavis: list[dict] = []
    for d in dans_la_fenetre:
        if not d.titre.lower().startswith("préavis"):
            continue
        numero = _numero(d.titre)
        if numero is None:
            _journal(nom, f"Objet sans numéro, non importé : {d.titre}")
            continue
        if any(p["number"] == numero for p in preavis):
            _journal(nom, f"Objet {numero} en double, le premier du site gardé : {d.titre}")
            continue
        lies = [d] + [
            x for x in par_seance[(d.jour, d.seance)] if x is not d and _ref(d) is not None and _ref(x) == _ref(d)
        ]
        preavis.append(
            {
                "id": None,
                "number": numero,
                "title": {"fr": _titre_du_preavis(d, numero)},
                "type_name": {"fr": TYPE_PREAVIS},
                "state_name": None,
                "begin_date": d.jour.isoformat(),
                "url_external": None,
                "contributors": {"data": []},
                "docs": {"data": [_doc(x) for x in lies]},
            }
        )
    return seances, preavis


def _ref(d: _Document) -> str | None:
    """La référence de l'Objet qu'un document cite, sans son texte (« 072: Plans Port de Founex » donne « 072 »)."""
    return d.objet.split(":", 1)[0].strip() or None if d.objet else None


def _numero(titre: str) -> str | None:
    m = _NUMERO_PREAVIS.match(titre)
    if m is None:
        return None
    numero = m["numero"].rstrip(".,;:")
    return None if _DATE_CHIFFRES.fullmatch(numero) else numero


def _titre_du_preavis(d: _Document, numero: str) -> str:
    """Le texte de l'Objet que le préavis cite (« 005: Demande de crédit… » donne « Demande de crédit… »), sinon la
    suite de son titre (« Préavis 04/2024 - Budget 2025 » donne « Budget 2025 »), sinon son titre."""
    if d.objet:
        texte = re.sub(r"^\s*\S+\s*:\s*", "", d.objet)
        if texte:
            return texte
    suite = d.titre[d.titre.index(numero) + len(numero) :].strip(" -–—:")
    return suite or d.titre


def _doc(d: _Document) -> dict:
    return {"name": d.titre, "url": d.lien, "date": d.publie.isoformat() if d.publie else None, "category": d.type}


# --- Mesure du site, pour le script de préparation des sources ------------------------------------------------------


def mesurer(pages: PagesLues, page_du_conseil: str, declare: Site, plateforme: Plateforme) -> Mesure:
    """Le site d'une commune mesuré pour le script de préparation des sources (#179)."""
    raise NotImplementedError("mesure des sites Quicksite : #179")


def requetes(pages: PagesLues, source: Source, depuis: date | None) -> int | None:
    """Les requêtes que coûterait la lecture de `source` (`lire`) au passage ordinaire dont la fenêtre part de
    `depuis`, rejouée sans réseau sur les pages déjà lues ; `None` si la lecture échoue."""
    robot = RobotSansReseau(pages.pages, lambda url: 1)
    try:
        sans_journal(lambda: lire(robot, source, depuis))  # type: ignore[arg-type]
    except (ValueError, PageNonLue):
        return None
    return robot.requetes
