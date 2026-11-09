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
préavis de même numéro, le plus ancien (le plus petit nœud) l'emporte ; l'un et l'autre sont notés dans le journal. Les
documents sont rangés par nœud : la recherche ne range pas toujours de la même façon des documents à égalité de tri.

Variante **`conseil`** (module « Conseil communal » de Quicksite, sur un site à part : Montreux) : la liste des
Séances (`site.seances`, `ordredujour/`) donne l'année en cours en pastilles (jour, mois ; les Séances annoncées
sans page n'ont pas de lien) et les années précédentes en onglets (date, lien) ; chaque Séance a sa page
(`ordredujour/?ID=<id>`, lien stable), dont chaque point (`div.card`) a son texte, cite parfois son Objet
(`documents/recherche/?id=<id>`) et donne ses documents (`download.asp?d=<id>`, nommés par leur fichier). La fiche
de chaque Objet cité est ouverte : numéro brut et type de son titre (« Préavis 29/2026 »), texte, auteur·e
(« Auteur : Municipalité »), documents typés et datés ; pas de statut. Un point relié à son Objet lui laisse ses
documents ; ceux des autres points vont à la Séance. Les conseillers (`site.membres`, « **Nom** Prénom ») sont lus
page après page (`rel="next"`).

Variante **`conseil-externe`** (le module Conseil dont la liste des Séances est sur le site de la Ville : Vevey) :
la page `site.seances` (Drupal) donne chaque Séance (`div.teaser-agenda` : « Séance du Conseil communal du jeudi
1er octobre 2026 - 19h30 ») et le lien de son ordre du jour sur le module (`seances/?ID=<id>`), souvent cassé
(`www.vevey.ch/conseil.vevey.ch/…`) : il est récrit vers `https://<hôte du module>/ConseilCommunal/seances/?ID=<id>`,
à la casse que `robots.txt` autorise. La page d'une Séance (ISO-8859-1) donne ses points numérotés (`h2` : « 9. »,
puis « 9.1 » et son titre) et leurs documents ; tous vont à la Séance (niveau « séances seulement »).

**Dates** : celle de la Séance que le site donne, même fictive ; un document est daté de sa publication quand le
site l'affiche. Les dates des noms de fichiers et de `Content-Disposition` ne servent pas : chaque document de ces
vues a sa Séance (choix à relire, #175).

**Fenêtre** : la recherche `coreapi` est lue en entier, chaque jour, comme toute page de liste (spec, « Fenêtre ») ;
au passage ordinaire, seuls les Séances et préavis de la fenêtre sont importés. La bibliothèque de l'ancienne
génération, triée par mise en ligne, s'arrête à la première page mise en ligne avant la fenêtre ; le rattrapage la
lit en entier. Un document illisible (sans lien ou sans Séance datée) est sauté et noté dans le journal ; un fragment sans
liste de documents, ou dont aucun document ne se lit, lève `ValueError`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode, urljoin, urlsplit

from bruts import Bruts
from mesure_sites import Mesure, PagesLues, liens, sans_journal
from pages_html import Noeud, arbre, espaces
from robot_communal import PageNonLue, Reponse, Robot
from schema import Plateforme, Site, Source, niveau_de

VARIANTES = ("ancienne", "coreapi", "conseil", "conseil-externe")
HOTES_DU_MODULE = {"www.vevey.ch": "conseil.vevey.ch"}  # le module Conseil d'une ville dont la liste est ailleurs
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
    elif site.variante == "conseil":
        seances, objets = _module_conseil(robot, source, depuis, avec_objets=avec_preavis)
        return Bruts(conseil, objets=objets, seances=seances, membres=_conseillers(robot, source))
    elif site.variante == "conseil-externe":
        return Bruts(conseil, objets=[], seances=_module_conseil_externe(robot, source, depuis), membres=[])
    else:
        documents = _documents_coreapi(robot, source, depuis)
        seances, objets = _seances_et_preavis(source.nom, documents, depuis, avec_preavis)
    return Bruts(conseil, objets=objets, seances=seances, membres=[])


def _journal(nom: str, message: str) -> None:
    """Note dans le journal du passage un élément sauté du conseil `nom` (le nom de sa source)."""
    print(f"{nom} : élément sauté, {message}", file=sys.stderr)


def _page_suivante(robot: Robot, source: Source, url: str, page: int) -> Reponse | None:
    """La page `page` d'une liste paginée. La première doit se lire (sinon l'import est en échec) ; une suivante
    qui ne se lit pas finit la liste, notée dans le journal (un réseau bloqué interrompt quand même l'import)."""
    if page == 1:
        return robot.lire(url, "import")
    try:
        return robot.lire(url, "import")
    except PageNonLue as e:
        _journal(source.nom, f"page {page} de la liste non lue ({e}), liste lue jusqu'à la page {page - 1}")
        return None


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
        reponse = _page_suivante(robot, source, url_de_page(site, page), page)
        if reponse is None:
            break
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
    seance: str | None  # le libellé de sa Séance, tel quel (« Séance du 1 janvier 2025 »), s'il en a une
    jour: date | None  # le jour de sa Séance
    publie: date | None
    objet: str | None  # l'Objet que le document cite (« 005: Demande de crédit… »)


_TOTAL = re.compile(r"(\d+)\s*à\s*(\d+)\s*sur\s*(\d+)\s*éléments?")


def _documents_coreapi(robot: Robot, source: Source, depuis: date | None) -> list[_Document]:
    """Les documents de la recherche `coreapi`, dans l'ordre du site, page de résultats après page de résultats,
    toutes, même au passage ordinaire (`depuis` n'y change rien) : la recherche n'est pas triée par mise en ligne,
    et une Séance ou un préavis de la fenêtre peut avoir des documents sur n'importe quelle page. Lire moins
    réécrirait l'élément avec une partie de ses documents."""
    site = source.site
    assert site is not None
    documents: list[_Document] = []
    for page in range(1, PAGES_MAX + 1):
        reponse = _page_suivante(robot, source, url_de_recherche(site, page), page)
        if reponse is None:
            break
        lus, fin, total = _page_de_resultats(source.nom, reponse.texte, reponse.url)
        documents += lus
        if not lus or fin >= total:
            break
    return documents


def _quand(d: _Document) -> date | None:
    """Le jour d'un document : celui de sa Séance, sinon sa publication."""
    return d.jour or d.publie


def _page_de_resultats(nom: str, texte: str, url: str) -> tuple[list[_Document], int, int]:
    """Les documents d'une page de résultats, et la position de sa fin dans le total (« 1 à 60 sur 399 éléments
    trouvés »). Lève `ValueError` pour un fragment sans liste de documents, ou dont aucun document ne se lit."""
    racine = arbre(texte)
    # La liste du thème de 2023 (`tplDocumentConseil`), ou celle d'un thème plus ancien (Rolle, Trélex).
    liste = next(
        (n for n in racine.elements() if "tplDocumentConseil" in _classes(n) or n.attr("id") == "search-standard-result"),
        None,
    )
    if liste is None:
        raise ValueError(f"{url} : aucune liste de documents (tplDocumentConseil, search-standard-result)")
    position = _TOTAL.search(espaces(racine.texte()))
    debut, fin, total = (int(x) for x in position.groups()) if position else (0, 0, 0)
    documents: list[_Document] = []
    illisibles = 0
    groupes = [n for n in liste.elements() if "accordion-item" in _classes(n)]
    for groupe, seance in [(g, _libelle_du_groupe(g)) for g in groupes] or [(liste, None)]:
        for noeud, entete in _documents_et_entetes(groupe):
            document = _document(noeud, seance or entete, url)
            if isinstance(document, str):
                illisibles += 1
                _journal(nom, f"document illisible ({document})")
            else:
                documents.append(document)
    if illisibles and not documents:
        raise ValueError(f"{url} : aucun document lisible dans la page {debut}–{fin}")
    return documents, fin, total


_ENTETE_DE_SEANCE = re.compile(r"^(s[ée]ance|assembl[ée]e)\b.*\d{4}$", re.I)


def _documents_et_entetes(racine: Noeud):
    """Les documents (`div.qs-edit`) sous `racine`, dans l'ordre, chacun avec le dernier en-tête de Séance qui le
    précède hors d'un document (« Séance du 28 septembre 2026 », vue par années d'Etoy), sinon `None`."""
    entete = None
    pile = list(reversed(racine.enfants_elements()))
    while pile:
        noeud = pile.pop()
        if "qs-edit" in _classes(noeud) and noeud.attr("data-qsedit-editnode") is not None:
            yield noeud, entete
            continue
        enfants = noeud.enfants_elements()
        if not enfants and _ENTETE_DE_SEANCE.match(espaces(noeud.texte())):
            entete = espaces(noeud.texte())
        pile.extend(reversed(enfants))


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
    titre = titre or next((espaces(a.texte()) for a in liens if espaces(a.texte())), "")
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
    if seance is None and (_SEANCE_PAR_LE_TYPE.search(type_) or _SEANCE_PAR_LE_TITRE.match(titre)):
        # Une vue sans Séances (Mollens) : un procès-verbal ou un ordre du jour donne la sienne par son titre.
        jour_du_titre = date_ecrite(titre)
        seance = f"Séance du {jour_en_lettres(jour_du_titre)}" if jour_du_titre else None
    jour = date_ecrite(seance or "")
    if jour is None:
        seance = None
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


_SEANCE_PAR_LE_TYPE = re.compile(r"proc[èe]s|ordre|d[ée]cision", re.I)
_SEANCE_PAR_LE_TITRE = re.compile(r"^(proc[èe]s[- ]verbal|ordre du jour|extraits? d|d[ée]cisions?\b|convocation)", re.I)
# « Objet n° 05-2026 » (Juriens) ou « 05-2026 » seul (La Rippe) : la référence d'Objet d'un préavis sans numéro dans
# son titre ; « 005: Demande de crédit… » (Founex) n'en est pas une, son numéro est dans le titre du préavis.
_OBJET_NUMERO = re.compile(r"^(?:Objet\s+n[°o]\.?\s*)?(?P<numero>[\w/.-]*\d[\w/.-]*)$", re.I)

# --- Séances et préavis -------------------------------------------------------------------------------------------

# Le numéro qui suit « Préavis » : des chiffres et leurs séparateurs (« 005_2026-2031 », « 06/2025 », « 2026-14 »),
# l'année comprise quand elle suit après une barre ou une espace (« N°3 /2023 », « N° 1 / 2022 », « 04 2026 ») ; ce
# qui suit, lettres comprises, n'en est pas (« 01-2026-Comptes 2025.pdf » donne « 01-2026 »). Tel que le site l'écrit.
_NUMERO_PREAVIS = re.compile(
    r"^préavis(?:\s+municipal)?\s*(?:n[°o]\.?\s*)?"
    r"(?P<numero>(?:\d[\d/._-]*\d|\d)(?:\s*/\s*\d{2,4}\b|\s+(?:19|20)\d{2}\b)?)",
    re.I,
)
# Un document qui cite un Objet sans en être le préavis : son rapport, sa convocation, la réponse de la Municipalité.
_PAS_UN_PREAVIS = re.compile(r"^(rapport|convocation|r[ée]ponses?|amendement|annexe|plan|extrait|d[ée]cision)", re.I)
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
    # La recherche range d'une lecture à l'autre différemment les documents à égalité de tri (Lully, Oron) : ils sont
    # remis dans l'ordre de leur nœud, celui de leur mise en ligne, pour qu'un passage ne réécrive pas ce qu'il a lu
    # la veille. De deux préavis de même numéro, le plus ancien l'emporte donc.
    documents = sorted(documents, key=_noeud)
    dans_la_fenetre = [d for d in documents if depuis is None or _quand(d) is None or _quand(d) >= depuis]
    par_seance: dict[tuple[date, str], list[_Document]] = {}
    for d in dans_la_fenetre:
        if d.jour is not None and d.seance is not None:
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
        par_l_objet = _OBJET_NUMERO.match(d.objet or "")
        titre_de_preavis = d.titre.lower().startswith("préavis")
        type_de_preavis = (d.type or "").lower() in ("préavis", "preavis") or (
            not d.type and not _PAS_UN_PREAVIS.match(d.titre)
        )
        if not titre_de_preavis and not (par_l_objet and type_de_preavis):
            continue
        numero = _numero(d.titre) if titre_de_preavis else None
        if numero is None and par_l_objet and type_de_preavis:
            # Le titre ne porte pas de numéro (La Rippe, Juriens, Etoy) : il est dans « Objet n° 05-2026 ».
            numero = par_l_objet["numero"]
        if numero is None:
            _journal(nom, f"Objet sans numéro, non importé : {d.titre}")
            continue
        if any(p["number"] == numero for p in preavis):
            _journal(nom, f"Objet {numero} en double, le premier du site gardé : {d.titre}")
            continue
        # Les documents qui citent le même Objet : ceux de sa Séance s'il en a une, sinon tous ceux lus, même hors de
        # la fenêtre (un rapport de 2021 reste au préavis qui revient en 2026, Rolle).
        voisins = par_seance[(d.jour, d.seance)] if d.jour is not None and d.seance is not None else documents
        lies = [d] + [x for x in voisins if x is not d and _ref(d) is not None and _ref(x) == _ref(d)]
        preavis.append(
            {
                "id": None,
                "number": numero,
                "title": {"fr": _titre_du_preavis(d, numero)},
                "type_name": {"fr": TYPE_PREAVIS},
                "state_name": None,
                "begin_date": _quand(d).isoformat() if _quand(d) else None,
                "url_external": None,
                "contributors": {"data": []},
                "docs": {"data": [_doc(x) for x in lies]},
            }
        )
    return seances, preavis


def _noeud(d: _Document) -> int:
    """Le nœud du document (`/n<id>`), qui croît avec sa mise en ligne."""
    m = _LIEN_NOEUD.search(d.lien)
    return int(m[0][2:]) if m else 0


def _ref(d: _Document) -> str | None:
    """La référence de l'Objet qu'un document cite, sans son texte (« 072: Plans Port de Founex » donne « 072 »)."""
    if not d.objet:
        return None
    return re.sub(r"^Objet\s+n[°o]\.?\s*", "", d.objet, flags=re.I).split(":", 1)[0].strip() or None


def _numero(titre: str) -> str | None:
    m = _NUMERO_PREAVIS.match(titre)
    if m is None:
        return None
    numero = m["numero"].rstrip(".,;:")
    return None if _DATE_CHIFFRES.fullmatch(numero) else numero


def _titre_du_preavis(d: _Document, numero: str) -> str:
    """Le texte de l'Objet que le préavis cite (« 005: Demande de crédit… » donne « Demande de crédit… »), sinon la
    suite de son titre (« Préavis 04/2024 - Budget 2025 » donne « Budget 2025 »), sinon son titre."""
    if d.objet and ":" in d.objet:
        texte = re.sub(r"^\s*\S+\s*:\s*", "", d.objet)
        if texte:
            return texte
    if numero not in d.titre:
        return d.titre  # le titre est déjà le texte de l'Objet
    suite = d.titre[d.titre.index(numero) + len(numero) :].strip(" -–—:")
    return suite or d.titre


def _doc(d: _Document) -> dict:
    return {"name": d.titre, "url": d.lien, "date": d.publie.isoformat() if d.publie else None, "category": d.type}


# --- Mesure du site, pour le script de préparation des sources ------------------------------------------------------

ESSAIS = 6  # liens du menu essayés au plus pour trouver la page des documents du conseil
_TRACE = re.compile(r"quicksite|qsPortal|/coreapi/elasticsearch/|conseilcommunal/", re.I)
# Les liens du menu qui mènent aux documents du conseil, par ordre de préférence : ses documents, puis ses préavis,
# ses procès-verbaux, ses séances. Ni « Documents d'identité » ni les formulaires.
_LIENS_DU_MENU = (
    re.compile(r"documents?[ -](du|des|conseil)|documents-publics|/documents?$", re.I),
    re.compile(r"pr[ée]avis", re.I),
    re.compile(r"proc[èe]s[- ]verbaux|/pv\b", re.I),
    re.compile(r"s[ée]ances?|ordres? du jour|assembl[ée]es", re.I),
    re.compile(r"documents?", re.I),
)
_HORS_SUJET = re.compile(r"identit|passeport|formulaire|r[èe]glement|municipal(e|it)", re.I)
_PROJET = re.compile(r"/coreapi/elasticsearch/projects/([\w-]+)/assets/js/elasticsearch\.js")
VUES_DU_CONSEIL = ("documentconseil", "documentconseildates", "documentconseilyears")


def mesurer(pages: PagesLues, page_du_conseil: str, declare: Site, plateforme: Plateforme) -> Mesure:
    """Le site d'une commune mesuré pour le script de préparation des sources, d'après sa page du conseil (déjà lue)
    et ses pages déjà déclarées : une page sans trace de Quicksite l'écarte (« autre ») ; puis, parmi les pages
    déclarées, la page du conseil et `ESSAIS` liens de son menu au plus, la première qui porte le marqueur de sonde
    d'une variante, tel que `plateforme` le déclare (section `plateformes` de `sources.json`), et la liste qui va
    avec : la liste du module Conseil (`conseil`, ses conseillers en page des membres), la liste d'une ville vers le
    module (`conseil-externe`), la bibliothèque de l'ancienne génération (`ancienne`), ou la recherche `coreapi`
    d'une vue du conseil (`coreapi`, avec ses paramètres) ; le fragment de la recherche est lu pour que `requetes`
    rejoue la lecture. Le niveau et les requêtes du passage ordinaire sont l'affaire du script (`requetes`)."""
    conseil = pages.texte(page_du_conseil) or ""
    if not _TRACE.search(conseil):
        return Mesure("autre", remarques=[f"aucune trace de Quicksite sur {page_du_conseil}"])
    mesure = Mesure(plateforme.id)
    marqueurs = {v.id: v.marqueur for v in plateforme.variantes}

    def porte(texte: str, variante: str) -> bool:
        """La page porte le marqueur de sonde de `variante` ; une variante que `plateforme` ne déclare pas, aucun."""
        return variante in marqueurs and marqueurs[variante] in texte

    tous = [(u, f"{u} {t}") for u, t in liens(conseil, page_du_conseil) if not _HORS_SUJET.search(t)]
    menu = [u for motif in _LIENS_DU_MENU for u, texte in tous if motif.search(texte)]
    module = [urljoin(page_du_conseil, h) for h in re.findall(r'href="([^"]*/conseilcommunal/public/ordredujour/)"', conseil)]
    essais = [u for u in (declare.seances, *module, page_du_conseil) if u] + list(dict.fromkeys(menu))[:ESSAIS]
    autres_vues = []
    for url in dict.fromkeys(essais):
        texte = pages.texte(url)
        if texte is None:
            continue
        if porte(texte, "conseil"):
            mesure.variante, mesure.seances = "conseil", url
            conseillers = urljoin(url, "../conseillers/")  # avec sa barre : sans, le site redirige
            if pages.texte(conseillers) and "tplCCIBPublicConseillers" in (pages.texte(conseillers) or ""):
                mesure.membres = conseillers
            return mesure
        if porte(texte, "conseil-externe") and _ID_DU_MODULE.search(texte):
            mesure.variante, mesure.seances = "conseil-externe", url
            return mesure
        if porte(texte, "ancienne"):
            mesure.variante, mesure.seances = "ancienne", url
            return mesure
        if not porte(texte, "coreapi"):
            continue
        coreapi = _parametres_coreapi(texte)
        if coreapi is not None:
            mesure.variante, mesure.seances, mesure.coreapi = "coreapi", url, coreapi
            return mesure
        vue = re.search(r'class="tplDeepsearch"[^>]*?data-elasticsearch-view="([^"]*)"', texte, re.S)
        if vue:
            autres_vues.append(f"{url} (vue {vue[1]})")
    mesure.remarques.append("aucune page des documents du conseil Quicksite trouvée")
    if autres_vues:
        mesure.remarques.append(f"recherches d'une autre vue : {', '.join(autres_vues)}")
    return mesure


def _parametres_coreapi(texte: str) -> dict | None:
    """Les paramètres de la recherche `coreapi` d'une page, si c'est une vue des documents du conseil."""
    section = re.search(r'<section[^>]*class="tplDeepsearch"(.*?)>', texte, re.S)
    projet = _PROJET.search(texte)
    if section is None or projet is None:
        return None
    attrs = dict(re.findall(r'data-elasticsearch-([\w-]+)="([^"]*)"', section[1]))
    if attrs.get("view") not in VUES_DU_CONSEIL or not attrs.get("node", "").isdigit():
        return None
    return {
        "projet": projet[1],
        "vue": attrs["view"],
        "noeud": int(attrs["node"]),
        "taille": int(attrs.get("pagesize") or 60),
        "tri": attrs.get("sort") or "date_extid",
    }


class _RobotCompteur:
    """Un robot qui lit par les pages du script de préparation (chaque page une fois par lancement) et compte les
    requêtes que le passage ordinaire ferait : deux pour une page redirigée, une sinon."""

    def __init__(self, pages: PagesLues) -> None:
        self._pages = pages
        self.requetes = 0

    def lire(self, url: str, role: str) -> Reponse:
        page = self._pages.lire(url)
        self.requetes += 1 if isinstance(page, PageNonLue) or page.url == url else 2
        if isinstance(page, PageNonLue):
            raise page
        return page


def requetes(pages: PagesLues, source: Source, depuis: date | None) -> int | None:
    """Les requêtes que coûterait la lecture de `source` (`lire`) au passage ordinaire dont la fenêtre part de
    `depuis`. Les pages qui manquent sont lues par le robot du script (une liste Quicksite en demande peu : pages de
    résultats, ou Séances et fiches du module Conseil) ; `None` si la lecture échoue."""
    robot = _RobotCompteur(pages)
    try:
        sans_journal(lambda: lire(robot, source, depuis))  # type: ignore[arg-type]
    except (ValueError, PageNonLue):
        return None
    return robot.requetes


# --- Module Conseil (Montreux) ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _SeanceListee:
    nom: str
    jour: date
    heure: str | None  # « 19:30 »
    lien: str | None  # page de la Séance ; `None` pour une Séance annoncée sans page


_MOIS_COURTS = {m: i for i, m in enumerate(_MOIS, start=1)}
_HEURE = re.compile(r"\b(\d{1,2})\s*h\s*(\d{2})\b")
_ANNEE = re.compile(r"\b(\d{4})\b")


def _module_conseil(robot: Robot, source: Source, depuis: date | None, avec_objets: bool) -> tuple[list[dict], list[dict]]:
    """Les Séances du module Conseil, chacune avec sa page, et les Objets que leurs points citent."""
    site = source.site
    assert site is not None and site.seances is not None
    liste = robot.lire(site.seances, "import")
    seances: list[dict] = []
    objets: list[dict] = []
    fiches: dict[str, dict | None] = {}  # lien de la fiche → Objet lu (None : illisible)
    for ligne in _liste_du_module(liste.texte, liste.url):
        if isinstance(ligne, str):
            _journal(source.nom, f"ligne de Séance illisible ({ligne})")
            continue
        if depuis is not None and ligne.jour < depuis:
            continue
        if ligne.lien is None:
            seances.append(_meeting(ligne, [], []))
            continue
        try:
            page = robot.lire(ligne.lien, "import")
        except PageNonLue as e:
            _journal(source.nom, f"Séance {ligne.lien} non lue ({e})")
            continue
        titre = next((espaces(n.texte()) for n in arbre(page.texte).elements() if n.tag == "h1"), "")
        ligne = _SeanceListee(titre or ligne.nom, ligne.jour, ligne.heure, ligne.lien)  # le nom brut, celui de sa page
        points, documents = [], []
        for point in _points_du_module(page.texte, page.url):
            numero = None
            if avec_objets and point.fiche is not None:
                if point.fiche not in fiches:
                    fiches[point.fiche] = _fiche_d_objet(robot, source, point.fiche)
                objet = fiches[point.fiche]
                numero = objet["number"] if objet else None
            points.append({"item_number_display": None, "item_title": point.titre, "item_affair_number": numero})
            if numero is None:
                documents += point.documents
        seances.append(_meeting(ligne, points, documents))
    for objet in fiches.values():
        if objet is None:
            continue
        if any(o["number"] == objet["number"] for o in objets):
            _journal(source.nom, f"Objet {objet['number']} en double, le premier du site gardé : {objet['title']['fr']}")
            continue
        objets.append(objet)
    return seances, objets


def _meeting(ligne: _SeanceListee, points: list[dict], documents: list[dict]) -> dict:
    return {
        "id": None,
        "name": {"fr": ligne.nom},
        "begin_date": ligne.jour.isoformat() + (f"T{ligne.heure}:00" if ligne.heure else ""),
        "url_external": {"fr": ligne.lien} if ligne.lien else None,
        "agendas": {"data": points},
        "docs": {"data": documents},
    }


def _liste_du_module(texte: str, url: str) -> list[_SeanceListee | str]:
    """Les Séances de la liste du module, dans l'ordre du site : l'année en cours (pastilles), puis les années
    précédentes (onglets). Lève `ValueError` pour une page sans liste."""
    racine = arbre(texte)
    bloc = next((n for n in racine.elements() if "tplCCIBPublicOrdreJour" in _classes(n)), None)
    if bloc is None:
        raise ValueError(f"{url} : aucune liste de Séances (tplCCIBPublicOrdreJour)")
    titre = next((espaces(n.texte()) for n in bloc.elements() if n.tag == "h1"), "")
    annee = _ANNEE.search(titre)
    lignes: list[_SeanceListee | str] = []
    for noeud in racine.elements():
        classes = _classes(noeud)
        if any(c in classes for c in ("date-past", "date-nextmeeting", "date-future")):
            lignes.append(_pastille(noeud, int(annee[1]) if annee else None, url))
        elif "table-row-body" in classes and any(
            "/ordredujour/" in (a.attr("href") or "") for a in noeud.elements() if a.tag == "a"
        ):
            lignes.append(_ligne_d_annee(noeud, url))
    return lignes


def _pastille(noeud: Noeud, annee: int | None, url: str) -> _SeanceListee | str:
    jour = next((espaces(n.texte()) for n in noeud.elements() if "day" in _classes(n)), "")
    mois = next((espaces(n.texte()) for n in noeud.elements() if n.tag == "label"), "")
    if annee is None or not jour.isdigit() or mois.lower() not in _MOIS_COURTS:
        return f"date illisible « {jour} {mois} »"
    try:
        quand = date(annee, _MOIS_COURTS[mois.lower()], int(jour))
    except ValueError:
        return f"date impossible « {jour} {mois} {annee} »"
    lien = next(
        (urljoin(url, a.attr("href") or "") for a in noeud.elements() if a.tag == "a" and "ID=" in (a.attr("href") or "")),
        None,
    )
    return _SeanceListee(f"Séance du {jour_en_lettres(quand)}", quand, None, lien)


def _ligne_d_annee(noeud: Noeud, url: str) -> _SeanceListee | str:
    a = next(a for a in noeud.elements() if a.tag == "a" and "/ordredujour/" in (a.attr("href") or ""))
    quand = date_ecrite(espaces(noeud.texte()))
    if quand is None:
        return f"sans date : {espaces(a.texte())}"
    return _SeanceListee(espaces(a.texte()), quand, None, urljoin(url, a.attr("href") or ""))


@dataclass(frozen=True)
class _PointDuModule:
    titre: str
    fiche: str | None  # la fiche de l'Objet cité (`documents/recherche/?id=<id>`)
    documents: list[dict]


def _points_du_module(texte: str, url: str) -> list[_PointDuModule]:
    """Les points de la page d'une Séance du module Conseil, dans l'ordre du site."""
    points = []
    for carte in (n for n in arbre(texte).elements() if n.tag == "div" and "card" in _classes(n)):
        fiche = next(
            (a for a in carte.elements() if a.tag == "a" and "/documents/recherche/" in (a.attr("href") or "")), None
        )
        description = next((n for n in carte.elements() if "description" in _classes(n)), None)
        titre = espaces(description.texte()) if description else ""
        points.append(
            _PointDuModule(
                titre=titre,
                fiche=urljoin(url, fiche.attr("href") or "") if fiche else None,
                documents=_documents_du_module(carte, url),
            )
        )
    return points


def _documents_du_module(noeud: Noeud, url: str) -> list[dict]:
    """Les documents (`download.asp?d=<id>`) d'un nœud, chacun une fois, nommés par leur fichier (`title`), sinon
    par le texte du lien sans sa taille ; datés quand leur ligne porte une date."""
    documents, vus = [], set()
    for a in noeud.elements():
        lien = urljoin(url, a.attr("href") or "") if a.tag == "a" else ""
        if "download.asp?d=" not in lien.lower() or lien in vus:
            continue
        vus.add(lien)
        nom = a.attr("title") or _texte_sans_taille(a) or lien.rsplit("=", 1)[-1]
        documents.append({"name": nom, "url": lien, "date": None, "category": None})
    return documents


def _texte_sans_taille(a: Noeud) -> str:
    """Le texte d'un lien sans la taille du fichier qui le suit (`span.info-file`, `span.badge`)."""
    morceaux = [
        e if isinstance(e, str) else e.texte()
        for e in a.enfants
        if isinstance(e, str) or not {"info-file", "badge"} & set(_classes(e))
    ]
    return espaces(" ".join(morceaux))


def _fiche_d_objet(robot: Robot, source: Source, url: str) -> dict | None:
    """L'Objet de sa fiche, à la forme d'une *affair* ; `None`, noté dans le journal, s'il ne se lit pas ou n'a
    pas de numéro."""
    try:
        page = robot.lire(url, "import")
    except PageNonLue as e:
        _journal(source.nom, f"Objet {url} non lu ({e})")
        return None
    racine = arbre(page.texte)
    bloc = next((n for n in racine.elements() if "tplDetailBlade" in _classes(n)), racine)
    entete = next((espaces(n.texte()) for n in bloc.elements() if n.tag == "h1"), "")
    m = re.match(r"^(?P<type>\D+?)\s+(?:n[°o]\.?\s*)?(?P<numero>\d[\w/.-]*)", entete)
    if m is None:
        _journal(source.nom, f"Objet sans numéro, non importé : {entete or url}")
        return None
    texte = next((espaces(n.texte()) for n in bloc.elements() if n.tag == "h5"), "")
    auteur = re.search(r"Auteur\s*:\s*(.+)", next((espaces(n.texte()) for n in bloc.elements() if n.tag == "small"), ""))
    documents = []
    for ligne in (n for n in bloc.elements() if "table-row-body" in _classes(n)):
        lien = next((a for a in ligne.elements() if a.tag == "a" and "download.asp" in (a.attr("href") or "")), None)
        if lien is None:
            continue
        colonnes = [espaces(c.texte()) for c in ligne.enfants_elements() if c.tag == "div"]
        jour = next((date_ecrite(c) for c in reversed(colonnes) if date_ecrite(c)), None)
        nom = lien.attr("title") or espaces(lien.texte())
        documents.append(
            {"name": nom, "url": urljoin(page.url, lien.attr("href") or ""), "date": jour.isoformat() if jour else None,
             "category": colonnes[-2] if len(colonnes) >= 2 else None}
        )
    contributeurs = []
    if auteur:
        nom = auteur[1].strip()
        groupe = re.match(r"^(municipalit[ée]|commission|bureau|groupe)", nom, re.I) is not None
        contributeurs.append({"type": "organization" if groupe else "person", "fullname": nom})
    dates = [d["date"] for d in documents if d["date"]]
    return {
        "id": None,
        "number": m["numero"].rstrip(".,;:"),
        "title": {"fr": texte or entete},
        "type_name": {"fr": m["type"].strip()},
        "state_name": None,
        "begin_date": min(dates) if dates else None,
        "url_external": {"fr": page.url},
        "contributors": {"data": contributeurs},
        "docs": {"data": documents},
    }


def _conseillers(robot: Robot, source: Source) -> list[str]:
    """Les conseillers du module (`site.membres`), page après page (`rel="next"`), chacun « Prénom Nom ». Une page
    illisible est notée dans le journal et arrête la lecture : l'import continue avec ceux déjà lus."""
    url = source.site.membres if source.site else None
    membres: list[str] = []
    vues: set[str] = set()
    while url and url not in vues and len(vues) < 10:
        vues.add(url)
        try:
            page = robot.lire(url, "import")
        except PageNonLue as e:
            _journal(source.nom, f"page des membres {url} non lue ({e})")
            break
        racine = arbre(page.texte)
        for ligne in (n for n in racine.elements() if "table-row-body" in _classes(n)):
            a = next((a for a in ligne.elements() if a.tag == "a" and any(b.tag == "b" for b in a.elements())), None)
            if a is None:
                continue
            nom = espaces(next(b for b in a.elements() if b.tag == "b").texte())
            prenom = espaces(a.texte())[len(nom) :].strip()
            if nom:
                membres.append(f"{prenom} {nom}".strip())
        suivante = next((a for a in racine.elements() if a.tag == "a" and a.attr("rel") == "next"), None)
        url = urljoin(page.url, suivante.attr("href") or "") if suivante else None
    return membres


# --- Module Conseil dont la liste est sur le site de la Ville (Vevey) -----------------------------------------------

_ID_DU_MODULE = re.compile(r"/conseilcommunal/seances/\?ID=(\d+)", re.I)


def _module_conseil_externe(robot: Robot, source: Source, depuis: date | None) -> list[dict]:
    """Les Séances de la liste du site de la Ville, chacune avec la page de son ordre du jour sur le module."""
    site = source.site
    assert site is not None and site.seances is not None
    liste = robot.lire(site.seances, "import")
    hote = HOTES_DU_MODULE.get(urlsplit(liste.url).hostname or "", urlsplit(liste.url).hostname)
    seances = []
    lignes = [n for n in arbre(liste.texte).elements() if "teaser-agenda" in _classes(n)]
    illisibles = 0
    for noeud in lignes:
        titre = next((espaces(a.texte()) for a in noeud.elements() if a.tag == "a"), "")
        quand = date_ecrite(titre)
        if quand is None:
            illisibles += 1
            _journal(source.nom, f"ligne de Séance illisible (sans date : {titre})")
            continue
        if depuis is not None and quand < depuis:
            continue
        heure = _HEURE.search(titre)
        ordre = next((m for a in noeud.elements() if a.tag == "a" and (m := _ID_DU_MODULE.search(a.attr("href") or ""))), None)
        lien = f"https://{hote}/ConseilCommunal/seances/?ID={ordre[1]}" if ordre else None
        ligne = _SeanceListee(titre, quand, f"{int(heure[1]):02d}:{heure[2]}" if heure else None, lien)
        if lien is None:
            seances.append(_meeting(ligne, [], []))
            continue
        try:
            page = robot.lire(lien, "import")
        except PageNonLue as e:
            _journal(source.nom, f"Séance {lien} non lue ({e})")
            continue
        points, documents = _ordre_du_jour_du_module(page.texte, page.url)
        seances.append(_meeting(ligne, points, documents))
    if lignes and illisibles == len(lignes):
        raise ValueError(f"{liste.url} : aucune ligne de Séance lisible")
    return seances


def _ordre_du_jour_du_module(texte: str, url: str) -> tuple[list[dict], list[dict]]:
    """Les points numérotés de l'ordre du jour d'une Séance du module (« 9. », « 9.1 »), et ses documents."""
    points, documents = [], []
    for groupe in (n for n in arbre(texte).elements() if "centerGroup" in _classes(n)):
        numero = next((espaces(n.texte()) for n in groupe.elements() if "number" in _classes(n)), "").rstrip(".")
        titre = next((espaces(n.texte()) for n in groupe.elements() if "title" in _classes(n)), "")
        sous = [n for n in groupe.elements() if n.tag == "li"]
        if not sous:
            points.append({"item_number_display": numero or None, "item_title": titre, "item_affair_number": None})
        for li in sous:
            num = next((espaces(n.texte()) for n in li.elements() if "theme-num" in _classes(n)), "")
            sujet = next((espaces(n.texte()) for n in li.elements() if "theme" in _classes(n)), "")
            points.append({"item_number_display": num or None, "item_title": sujet, "item_affair_number": None})
        documents += _documents_du_module(groupe, url)
    return points, documents

