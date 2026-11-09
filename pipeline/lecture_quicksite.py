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
« séances et préavis ») : un document dont le titre commence par « Préavis », ou qui, typé « Préavis » ou sans type,
cite son Objet par un numéro seul (« Objet n° 05-2026 ») ; jamais un document que son titre dit être autre chose
(rapport de commission ou de minorité, convocation, réponse, annexe, plan, extrait, décision), quel que soit son type.
Son numéro brut est celui de son titre (« Préavis 005_2026-2031 », « Préavis 06/2025 »), sinon, quand le titre n'en
porte pas (Etoy, La Rippe), celui de sa référence d'Objet ; son type est « Préavis », sa date celle de sa Séance ; ses
documents sont le préavis et ceux de la même Séance qui citent le même Objet (« 072: … »). Un préavis sans numéro
n'est pas importé, noté dans le journal. Les documents sont rangés par nœud (`/n<id>`, qui croît avec la mise en
ligne) : la recherche ne range pas toujours de la même façon des documents à égalité de tri. De deux préavis de même
numéro, le plus ancien (le plus petit nœud) l'emporte donc, et non le premier dans l'ordre du site ; l'autre est noté
dans le journal, avec celui qui est gardé.

Variante **`conseil`** (module « Conseil communal » de Quicksite, sur un site à part : Montreux) : la liste des
Séances (`site.seances`, `ordredujour/`) donne l'année en cours en pastilles (jour, mois ; les Séances annoncées
sans page n'ont pas de lien) et les années précédentes en onglets (date, lien) ; chaque Séance a sa page
(`ordredujour/?ID=<id>`, lien stable), dont chaque point (`div.card`) a son texte, cite parfois son Objet
(`documents/recherche/?id=<id>`) et donne ses documents (`download.asp?d=<id>`, nommés par le texte de leur lien
sans sa taille, sinon par leur fichier). La fiche de chaque Objet cité est ouverte : numéro brut et type de son titre
(« Préavis 29/2026 »), texte, auteur·e (« Auteur : Municipalité »), documents typés et datés ; pas de statut. Un
point qui cite un Objet lui laisse ses documents, même quand sa fiche ne se lit pas : l'Objet est alors sauté, noté
dans le journal, et les retrouve au passage où sa fiche se relit (à la Séance, l'import les garderait pour toujours).
Seuls les documents des points sans Objet vont à la Séance. Les conseillers (`site.membres`, « **Nom** Prénom ») sont
lus page après page (`rel="next"`).

Variante **`conseil-externe`** (le module Conseil dont la liste des Séances est sur le site de la Ville : Vevey) :
la page `site.seances` (Drupal) donne chaque Séance (`div.teaser-agenda` : « Séance du Conseil communal du jeudi
1er octobre 2026 - 19h30 ») et le lien de son ordre du jour sur le module (`conseilcommunal/seances/?ID=<id>`). Ce
lien donne l'hôte du module : le sien, ou, quand il est cassé, le premier segment de son chemin
(`www.vevey.ch/conseil.vevey.ch/conseilcommunal/…`) ; il est récrit vers
`https://<hôte du module>/ConseilCommunal/seances/?ID=<id>`, à la casse que `robots.txt` autorise. La page d'une
Séance (ISO-8859-1) donne ses points numérotés (`div.centerGroup`, `h2` : « 9. », puis « 9.1 » et son titre) et leurs
documents ; tous vont à la Séance (niveau « séances seulement »). Une page de Séance sans points est sautée, notée
dans le journal ; si aucune page de Séance à ouvrir ne se lit, l'import est en échec, comme pour une liste dont aucune
ligne ne se lit : la sonde lit la liste de la Ville et ne verrait pas une refonte du module.

**Dates** : celle de la Séance que le site donne, même fictive ; un document est daté de sa publication quand le
site l'affiche. Les dates des noms de fichiers et de `Content-Disposition` ne servent pas : chaque document de ces
vues a sa Séance (choix à relire, #175).

**Fenêtre** : la recherche `coreapi` est lue en entier, chaque jour, comme toute page de liste (spec, « Fenêtre ») ;
au passage ordinaire, seuls les Séances et préavis de la fenêtre sont importés. La bibliothèque de l'ancienne
génération, triée par mise en ligne, s'arrête à la première page mise en ligne avant la fenêtre ; le rattrapage la
lit en entier. Une liste paginée s'arrête à sa dernière page, ou à une page qui ne donne rien de nouveau ; au-delà de
`PAGES_MAX` pages, garde-fou contre une pagination sans fin, elle est tronquée et notée dans le journal. Un document
illisible (sans lien ou sans Séance datée) est sauté et noté dans le journal ; un fragment sans liste de documents, ou
dont aucun document ne se lit, lève `ValueError`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode, urljoin, urlsplit

from bruts import Bruts
from mesure_sites import Mesure, PagesLues, RobotCompteur, liens, sans_journal
from pages_html import Noeud, arbre, espaces
from robot_communal import PageNonLue, Reponse, Robot
from schema import Coreapi, Plateforme, Site, Source, niveau_de

VARIANTES = ("ancienne", "coreapi", "conseil", "conseil-externe")
TYPE_PREAVIS = "Préavis"  # le type d'un préavis lu dans une liste de documents
# Pages lues au plus d'une liste paginée, même au rattrapage : un garde-fou contre une pagination sans fin, loin de tout
# historique réel (20 000 documents d'une bibliothèque, 60 000 au moins d'une recherche `coreapi`). Atteint, il tronque
# la liste, et le journal le dit.
PAGES_MAX = 1000


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


def _page_de_liste(robot: Robot, source: Source, url: str, page: int) -> Reponse | None:
    """La page `page` d'une liste paginée. La première doit se lire (sinon l'import est en échec) ; une suivante
    qui ne se lit pas finit la liste, notée dans le journal (un réseau bloqué interrompt quand même l'import)."""
    if page == 1:
        return robot.lire(url, "import")
    try:
        return robot.lire(url, "import")
    except PageNonLue as e:
        _journal(source.nom, f"page {page} de la liste non lue ({e}), liste lue jusqu'à la page {page - 1}")
        return None


def _liste_tronquee(nom: str) -> None:
    """Note dans le journal une liste paginée lue jusqu'à `PAGES_MAX` sans en voir la fin."""
    _journal(nom, f"liste tronquée : {PAGES_MAX} pages lues sans en voir la fin, les suivantes ne le sont pas")


def _meeting(
    nom: str,
    jour: date,
    documents: list[dict],
    *,
    heure: str | None = None,
    lien: str | None = None,
    points: list[dict] | None = None,
) -> dict:
    """Une Séance à la forme d'un *meeting* d'OpenParlData, sans identifiant (ADR 0010) : son nom brut, son jour et
    son heure (« 19:30 ») si le site la donne, sa page propre si elle en a une, les points de son ordre du jour s'il
    est structuré, et ses documents."""
    return {
        "id": None,
        "name": {"fr": nom},
        "begin_date": jour.isoformat() + (f"T{heure}:00" if heure else ""),
        "url_external": {"fr": lien} if lien else None,
        "agendas": {"data": points or []},
        "docs": {"data": documents},
    }


def _affair(
    numero: str,
    titre: str,
    type_: str,
    depose: str | None,
    documents: list[dict],
    *,
    lien: str | None = None,
    contributeurs: list[dict] | None = None,
) -> dict:
    """Un Objet à la forme d'une *affair* d'OpenParlData, sans identifiant (ADR 0010) ni statut (aucune variante de
    Quicksite n'en publie) : son numéro brut, son titre, son type, sa date, sa page propre si elle en a une, ses
    auteur·e·s s'ils sont publiés, et ses documents."""
    return {
        "id": None,
        "number": numero,
        "title": {"fr": titre},
        "type_name": {"fr": type_},
        "state_name": None,
        "begin_date": depose,
        "url_external": {"fr": lien} if lien else None,
        "contributors": {"data": contributeurs or []},
        "docs": {"data": documents},
    }


def _en_double(nom: str, objets: list[dict], numero: str, titre: str, regle: str) -> bool:
    """Un Objet de numéro `numero` est déjà parmi `objets` : celui de titre `titre` est sauté, noté dans le journal
    avec celui que `regle` a gardé (« le premier du site », « le plus ancien »)."""
    garde = next((o for o in objets if o["number"] == numero), None)
    if garde is not None:
        _journal(nom, f"Objet {numero} en double, {regle} gardé (« {garde['title']['fr']} ») : {titre}")
    return garde is not None


def _doc(d: _DocumentDeBibliotheque | _DocumentDeRecherche) -> dict:
    """Un document d'une liste, à la forme d'un document d'OpenParlData : son titre, son lien stable, sa
    publication et son type."""
    return {"name": d.titre, "url": d.lien, "date": d.publie.isoformat() if d.publie else None, "category": d.type}


# --- Bibliothèque (ancienne génération) ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _DocumentDeBibliotheque:
    """Un document de la bibliothèque de l'ancienne génération : la référence de son Objet et sa description, mais
    pas de Séance (elle se lit dans son titre)."""

    lien: str  # lien stable `Home.asp?N=<id>&DocAction=Download`, absolu
    titre: str
    type: str | None
    reference: str | None  # la référence de son Objet (`strBusinessID`, « 2026-14 »)
    description: str
    publie: date | None  # sa mise en ligne


TYPES_DE_SEANCE = ("Ordre du jour", "PV du conseil", "Décision")
_TITRES_DE_SEANCE = re.compile(r"^(ordre du jour|proc[èe]s[- ]verbal|extrait de d[ée]cision)", re.I)
_CITE_UN_PREAVIS = re.compile(r"pr[ée]avis\s+(?:n[°o]\.?\s*)?(\d[\w/-]*\d)", re.I)


def _url_de_page(site: Site, page: int) -> str:
    """La page `page` de la bibliothèque des documents (la première est `site.seances` elle-même)."""
    if site.seances is None:
        raise ValueError("variante ancienne sans page `seances`")
    if page == 1:
        return site.seances
    return f"{site.seances}{'&' if '?' in site.seances else '?'}Page_0={page}"


def _documents_bibliotheque(robot: Robot, source: Source, depuis: date | None) -> list[_DocumentDeBibliotheque]:
    """Les documents de la bibliothèque, dans l'ordre du site, page après page : jusqu'à une page vide ou qui ne
    donne rien de nouveau, et, au passage ordinaire, jusqu'à la première page mise en ligne avant la fenêtre."""
    site = source.site
    assert site is not None
    documents: list[_DocumentDeBibliotheque] = []
    vus: set[str] = set()
    for page in range(1, PAGES_MAX + 1):
        reponse = _page_de_liste(robot, source, _url_de_page(site, page), page)
        if reponse is None:
            break
        lus = _page_de_bibliotheque(source.nom, reponse.texte, reponse.url)
        nouveaux = [d for d in lus if d.lien not in vus]
        if not nouveaux:
            break
        vus.update(d.lien for d in nouveaux)
        documents += nouveaux
        if depuis is not None and all(d.publie is not None and d.publie < depuis for d in nouveaux):
            break
    else:
        _liste_tronquee(source.nom)
    return documents


def _page_de_bibliotheque(nom: str, texte: str, url: str) -> list[_DocumentDeBibliotheque]:
    """Les documents d'une page de la bibliothèque. Lève `ValueError` pour une page sans bibliothèque, ou dont
    aucun document ne se lit."""
    liste = arbre(texte).premier(lambda n: "tplListDocumentSummary" in n.classes())
    if liste is None:
        raise ValueError(f"{url} : aucune bibliothèque de documents (tplListDocumentSummary)")
    documents: list[_DocumentDeBibliotheque] = []
    illisibles = 0
    for noeud in (n for n in liste.elements() if "tplDocumentSummaryItem" in n.classes()):
        document = _document_de_bibliotheque(noeud, url)
        if isinstance(document, str):
            illisibles += 1
            _journal(nom, f"document illisible ({document})")
        else:
            documents.append(document)
    if illisibles and not documents:
        raise ValueError(f"{url} : aucun document lisible dans la bibliothèque")
    return documents


def _document_de_bibliotheque(noeud: Noeud, url: str) -> _DocumentDeBibliotheque | str:
    """Un document de la bibliothèque, ou la raison pour laquelle il ne se lit pas."""
    titre = noeud.texte_du_premier(lambda n: "strNodeName" in n.classes())
    lien = noeud.premier(lambda n: n.tag == "a" and "DocAction=Download" in (n.attr("href") or ""))
    if lien is None:
        return f"sans lien vers le document : {titre or url}"
    reference = noeud.texte_du_premier(lambda n: "strBusinessID" in n.classes()).rstrip(": ")
    return _DocumentDeBibliotheque(
        lien=urljoin(url, lien.attr("href") or ""),
        titre=titre or "Document",
        type=noeud.texte_du_premier(lambda n: n.attr("id") == "doctype") or None,
        reference=reference or None,
        description=noeud.texte_du_premier(lambda n: "strDescription" in n.classes()),
        publie=_date_ecrite(noeud.texte_du_premier(lambda n: "dtmDocLastUpdate" in n.classes())),
    )


def _bibliotheque(
    nom: str, documents: list[_DocumentDeBibliotheque], depuis: date | None, avec_preavis: bool
) -> tuple[list[dict], list[dict]]:
    """Les Séances, tirées des ordres du jour, procès-verbaux et décisions datés, et les préavis de la bibliothèque,
    dans l'ordre du site, ceux de la fenêtre seulement."""
    par_seance: dict[date, list[_DocumentDeBibliotheque]] = {}
    for d in documents:
        if d.type not in TYPES_DE_SEANCE and not (d.type is None and _TITRES_DE_SEANCE.match(d.titre)):
            continue
        jour = _date_ecrite(d.titre) or _date_ecrite(d.description)
        if jour is None:
            _journal(nom, f"document de Séance sans date : {d.titre}")
            continue
        if depuis is None or jour >= depuis:
            par_seance.setdefault(jour, []).append(d)
    seances = [
        _meeting(f"Séance du {_jour_en_lettres(jour)}", jour, [_doc(d) for d in docs])
        for jour, docs in par_seance.items()
    ]
    if not avec_preavis:
        return seances, []
    preavis: list[dict] = []
    for d in documents:
        if d.type != TYPE_PREAVIS or (depuis is not None and d.publie is not None and d.publie < depuis):
            continue
        numero = _numero(d.titre)
        if numero is None:
            _journal(nom, f"Objet sans numéro, non importé : {d.titre}")
            continue
        if _en_double(nom, preavis, numero, d.titre, "le premier du site"):
            continue
        lies = [d] + [x for x in documents if x is not d and x.type != TYPE_PREAVIS and numero in _cites(x)]
        suite = d.titre[d.titre.index(numero) + len(numero) :].strip(" -–—:")
        depose = d.publie.isoformat() if d.publie else None
        preavis.append(_affair(numero, suite or d.titre, TYPE_PREAVIS, depose, [_doc(x) for x in lies]))
    return seances, preavis


def _cites(d: _DocumentDeBibliotheque) -> set[str]:
    """Les numéros d'Objet qu'un document cite : sa référence, et les préavis que son titre nomme."""
    cites = set(_CITE_UN_PREAVIS.findall(d.titre))
    return cites | {d.reference} if d.reference else cites


def _jour_en_lettres(jour: date) -> str:
    """« 1er octobre 2026 », « 29 octobre 2026 »."""
    return f"{'1er' if jour.day == 1 else jour.day} {_MOIS[jour.month - 1]} {jour.year}"


# --- Recherche `coreapi` ------------------------------------------------------------------------------------------


def _url_de_recherche(site: Site, page: int = 1) -> str:
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
class _DocumentDeRecherche:
    """Un document de la recherche `coreapi` : sa Séance et l'Objet qu'il cite, s'il en a, mais pas de description."""

    lien: str  # lien stable `/n<id>`, absolu
    titre: str
    type: str | None  # le type du site (« Préavis », « Décisions »), s'il en donne un
    seance: str | None  # le libellé de sa Séance, tel quel (« Séance du 1 janvier 2025 »), s'il en a une
    jour: date | None  # le jour de sa Séance
    publie: date | None
    objet: str | None  # l'Objet que le document cite (« 005: Demande de crédit… »)


_TOTAL = re.compile(r"(\d+)\s*à\s*(\d+)\s*sur\s*(\d+)\s*éléments?")


def _documents_coreapi(robot: Robot, source: Source, depuis: date | None) -> list[_DocumentDeRecherche]:
    """Les documents de la recherche `coreapi`, dans l'ordre du site, page de résultats après page de résultats,
    toutes, même au passage ordinaire (`depuis` n'y change rien) : la recherche n'est pas triée par mise en ligne,
    et une Séance ou un préavis de la fenêtre peut avoir des documents sur n'importe quelle page. Lire moins
    réécrirait l'élément avec une partie de ses documents. Elle s'arrête à la fin du total (« 1 à 60 sur 399 »), ou à
    une page qui ne donne rien de nouveau (un site qui ignorerait `page` rendrait la première sans fin) ; un document
    qu'une page reprend d'une autre, sous la même Séance, n'est lu qu'une fois."""
    site = source.site
    assert site is not None
    documents: list[_DocumentDeRecherche] = []
    vus: set[_DocumentDeRecherche] = set()
    for page in range(1, PAGES_MAX + 1):
        reponse = _page_de_liste(robot, source, _url_de_recherche(site, page), page)
        if reponse is None:
            break
        lus, fin, total = _page_de_resultats(source.nom, reponse.texte, reponse.url)
        nouveaux = [d for d in lus if d not in vus]
        vus.update(nouveaux)
        documents += nouveaux
        if not nouveaux or fin >= total:
            break
    else:
        _liste_tronquee(source.nom)
    return documents


def _quand(d: _DocumentDeRecherche) -> date | None:
    """Le jour d'un document : celui de sa Séance, sinon sa publication."""
    return d.jour or d.publie


def _page_de_resultats(nom: str, texte: str, url: str) -> tuple[list[_DocumentDeRecherche], int, int]:
    """Les documents d'une page de résultats, et la position de sa fin dans le total (« 1 à 60 sur 399 éléments
    trouvés »). Lève `ValueError` pour un fragment sans liste de documents, ou dont aucun document ne se lit."""
    racine = arbre(texte)
    # La liste du thème de 2023 (`tplDocumentConseil`), ou celle d'un thème plus ancien (Rolle, Trélex).
    liste = racine.premier(lambda n: "tplDocumentConseil" in n.classes() or n.attr("id") == "search-standard-result")
    if liste is None:
        raise ValueError(f"{url} : aucune liste de documents (tplDocumentConseil, search-standard-result)")
    position = _TOTAL.search(espaces(racine.texte()))
    debut, fin, total = (int(x) for x in position.groups()) if position else (0, 0, 0)
    documents: list[_DocumentDeRecherche] = []
    illisibles = 0
    groupes = [n for n in liste.elements() if "accordion-item" in n.classes()]
    for groupe, seance in [(g, _libelle_du_groupe(g)) for g in groupes] or [(liste, None)]:
        for noeud, entete in _documents_et_entetes(groupe):
            document = _document_de_recherche(noeud, seance or entete, url)
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
        if "qs-edit" in noeud.classes() and noeud.attr("data-qsedit-editnode") is not None:
            yield noeud, entete
            continue
        enfants = noeud.enfants_elements()
        if not enfants and _ENTETE_DE_SEANCE.match(espaces(noeud.texte())):
            entete = espaces(noeud.texte())
        pile.extend(reversed(enfants))


def _libelle_du_groupe(groupe: Noeud) -> str | None:
    """Le libellé de la Séance d'un groupe de documents : l'en-tête du groupe (son bouton), « Séance du … »."""
    entete = groupe.premier(lambda n: "accordion-header" in n.classes() or n.tag == "button")
    return espaces(entete.texte()) if entete else None


_LIEN_NOEUD = re.compile(r"/n\d+$")


def _document_de_recherche(noeud: Noeud, seance: str | None, url: str) -> _DocumentDeRecherche | str:
    """Un document de la recherche, ou la raison pour laquelle il ne se lit pas."""
    liens = [a for a in noeud.elements() if a.tag == "a" and _LIEN_NOEUD.search(a.attr("href") or "")]
    titre = noeud.texte_du_premier(lambda n: n.tag in ("h5", "h6"))
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
        jour_du_titre = _date_ecrite(titre)
        seance = f"Séance du {_jour_en_lettres(jour_du_titre)}" if jour_du_titre else None
    jour = _date_ecrite(seance or "")
    if jour is None:
        seance = None
    publie = re.search(r"Publié le\s+(.+)", espaces(noeud.texte()))
    objet = filtres["ext_id"].attr("data-filter-value") if "ext_id" in filtres else None
    return _DocumentDeRecherche(
        lien=liens[0].attr("href") or "",
        titre=titre or (liens[0].attr("href") or "").rsplit("/", 1)[-1],
        type=type_ or None,
        seance=seance,
        jour=jour,
        publie=_date_ecrite(publie[1]) if publie else None,
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
# Un document qui cite un Objet sans en être le préavis, quel que soit le type que le site lui donne : un rapport (de
# commission, de minorité…), une convocation, la réponse de la Municipalité, un amendement, une annexe, un plan, un
# extrait, une décision. Le rapport de gestion et le rapport-préavis de la Municipalité restent des préavis (Lully type
# « Préavis » son rapport de gestion).
_PAS_UN_PREAVIS = re.compile(
    r"^(rapports?(?!\s+de\s+gestion|[\s-]+pr[ée]avis)|convocations?|r[ée]ponses?|amendements?|annexes?|plans?|"
    r"extraits?|d[ée]cisions?)\b",
    re.I,
)
_TYPES_DE_PREAVIS = ("préavis", "preavis")
_DATE_CHIFFRES = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_MOIS = "janvier février mars avril mai juin juillet août septembre octobre novembre décembre".split()
_DATE_LETTRES = re.compile(rf"\b(\d{{1,2}})(?:er)?\s+({'|'.join(_MOIS)})\s+(\d{{4}})\b", re.I)


def _date_ecrite(texte: str) -> date | None:
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
    nom: str, documents: list[_DocumentDeRecherche], depuis: date | None, avec_preavis: bool
) -> tuple[list[dict], list[dict]]:
    """Les Séances (*meetings*) et les préavis (*affairs*) des documents, dans l'ordre de leurs nœuds, ceux de la
    fenêtre seulement."""
    # La recherche range d'une lecture à l'autre différemment les documents à égalité de tri (Lully, Oron) : ils sont
    # remis dans l'ordre de leur nœud, celui de leur mise en ligne, pour qu'un passage ne réécrive pas ce qu'il a lu
    # la veille. De deux préavis de même numéro, le plus ancien l'emporte donc, et non le premier du site.
    documents = sorted(documents, key=_numero_de_noeud)
    dans_la_fenetre = [d for d in documents if depuis is None or _quand(d) is None or _quand(d) >= depuis]
    par_seance: dict[tuple[date, str], list[_DocumentDeRecherche]] = {}
    for d in dans_la_fenetre:
        if d.jour is not None and d.seance is not None:
            par_seance.setdefault((d.jour, d.seance), []).append(d)
    seances = [_meeting(libelle, jour, [_doc(d) for d in docs]) for (jour, libelle), docs in par_seance.items()]
    if not avec_preavis:
        return seances, []
    preavis: list[dict] = []
    for d in dans_la_fenetre:
        if not _est_un_preavis(d):
            continue
        numero = _numero(d.titre) or _reference_seule(d)
        if numero is None:
            _journal(nom, f"Objet sans numéro, non importé : {d.titre}")
            continue
        if _en_double(nom, preavis, numero, d.titre, "le plus ancien"):
            continue
        # Les documents qui citent le même Objet : ceux de sa Séance s'il en a une, sinon tous ceux lus, même hors de
        # la fenêtre (un rapport de 2021 reste au préavis qui revient en 2026, Rolle).
        voisins = par_seance[(d.jour, d.seance)] if d.jour is not None and d.seance is not None else documents
        lies = [d] + [x for x in voisins if x is not d and _ref(d) is not None and _ref(x) == _ref(d)]
        quand = _quand(d)
        depose = quand.isoformat() if quand else None
        preavis.append(_affair(numero, _titre_du_preavis(d, numero), TYPE_PREAVIS, depose, [_doc(x) for x in lies]))
    return seances, preavis


def _est_un_preavis(d: _DocumentDeRecherche) -> bool:
    """Un préavis : un document dont le titre commence par « Préavis », ou qui, typé « Préavis » ou sans type, cite
    son Objet par un numéro seul (« Objet n° 05-2026 », La Rippe, Juriens) ; jamais un document que son titre dit être
    autre chose (`_PAS_UN_PREAVIS`), quel que soit son type."""
    if _PAS_UN_PREAVIS.match(d.titre):
        return False
    if d.titre.lower().startswith("préavis"):
        return True
    return _reference_seule(d) is not None and (d.type is None or d.type.lower() in _TYPES_DE_PREAVIS)


def _reference_seule(d: _DocumentDeRecherche) -> str | None:
    """La référence d'Objet d'un document quand elle n'est qu'un numéro (« Objet n° 05-2026 », « 05-2026 »). Le
    numéro d'un préavis est celui de son titre (`_numero`) ; cette référence ne le donne que si le titre n'en porte
    pas (Etoy, La Rippe, Juriens)."""
    m = _OBJET_NUMERO.match(d.objet or "")
    return m["numero"] if m else None


def _numero_de_noeud(d: _DocumentDeRecherche) -> int:
    """Le numéro du nœud Quicksite du document (`/n<id>`), qui croît avec sa mise en ligne."""
    m = _LIEN_NOEUD.search(d.lien)
    return int(m[0][2:]) if m else 0


def _ref(d: _DocumentDeRecherche) -> str | None:
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


def _titre_du_preavis(d: _DocumentDeRecherche, numero: str) -> str:
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


def _parametres_coreapi(texte: str) -> Coreapi | None:
    """La recherche `coreapi` d'une page, telle que `site.coreapi` la déclare, si c'est une vue des documents du
    conseil."""
    section = re.search(r'<section[^>]*class="tplDeepsearch"(.*?)>', texte, re.S)
    projet = _PROJET.search(texte)
    if section is None or projet is None:
        return None
    attrs = dict(re.findall(r'data-elasticsearch-([\w-]+)="([^"]*)"', section[1]))
    if attrs.get("view") not in VUES_DU_CONSEIL or not attrs.get("node", "").isdigit():
        return None
    return Coreapi(
        projet=projet[1],
        vue=attrs["view"],
        noeud=int(attrs["node"]),
        taille=int(attrs.get("pagesize") or 60),
        tri=attrs.get("sort") or "date_extid",
    )


def requetes(pages: PagesLues, source: Source, depuis: date | None) -> int | None:
    """Les requêtes que coûterait la lecture de `source` (`lire`) au passage ordinaire dont la fenêtre part de
    `depuis`. Les pages qui manquent sont lues par le robot du script (une liste Quicksite en demande peu : pages de
    résultats, ou Séances et fiches du module Conseil) ; `None` si la lecture échoue."""
    robot = RobotCompteur(pages.lire)
    try:
        sans_journal(lambda: lire(robot, source, depuis))  # type: ignore[arg-type]
    except (ValueError, PageNonLue):
        return None
    return robot.requetes


# --- Module Conseil (Montreux) ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _SeanceListee:
    """Une Séance de la liste d'un module Conseil : son nom, son jour, son heure s'il la donne, et sa page."""

    nom: str
    jour: date
    heure: str | None  # « 19:30 »
    lien: str | None  # page de la Séance ; `None` pour une Séance annoncée sans page

    def meeting(self, points: list[dict] | None = None, documents: list[dict] | None = None) -> dict:
        """La Séance à la forme d'un *meeting*, avec les points et les documents de sa page."""
        return _meeting(self.nom, self.jour, documents or [], heure=self.heure, lien=self.lien, points=points)


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
            seances.append(ligne.meeting())
            continue
        try:
            page = robot.lire(ligne.lien, "import")
        except PageNonLue as e:
            _journal(source.nom, f"Séance {ligne.lien} non lue ({e})")
            continue
        titre = arbre(page.texte).texte_du_premier(lambda n: n.tag == "h1")
        ligne = _SeanceListee(titre or ligne.nom, ligne.jour, ligne.heure, ligne.lien)  # le nom brut, celui de sa page
        points, documents = [], []
        for point in _points_du_module(page.texte, page.url):
            cite_un_objet = avec_objets and point.fiche is not None
            numero = None
            if cite_un_objet:
                if point.fiche not in fiches:
                    fiches[point.fiche] = _fiche_d_objet(robot, source, point.fiche)
                objet = fiches[point.fiche]
                numero = objet["number"] if objet else None
            points.append({"item_number_display": None, "item_title": point.titre, "item_affair_number": numero})
            if not cite_un_objet:
                # Seuls les documents d'un point sans Objet vont à la Séance. Ceux d'un point dont la fiche ne se lit
                # pas restent à son Objet, qui les retrouvera au passage où elle se relit : à la Séance, l'import, qui
                # garde les documents archivés, les y laisserait pour toujours.
                documents += point.documents
        seances.append(ligne.meeting(points, documents))
    for objet in fiches.values():
        if objet is None or _en_double(source.nom, objets, objet["number"], objet["title"]["fr"], "le premier du site"):
            continue
        objets.append(objet)
    return seances, objets


def _liste_du_module(texte: str, url: str) -> list[_SeanceListee | str]:
    """Les Séances de la liste du module, dans l'ordre du site : l'année en cours (pastilles), puis les années
    précédentes (onglets). Lève `ValueError` pour une page sans liste."""
    racine = arbre(texte)
    bloc = racine.premier(lambda n: "tplCCIBPublicOrdreJour" in n.classes())
    if bloc is None:
        raise ValueError(f"{url} : aucune liste de Séances (tplCCIBPublicOrdreJour)")
    titre = bloc.texte_du_premier(lambda n: n.tag == "h1")
    annee = _ANNEE.search(titre)
    lignes: list[_SeanceListee | str] = []
    for noeud in racine.elements():
        classes = noeud.classes()
        if any(c in classes for c in ("date-past", "date-nextmeeting", "date-future")):
            lignes.append(_pastille(noeud, int(annee[1]) if annee else None, url))
        elif "table-row-body" in classes and any(
            "/ordredujour/" in (a.attr("href") or "") for a in noeud.elements() if a.tag == "a"
        ):
            lignes.append(_ligne_d_annee(noeud, url))
    return lignes


def _pastille(noeud: Noeud, annee: int | None, url: str) -> _SeanceListee | str:
    jour = noeud.texte_du_premier(lambda n: "day" in n.classes())
    mois = noeud.texte_du_premier(lambda n: n.tag == "label")
    if annee is None or not jour.isdigit() or mois.lower() not in _MOIS_COURTS:
        return f"date illisible « {jour} {mois} »"
    try:
        quand = date(annee, _MOIS_COURTS[mois.lower()], int(jour))
    except ValueError:
        return f"date impossible « {jour} {mois} {annee} »"
    lien = noeud.premier(lambda n: n.tag == "a" and "ID=" in (n.attr("href") or ""))
    page = urljoin(url, lien.attr("href") or "") if lien else None
    return _SeanceListee(f"Séance du {_jour_en_lettres(quand)}", quand, None, page)


def _ligne_d_annee(noeud: Noeud, url: str) -> _SeanceListee | str:
    a = next(a for a in noeud.elements() if a.tag == "a" and "/ordredujour/" in (a.attr("href") or ""))
    quand = _date_ecrite(espaces(noeud.texte()))
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
    for carte in (n for n in arbre(texte).elements() if n.tag == "div" and "card" in n.classes()):
        fiche = carte.premier(lambda n: n.tag == "a" and "/documents/recherche/" in (n.attr("href") or ""))
        description = carte.premier(lambda n: "description" in n.classes())
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
    """Les documents (`download.asp?d=<id>`) d'un nœud, chacun une fois, nommés par `_nom_du_document`, sans date
    (la page d'une Séance n'en donne pas)."""
    documents, vus = [], set()
    for a in noeud.elements():
        lien = urljoin(url, a.attr("href") or "") if a.tag == "a" else ""
        if "download.asp?d=" not in lien.lower() or lien in vus:
            continue
        vus.add(lien)
        documents.append({"name": _nom_du_document(a, lien), "url": lien, "date": None, "category": None})
    return documents


# Le texte d'un lien qui ne nomme pas son document : vide, un verbe (« Télécharger »), un format ou une taille.
_PAS_UN_NOM = re.compile(
    r"^(?:t[ée]l[ée]charger(?:\s+le\s+(?:document|fichier))?|download|ouvrir|voir|afficher"
    r"|\(?\s*(?:(?:pdf|docx?|xlsx?|zip)\b[\s,]*)?(?:\d+(?:[.,]\d+)?\s*(?:[kmg]i?b|[kmg]?o)\b)?\s*\)?)$",
    re.I,
)


def _nom_du_document(a: Noeud, lien: str) -> str:
    """Le nom d'un document du module (ADR 0010) : le texte de son lien sans sa taille, sinon, quand ce texte ne le
    nomme pas (vide, « Télécharger », une taille), le nom de son fichier (`title`), sinon la fin de son lien."""
    noms = (_texte_sans_taille(a), a.attr("title") or "")
    return next((nom for nom in noms if not _PAS_UN_NOM.match(nom)), lien.rsplit("=", 1)[-1])


def _texte_sans_taille(a: Noeud) -> str:
    """Le texte d'un lien sans la taille du fichier qui le suit (`span.info-file`, `span.badge`)."""
    morceaux = [
        e if isinstance(e, str) else e.texte()
        for e in a.enfants
        if isinstance(e, str) or not {"info-file", "badge"} & set(e.classes())
    ]
    return espaces(" ".join(morceaux))


def _fiche_d_objet(robot: Robot, source: Source, url: str) -> dict | None:
    """L'Objet de sa fiche, à la forme d'une *affair* ; `None`, noté dans le journal, s'il ne se lit pas ou n'a
    pas de numéro (ses documents ne vont pas pour autant à la Séance)."""
    try:
        page = robot.lire(url, "import")
    except PageNonLue as e:
        _journal(source.nom, f"Objet {url} non lu ({e}), ses documents avec lui")
        return None
    racine = arbre(page.texte)
    bloc = racine.premier(lambda n: "tplDetailBlade" in n.classes()) or racine
    entete = bloc.texte_du_premier(lambda n: n.tag == "h1")
    m = re.match(r"^(?P<type>\D+?)\s+(?:n[°o]\.?\s*)?(?P<numero>\d[\w/.-]*)", entete)
    if m is None:
        _journal(source.nom, f"Objet sans numéro, non importé : {entete or url}")
        return None
    texte = bloc.texte_du_premier(lambda n: n.tag == "h5")
    auteur = re.search(r"Auteur\s*:\s*(.+)", bloc.texte_du_premier(lambda n: n.tag == "small"))
    documents = []
    for ligne in (n for n in bloc.elements() if "table-row-body" in n.classes()):
        lien = ligne.premier(lambda n: n.tag == "a" and "download.asp" in (n.attr("href") or ""))
        if lien is None:
            continue
        colonnes = [espaces(c.texte()) for c in ligne.enfants_elements() if c.tag == "div"]
        jour = next((_date_ecrite(c) for c in reversed(colonnes) if _date_ecrite(c)), None)
        adresse = urljoin(page.url, lien.attr("href") or "")
        documents.append(
            {"name": _nom_du_document(lien, adresse), "url": adresse, "date": jour.isoformat() if jour else None,
             "category": colonnes[-2] if len(colonnes) >= 2 else None}
        )
    contributeurs = []
    if auteur:
        nom = auteur[1].strip()
        groupe = re.match(r"^(municipalit[ée]|commission|bureau|groupe)", nom, re.I) is not None
        contributeurs.append({"type": "organization" if groupe else "person", "fullname": nom})
    dates = [d["date"] for d in documents if d["date"]]
    numero, type_ = m["numero"].rstrip(".,;:"), m["type"].strip()
    depose = min(dates) if dates else None
    return _affair(numero, texte or entete, type_, depose, documents, lien=page.url, contributeurs=contributeurs)


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
        for ligne in (n for n in racine.elements() if "table-row-body" in n.classes()):
            a = ligne.premier(lambda n: n.tag == "a" and n.premier(lambda b: b.tag == "b") is not None)
            if a is None:
                continue
            nom = a.texte_du_premier(lambda b: b.tag == "b")
            prenom = espaces(a.texte())[len(nom) :].strip()
            if nom:
                membres.append(f"{prenom} {nom}".strip())
        suivante = racine.premier(lambda n: n.tag == "a" and n.attr("rel") == "next")
        url = urljoin(page.url, suivante.attr("href") or "") if suivante else None
    return membres


# --- Module Conseil dont la liste est sur le site de la Ville (Vevey) -----------------------------------------------

_ID_DU_MODULE = re.compile(r"/conseilcommunal/seances/\?ID=(\d+)", re.I)
_HOTE = re.compile(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", re.I)


def _module_conseil_externe(robot: Robot, source: Source, depuis: date | None) -> list[dict]:
    """Les Séances de la liste du site de la Ville, chacune avec la page de son ordre du jour sur le module. Une page
    de Séance qui ne se lit pas, ou sans points, est sautée et notée dans le journal ; si aucune de celles à ouvrir ne
    se lit, lève `ValueError` : une refonte du module, que la sonde ne voit pas, ne passe pas en silence."""
    site = source.site
    assert site is not None and site.seances is not None
    liste = robot.lire(site.seances, "import")
    seances = []
    lignes = [n for n in arbre(liste.texte).elements() if "teaser-agenda" in n.classes()]
    illisibles = 0
    pages_a_ouvrir = pages_lues = 0
    for noeud in lignes:
        titre = noeud.texte_du_premier(lambda n: n.tag == "a")
        quand = _date_ecrite(titre)
        if quand is None:
            illisibles += 1
            _journal(source.nom, f"ligne de Séance illisible (sans date : {titre})")
            continue
        if depuis is not None and quand < depuis:
            continue
        heure = _HEURE.search(titre)
        liens = (urljoin(liste.url, a.attr("href") or "") for a in noeud.elements() if a.tag == "a")
        lien = next((p for p in map(_page_du_module, liens) if p), None)
        ligne = _SeanceListee(titre, quand, f"{int(heure[1]):02d}:{heure[2]}" if heure else None, lien)
        if lien is None:
            seances.append(ligne.meeting())
            continue
        pages_a_ouvrir += 1
        try:
            page = robot.lire(lien, "import")
        except PageNonLue as e:
            _journal(source.nom, f"Séance {lien} non lue ({e})")
            continue
        ordre_du_jour = _ordre_du_jour_du_module(page.texte, page.url)
        if ordre_du_jour is None:
            _journal(source.nom, f"Séance {lien} illisible (aucun point centerGroup)")
            continue
        pages_lues += 1
        seances.append(ligne.meeting(*ordre_du_jour))
    if lignes and illisibles == len(lignes):
        raise ValueError(f"{liste.url} : aucune ligne de Séance lisible")
    if pages_a_ouvrir and not pages_lues:
        raise ValueError(f"{liste.url} : aucune des {pages_a_ouvrir} pages de Séance du module ne se lit")
    return seances


def _page_du_module(lien: str) -> str | None:
    """La page de l'ordre du jour sur le module d'un lien de la liste (`…/conseilcommunal/seances/?ID=<id>`), récrite
    vers `https://<hôte du module>/ConseilCommunal/seances/?ID=<id>`, à la casse que `robots.txt` autorise ; `None`
    pour un autre lien. L'hôte du module est celui du lien, ou, pour un lien cassé qui le met en tête de son chemin
    (`www.vevey.ch/conseil.vevey.ch/conseilcommunal/…`), ce premier segment."""
    ordre = _ID_DU_MODULE.search(lien)
    if ordre is None:
        return None
    parties = urlsplit(lien)
    premier = parties.path.split("/")[1]
    hote = premier if _HOTE.fullmatch(premier) else parties.hostname
    return f"https://{hote}/ConseilCommunal/seances/?ID={ordre[1]}"


def _ordre_du_jour_du_module(texte: str, url: str) -> tuple[list[dict], list[dict]] | None:
    """Les points numérotés de l'ordre du jour d'une Séance du module (« 9. », « 9.1 »), et ses documents ; `None`
    pour une page sans points (`div.centerGroup`)."""
    groupes = [n for n in arbre(texte).elements() if "centerGroup" in n.classes()]
    if not groupes:
        return None
    points, documents = [], []
    for groupe in groupes:
        numero = groupe.texte_du_premier(lambda n: "number" in n.classes()).rstrip(".")
        titre = groupe.texte_du_premier(lambda n: "title" in n.classes())
        sous = [n for n in groupe.elements() if n.tag == "li"]
        if not sous:
            points.append({"item_number_display": numero or None, "item_title": titre, "item_affair_number": None})
        for li in sous:
            num = li.texte_du_premier(lambda n: "theme-num" in n.classes())
            sujet = li.texte_du_premier(lambda n: "theme" in n.classes())
            points.append({"item_number_display": num or None, "item_title": sujet, "item_affair_number": None})
        documents += _documents_du_module(groupe, url)
    return points, documents

