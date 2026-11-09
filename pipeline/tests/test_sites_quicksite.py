"""Les communes Quicksite dans le passage du cron (spec de J3, « Les plateformes ») : déclarées dans un `sources.json`
de test, lues par le robot communal sur l'échantillon enregistré (`echantillon-sites/quicksite/`), archivées comme
les autres conseils. Le seul seam est le passage du cron (`passage_sites._passer`) ; les cas instables sont fabriqués
par de petites retouches de l'échantillon.

Variante ancienne génération : Aigle (bibliothèque des documents, page après page). Variante `coreapi` : Founex (vue `documentconseildates`, documents groupés par Séance) et Ropraz (vue
`documentconseil`, une Séance par document, dont les fausses « Séance du 1 janvier ») ; Ropraz déclarée avec deux
recherches, comme Duillier et Juriens, qui séparent leurs préavis et leurs procès-verbaux.
"""

import re
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau, echantillon
from lecture_quicksite import PAGES_MAX
from passage_sites import T0, _lire, _opendata, _passer
from schema import FichierSources

FOUNEX = "https://www.founex.ch"
ROPRAZ = "https://www.ropraz.ch"
RESEAU_QUICKSITE = "193.34.137.65"

PLATEFORMES = [
    {
        "id": "quicksite",
        "nom": "Quicksite",
        "editeur": "eAdmin Solutions SA",
        "variantes": [
            {"id": "ancienne", "marqueur": "tplListDocumentSummary", "niveaux": [["seances"], ["preavis", "seances"]]},
            {"id": "coreapi", "marqueur": "tplDeepsearch", "niveaux": [["seances"], ["preavis", "seances"]]},
            {"id": "conseil", "marqueur": "tplCCIBPublicOrdreJour", "niveaux": [["seances"], ["objets", "seances"]]},
            {"id": "conseil-externe", "marqueur": "teaser-agenda", "niveaux": [["seances"]]},
        ],
    }
]


def _quicksite(
    ofs,
    commune,
    seances,
    coreapi=None,
    donne=("preavis", "seances"),
    conseil="Conseil communal",
    variante="coreapi",
    membres=None,
):
    site = {"plateforme": "quicksite", "variante": variante, "seances": seances}
    site |= {"membres": membres} if membres else {}
    return {
        "id": f"site-{ofs}",
        "nom": f"{conseil} de {commune} (site de la commune)",
        "nom_court": f"Site de {commune}",
        "attribution": {
            "texte": f"Commune de {commune}",
            "lien": seances,
            "licence": "Actes officiels (art. 5 LDA) : métadonnées et liens seulement",
        },
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "scrape"},
        "conseil": {"body_key": str(ofs), "donne": list(donne)},
        "site": site | ({"coreapi": coreapi} if coreapi else {}),
    }


def _founex(**options):
    return _quicksite(
        5717,
        "Founex",
        f"{FOUNEX}/N640/documents.html",
        {"projet": "founex25", "vue": "documentconseildates", "noeud": 640, "taille": 60, "tri": "date_extid"},
        **options,
    )


def _ropraz(**options):
    return _quicksite(
        5798,
        "Ropraz",
        f"{ROPRAZ}/documents-du-conseil",
        {"projet": "ropraz26", "vue": "documentconseil", "noeud": 748, "taille": 200, "tri": "date_extid_desc_rank"},
        conseil="Conseil général",
        **options,
    )


def _sources(*sources):
    return FichierSources.model_validate({"plateformes": PLATEFORMES, "sources": [_opendata("5586"), *sources]})


def _recherche(reseau, hote):
    """L'URL de la première page de résultats de la recherche de `hote`, telle que l'échantillon l'a enregistrée."""
    return next(u for u in reseau.pages if u.startswith(hote) and "/coreapi/" in u)


def _page_suivante(url, page):
    return f"{url}&page={page}"


def _reseau(horloge):
    adresses = {"www.founex.ch": RESEAU_QUICKSITE, "www.ropraz.ch": RESEAU_QUICKSITE, "www.aigle.ch": "185.54.6.109"}
    reseau = Reseau(horloge, adresses=adresses)
    reseau.pages |= echantillon("quicksite", "coreapi") | echantillon("quicksite", "coreapi-documentconseil")
    reseau.pages |= echantillon("quicksite", "ancienne")
    reseau.adresses |= {"www.conseilmontreux.ch": "185.54.6.110", "www.vevey.ch": "5.102.146.10"}
    reseau.adresses |= {"conseil.vevey.ch": "5.102.146.20"}
    reseau.pages |= echantillon("quicksite", "conseil") | echantillon("quicksite", "conseil-externe")
    return reseau


def _fragment(seances, fin, total):
    """Une page de résultats de la vue `documentconseildates`, à la forme de celle de Founex : `seances` donne, pour
    chaque Séance, son libellé et ses documents (nœud, titre)."""
    groupes = "".join(
        f'<div class="accordion-item"><h2><button>{libelle}</button></h2><div class="container">'
        + "".join(
            f'<div class="qs-edit qs-edit-in" data-qsedit data-qsedit-editnode="{n}"><div class="col">'
            f'<a href="{FOUNEX}/n{n}" class="d-block"><h6>{titre}</h6></a></div></div>'
            for n, titre in documents
        )
        + "</div></div>"
        for libelle, documents in seances
    )
    return Page(
        f'<div class="tplDocumentConseil"><div class="col">{fin - 59} à {fin} sur {total} éléments trouvés</div>'
        f'<div class="accordion" id="accordion-docs">{groupes}</div></div>'
    )


def _founex_en_trois_pages(reseau):
    """La recherche de Founex en trois pages de 60 : la première est l'échantillon (de la Séance à venir du 9 novembre
    au 15 juin), la deuxième va du 20 avril au 2 mars, avant la fenêtre, la troisième remonte à 2025."""
    url = _recherche(reseau, FOUNEX)
    page = reseau.pages[url]
    reseau.pages[url] = Page(page.corps.replace(b"sur 399", b"sur 180"), entetes=page.entetes)
    reseau.pages[_page_suivante(url, 2)] = _fragment(
        [
            ("Séance du 20 avril 2026", [(1874, "Ordre du jour du 20 avril 2026")]),
            ("Séance du 2 mars 2026", [(1776, "Ordre du jour du 02.03.2026")]),
        ],
        120,
        180,
    )
    reseau.pages[_page_suivante(url, 3)] = _fragment(
        [("Séance du 8 décembre 2025", [(1700, "Ordre du jour du 08.12.2025")])], 180, 180
    )
    return url


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_une_commune_coreapi_archive_ses_seances_avec_leurs_documents_sans_lien_propre(tmp_path, horloge):
    reseau = _reseau(horloge)
    _founex_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_founex()))

    seance = _lire(tmp_path, "conseils/5717/seances/2026-11-09.json")
    del seance["genere"]
    assert seance == {
        "version": 1,
        "id": None,
        "date": "2026-11-09",
        "nom": "Séance du 9 novembre 2026",
        "lien": None,
        "ordre_du_jour": [],
        "documents": [
            {"titre": "Ordre du Jour du 09.11.2026", "date": None, "lien": f"{FOUNEX}/n2227"},
            {"titre": "Procès-verbal du 28.09.2026", "date": None, "lien": f"{FOUNEX}/n2228"},
            {"titre": "Préavis 005_2026-2031", "date": None, "lien": f"{FOUNEX}/n2229"},
        ],
    }
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5717/seances.json")["seances"]] == [
        "5717/2026-11-09",
        "5717/2026-09-28",
        "5717/2026-06-15",
    ]


def test_les_preavis_d_une_commune_coreapi_sont_archives_avec_leur_numero_brut_et_leur_objet(tmp_path, horloge):
    reseau = _reseau(horloge)
    _founex_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_founex()))

    objet = _lire(tmp_path, "conseils/5717/objets/005_2026-2031.json")
    del objet["genere"]
    assert objet == {
        "version": 1,
        "id": None,
        "numero": "005_2026-2031",
        "titre": "Demande de crédit de CHF 114'000.00 pour le déplacement des armoires de contrôle de l'éclairage "
        "public des stations Romande Energie",
        "type": "Préavis",
        "statut": None,
        "depose": "2026-11-09",
        "lien": None,
        "contributeurs": [],
        "etapes": [],
        "documents": [{"titre": "Préavis 005_2026-2031", "date": None, "lien": f"{FOUNEX}/n2229"}],
        "communes": [],
    }
    # Le numéro est celui du titre, tel quel : le préavis 072 de la législature passée revient au 15 juin sous une
    # autre écriture, et les plans qui citent le même Objet lui sont joints.
    plans = _lire(tmp_path, "conseils/5717/objets/072-2021-2026.json")
    assert [d["titre"] for d in plans["documents"]] == ["Préavis 072/2021-2026", "Plans Port de Founex _Préavis 072"]
    assert plans["depose"] == "2026-06-15"
    assert sorted(p.name for p in (tmp_path / "conseils/5717/objets").iterdir()) == [
        "001_2026-2031.json",
        "005_2026-2031.json",
        "072-2021-2026.json",
        "072_2021-2026.json",
    ]


def test_le_passage_ordinaire_lit_toute_la_recherche_mais_n_importe_que_la_fenetre(tmp_path, horloge):
    # La recherche n'est pas triée par mise en ligne : un document d'une Séance de la fenêtre peut être sur n'importe
    # quelle page. Elle est donc lue en entier chaque jour, comme toute page de liste (spec, « Fenêtre »).
    reseau = _reseau(horloge)
    url = _founex_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_founex()))

    lues = [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal]
    assert lues == [
        (f"{FOUNEX}/robots.txt", "VigieVaud-sonde"),
        (f"{FOUNEX}/N640/documents.html", "VigieVaud-sonde"),  # la page vide, sondée, jamais importée
        (url, "VigieVaud-import"),
        (_page_suivante(url, 2), "VigieVaud-import"),
        (_page_suivante(url, 3), "VigieVaud-import"),
    ]
    # Le 20 avril, le 2 mars et décembre 2025, avant la fenêtre (23 avril), ne sont pas importés.
    assert not (tmp_path / "conseils/5717/seances/2026-04-20.json").exists()
    assert not (tmp_path / "conseils/5717/seances/2025-12-08.json").exists()
    heures = reseau.heures("www.founex.ch")
    assert all(b - a >= timedelta(seconds=5) for a, b in zip(heures, heures[1:]))


def test_un_preavis_de_la_fenetre_garde_ses_documents_anciens_d_une_page_suivante(tmp_path, horloge):
    # Rolle, le 8 novembre : un préavis de 2021 revient en 2026 (sa clôture) ; son rapport de 2021 est sur une page de
    # résultats plus loin. Le passage ordinaire qui suit le rattrapage ne doit pas le lui retirer.
    reseau = _reseau(horloge)
    url = _recherche(reseau, ROPRAZ)
    reseau.pages[url] = Page(
        '<div class="tplDocumentConseil"><div>1 à 1 sur 2 éléments trouvés</div>'
        + _document_par_type(901, "Clôture du préavis 9", "Préavis", "Objet n° 2021-2026-9", "16 juin 2026")
        + "</div>"
    )
    reseau.pages[_page_suivante(url, 2)] = Page(
        '<div class="tplDocumentConseil"><div>2 à 2 sur 2 éléments trouvés</div>'
        + _document_par_type(902, "Rapport de la commission des finances", "Rapport", "Objet n° 2021-2026-9",
                             "14 décembre 2021")
        + "</div>"
    )
    sources = _sources(_ropraz())
    _passer(tmp_path, horloge, reseau, sources, rattrapage_cible="5798")

    _passer(tmp_path, horloge, reseau, sources, heure=T0 + timedelta(days=1))

    documents = _lire(tmp_path, "conseils/5798/objets/2021-2026-9.json")["documents"]
    assert [d["lien"] for d in documents] == [f"{ROPRAZ}/n901", f"{ROPRAZ}/n902"]


def test_un_document_que_le_site_ne_montre_plus_reste_a_sa_seance(tmp_path, horloge):
    # Oron, entre deux lectures : un document à égalité de tri change de page et n'est pas vu. L'archive le garde.
    reseau = _reseau(horloge)
    _founex_en_trois_pages(reseau)
    sources = _sources(_founex())
    _passer(tmp_path, horloge, reseau, sources)
    url = _recherche(reseau, FOUNEX)
    page = reseau.pages[url]
    reseau.pages[url] = Page(re.sub(rb'href="https://www.founex.ch/n2228"', b'href="#"', page.corps), entetes=page.entetes)

    _passer(tmp_path, horloge, reseau, sources, heure=T0 + timedelta(days=1))

    liens = [d["lien"] for d in _lire(tmp_path, "conseils/5717/seances/2026-11-09.json")["documents"]]
    assert liens == [f"{FOUNEX}/n2227", f"{FOUNEX}/n2229", f"{FOUNEX}/n2228"]


def test_le_rattrapage_lit_toutes_les_pages_de_resultats(tmp_path, horloge):
    reseau = _reseau(horloge)
    url = _founex_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_founex()), rattrapage_cible="quicksite")

    assert _page_suivante(url, 3) in [r.url for r in reseau.journal]
    assert _lire(tmp_path, "conseils/5717/seances/2025-12-08.json")["documents"][0]["lien"] == f"{FOUNEX}/n1700"
    assert (tmp_path / "conseils/5717/seances/2026-03-02.json").exists()


def test_une_pagination_sans_fin_est_tronquee_au_garde_fou_et_notee_dans_le_journal(tmp_path, horloge, capsys):
    # Une recherche qui annonce toujours plus de documents qu'elle n'en a donné : le rattrapage, sans plafond de
    # requêtes, la lit jusqu'au garde-fou, bien au-delà des quelques dizaines de pages d'un historique réel, et le
    # journal dit que la liste est tronquée.
    reseau = _reseau(horloge)
    url = _recherche(reseau, ROPRAZ)
    for page in range(1, PAGES_MAX + 2):
        reseau.pages[url if page == 1 else _page_suivante(url, page)] = Page(
            f'<div class="tplDocumentConseil"><div>{page} à {page} sur 999999 éléments trouvés</div>'
            + _document_par_type(10000 + page, f"Document {page}")
            + "</div>"
        )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()), rattrapage_cible="5798")

    lues = [r.url for r in reseau.journal if "/coreapi/" in r.url]
    assert len(lues) == PAGES_MAX > 200
    assert _page_suivante(url, PAGES_MAX + 1) not in lues
    assert f"élément sauté, liste tronquée : {PAGES_MAX} pages lues sans en voir la fin" in capsys.readouterr().err
    assert "5798" in _lire(tmp_path, "conseils/import.json")["conseils"]


def test_une_recherche_qui_ignore_la_page_demandee_s_arrete_a_la_page_qui_ne_donne_rien_de_nouveau(tmp_path, horloge):
    reseau = _reseau(horloge)
    url = _founex_en_trois_pages(reseau)
    reseau.pages[_page_suivante(url, 2)] = reseau.pages[url]

    _passer(tmp_path, horloge, reseau, _sources(_founex()), rattrapage_cible="quicksite")

    assert [r.url for r in reseau.journal if "/coreapi/" in r.url] == [url, _page_suivante(url, 2)]
    liens = [d["lien"] for d in _lire(tmp_path, "conseils/5717/seances/2026-11-09.json")["documents"]]
    assert liens == [f"{FOUNEX}/n2227", f"{FOUNEX}/n2228", f"{FOUNEX}/n2229"]  # chacun une fois


def test_une_commune_coreapi_en_seances_seulement_n_importe_aucun_preavis(tmp_path, horloge):
    reseau = _reseau(horloge)
    _founex_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_founex(donne=("seances",))))

    assert (tmp_path / "conseils/5717/seances/2026-09-28.json").exists()
    assert not (tmp_path / "conseils/5717/objets").exists()


def test_une_fausse_seance_du_1er_janvier_est_importee_telle_quelle_avec_ses_preavis(tmp_path, horloge):
    # Ropraz range les préavis d'une année sous une « Séance du 1 janvier » : le rattrapage la garde telle quelle.
    reseau = _reseau(horloge)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()), rattrapage_cible="5798")

    seance = _lire(tmp_path, "conseils/5798/seances/2025-01-01.json")
    assert seance["nom"] == "Séance du 1 janvier 2025"
    # Dans l'ordre de leurs nœuds (794, 804, 805), celui de leur mise en ligne.
    assert [(d["titre"], d["date"]) for d in seance["documents"]] == [
        ("Préavis 01/2025", "2025-01-01"),
        ("Préavis 06/2025", "2025-01-01"),
        ("Décision", "2025-01-01"),
    ]
    preavis = _lire(tmp_path, "conseils/5798/objets/06-2025.json")
    assert (preavis["numero"], preavis["titre"], preavis["depose"]) == ("06/2025", "Préavis 06/2025", "2025-01-01")
    # « Preavis_04.2024_Budget 2025.pdf », un nom de fichier, n'est pas un préavis : il reste un document de sa Séance.
    avril = _lire(tmp_path, "conseils/5798/seances/2026-04-23.json")
    assert [d["titre"] for d in avril["documents"]] == ["Preavis_04.2024_Budget 2025.pdf"]
    assert sorted(p.name for p in (tmp_path / "conseils/5798/objets").iterdir()) == ["01-2025.json", "06-2025.json"]


def test_au_passage_ordinaire_ropraz_ne_garde_que_la_seance_de_la_fenetre(tmp_path, horloge):
    reseau = _reseau(horloge)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5798/seances.json")["seances"]] == ["5798/2026-04-23"]


def test_un_preavis_sans_numero_n_est_pas_importe_et_un_document_illisible_est_saute(tmp_path, horloge, capsys):
    reseau = _reseau(horloge)
    url = _founex_en_trois_pages(reseau)
    page = reseau.pages[url]
    corps = page.corps.decode("utf-8")
    corps = corps.replace("Préavis 001_2026-2031", "Préavis du Conseil", 1)  # sans numéro
    corps = re.sub(r'href="https://www.founex.ch/n2190"', 'href="#"', corps)  # ordre du jour sans lien
    reseau.pages[url] = Page(corps, entetes=page.entetes)

    _passer(tmp_path, horloge, reseau, _sources(_founex()))

    journal = capsys.readouterr().err
    assert "Conseil communal de Founex (site de la commune) : élément sauté, Objet sans numéro, non importé" in journal
    assert "document illisible (sans lien vers le document : Ordre du Jour du 28 septembre 2026)" in journal
    assert not (tmp_path / "conseils/5717/objets/001_2026-2031.json").exists()
    titres = [d["titre"] for d in _lire(tmp_path, "conseils/5717/seances/2026-09-28.json")["documents"]]
    assert "Préavis du Conseil" in titres and "Ordre du Jour du 28 septembre 2026" not in titres
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5717"] == "2026-10-23T05:17:05Z"


def _document_par_type(n, titre, type_="", objet="", publie="", seance=""):
    """Un document de la vue `documentconseil`, à la forme de ceux de La Rippe et de Mollens : sans Séance, sauf
    `seance`, donnée comme Ropraz la donne."""
    filtres = f'<a href="javascript:;" data-filter-type="t" data-filter-value="x">{type_}</a>'
    if objet:
        filtres += f'<a href="javascript:;" data-filter-type="ext_id" data-filter-value="{objet}">{objet}</a>'
    if seance:
        filtres += f'<a href="javascript:;" data-filter-type="sortdate" data-filter-value="1">{seance}</a>'
    return (
        f'<div class="qs-edit qs-edit-top qs-edit-out" data-qsedit data-qsedit-editnode="{n}"><div class="col">'
        f'{filtres}<a href="{ROPRAZ}/n{n}"><h5>{titre}</h5></a></div>'
        + (f'<div class="col-auto"><small>Publié le {publie}</small></div>' if publie else "")
        + "</div>"
    )


def test_une_vue_sans_seances_donne_ses_preavis_par_objet_et_ses_seances_par_les_titres_des_proces_verbaux(
    tmp_path, horloge
):
    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil"><div>1 à 3 sur 3 éléments trouvés</div>'
        + _document_par_type(901, "Délégations de compétences", "", "Objet n° 05-2026", "6 octobre 2026")
        + _document_par_type(902, "Comptes communaux 2025", "Préavis", "Objet n° 04-2026", "24 août 2026")
        + _document_par_type(903, "Procès verbal de la séance du 23 juin 2026")
        + "</div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    preavis = _lire(tmp_path, "conseils/5798/objets/05-2026.json")
    assert (preavis["numero"], preavis["titre"], preavis["depose"]) == ("05-2026", "Délégations de compétences", "2026-10-06")
    assert (tmp_path / "conseils/5798/objets/04-2026.json").exists()
    seance = _lire(tmp_path, "conseils/5798/seances/2026-06-23.json")
    assert (seance["nom"], [d["lien"] for d in seance["documents"]]) == ("Séance du 23 juin 2026", [f"{ROPRAZ}/n903"])
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5798/seances.json")["seances"]] == ["5798/2026-06-23"]


def test_la_vue_par_annees_donne_la_seance_de_son_en_tete_et_le_preavis_de_sa_reference(tmp_path, horloge):
    # La vue `documentconseilyears` d'Etoy : un en-tête par Séance, puis ses documents, titrés par leur lien ; le
    # préavis n'a pas de numéro dans son titre, ses rapport et décision partagent sa référence d'Objet.
    def document(n, titre, type_, reference):
        return (
            f'<div class="qs-edit qs-edit-top qs-edit-out" data-qsedit data-qsedit-editnode="{n}">'
            f'<a href="{ROPRAZ}/n{n}" class="link-dark"><i class="fal"></i></a><div class="col-auto">28.09.2026</div>'
            f'<a href="javascript:;" data-filter-type="ext_id" data-filter-value="{reference}">{reference}</a>'
            f'<a href="{ROPRAZ}/n{n}" class="d-block mb-1">{titre}</a>'
            f'<a href="javascript:;" class="badge" data-filter-type="t" data-filter-value="x">{type_}</a></div>'
        )

    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil">1 à 3 sur 3 éléments trouvés<div class="tab-pane" id="nav-2026">'
        '<div id="search-standard-result"><div class="mt-3"><div class="bg-light">Séance du 28 septembre 2026</div></div>'
        + document(1907, "Préavis relatif à l'arrêté d'imposition pour 2027", "Préavis", "04-2026")
        + document(1908, "Rapport de la Commission des Finances", "Rapport", "04-2026")
        + document(1909, "Décision au préavis 04-2026", "Décision", "04-2026")
        + "</div></div></div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    preavis = _lire(tmp_path, "conseils/5798/objets/04-2026.json")
    assert (preavis["titre"], preavis["depose"]) == ("Préavis relatif à l'arrêté d'imposition pour 2027", "2026-09-28")
    assert [d["lien"] for d in preavis["documents"]] == [f"{ROPRAZ}/n1907", f"{ROPRAZ}/n1908", f"{ROPRAZ}/n1909"]
    seance = _lire(tmp_path, "conseils/5798/seances/2026-09-28.json")
    assert [d["titre"] for d in seance["documents"]][0] == "Préavis relatif à l'arrêté d'imposition pour 2027"
    assert sorted(p.name for p in (tmp_path / "conseils/5798/objets").iterdir()) == ["04-2026.json"]


def test_le_numero_d_un_preavis_garde_son_annee_et_un_rapport_n_est_pas_un_preavis(tmp_path, horloge):
    # Jouxtens-Mézery numérote « N°3 /2023 », Mies écrit le nom du fichier (« 01-2026-Comptes 2025.pdf ») ; à Oron,
    # le rapport de la commission, sans type, cite l'Objet de son préavis.
    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil"><div>1 à 4 sur 4 éléments trouvés</div>'
        + _document_par_type(901, "Rapport de la Commission ad hoc", "", "Objet n° 11-2026", "6 octobre 2026")
        + _document_par_type(902, "Préavis N°3 /2026: Demande de crédit", "Préavis", "", "6 octobre 2026")
        + _document_par_type(903, "Préavis N°3 /2025: Comptes", "Préavis", "", "6 octobre 2026")
        + _document_par_type(904, "Préavis 01-2026-Comptes 2025.pdf", "Préavis", "", "6 octobre 2026")
        + "</div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    numeros = sorted(_lire(tmp_path, f"conseils/5798/objets/{p.name}")["numero"]
                     for p in (tmp_path / "conseils/5798/objets").iterdir())
    assert numeros == ["01-2026", "3 /2025", "3 /2026"]


def test_un_rapport_que_le_site_type_preavis_n_est_pas_un_preavis_et_reste_a_sa_seance(tmp_path, horloge):
    # Pompaples type « Préavis » le rapport de minorité d'un préavis, avec sa propre référence d'Objet : il ne devient
    # pas l'Objet « 12-2025-2-b », et reste un document de sa Séance.
    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil">1 à 2 sur 2 éléments trouvés<div id="search-standard-result">'
        '<div class="bg-light">Séance du 6 octobre 2026</div>'
        + _document_par_type(901, "Préavis 12-2025-2 - Patinoire", "Préavis", "Objet n° 12-2025-2")
        + _document_par_type(902, "Rapport de minorité - Préavis 12-2025-2", "Préavis", "Objet n° 12-2025-2-b")
        + "</div></div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert sorted(p.name for p in (tmp_path / "conseils/5798/objets").iterdir()) == ["12-2025-2.json"]
    seance = _lire(tmp_path, "conseils/5798/seances/2026-10-06.json")
    assert [d["lien"] for d in seance["documents"]] == [f"{ROPRAZ}/n901", f"{ROPRAZ}/n902"]


@pytest.mark.parametrize(
    ("titre", "type_", "preavis"),
    [
        # Typé « Préavis » : une commune qui titre ses préavis par leur sujet les garde tous ; seuls les rapports d'une
        # commission, de sa minorité ou de sa majorité sont écartés.
        ("Réponse de la Municipalité au postulat sur les pistes cyclables", "Préavis", True),
        ("Plan d'affectation communal", "Préavis", True),
        ("Rapport de la Municipalité sur la motion des pistes cyclables", "Préavis", True),
        ("Décision d'octroi d'un crédit", "Préavis", True),
        ("Rapport de gestion 2025", "Préavis", True),
        ("Rapport de la Commission des finances", "Préavis", False),
        ("Rapport de majorité", "Préavis", False),
        ("Rapport COFIN", "Préavis", False),
        # Sans type : ni un rapport, ni une annexe, ni un plan…, le `_` d'un nom de fichier finissant le mot.
        ("Délégations de compétences", "", True),
        ("Planification financière 2026-2030", "", True),
        ("Rapport de gestion 2025", "", False),
        ("Rapport_commission_finances", "", False),
        ("Annexe_1_plan_situation", "", False),
        ("Plan_de_quartier", "", False),
        # Un titre « Préavis … » sans numéro ne prend celui de sa référence que s'il a le type d'un préavis.
        ("Préavis relatif à l'arrêté d'imposition", "Préavis", True),
        ("Préavis de la commission des finances", "Rapport", False),
    ],
)
def test_ce_qui_est_un_preavis_quand_il_cite_son_objet_par_un_numero_seul(tmp_path, horloge, titre, type_, preavis):
    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil"><div>1 à 1 sur 1 éléments trouvés</div>'
        + _document_par_type(901, titre, type_, "Objet n° 11-2026", "6 octobre 2026")
        + "</div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert (tmp_path / "conseils/5798/objets/11-2026.json").exists() is preavis


def test_deux_preavis_de_meme_numero_donnent_le_meme_objet_quel_que_soit_l_ordre_du_site(tmp_path, horloge, capsys):
    # Lully : « 00-2026 » pour les comptes et pour la gestion, que la recherche range tantôt dans un ordre, tantôt
    # dans l'autre. Le plus ancien (le plus petit nœud) l'emporte, chaque jour, et le journal nomme l'un et l'autre.
    reseau = _reseau(horloge)
    url = _recherche(reseau, ROPRAZ)
    comptes = _document_par_type(1493, "Comptes 2025", "Préavis", "Objet n° 00-2026", "6 octobre 2026")
    gestion = _document_par_type(1489, "Rapport de gestion 2025", "Préavis", "Objet n° 00-2026", "6 octobre 2026")
    sources = _sources(_ropraz())
    for jour, documents in enumerate((comptes + gestion, gestion + comptes)):
        reseau.pages[url] = Page(f'<div class="tplDocumentConseil"><div>1 à 2 sur 2 éléments trouvés</div>{documents}</div>')
        _passer(tmp_path, horloge, reseau, sources, heure=T0 + timedelta(days=jour))
        assert _lire(tmp_path, "conseils/5798/objets/00-2026.json")["titre"] == "Rapport de gestion 2025"
        assert (
            "Objet 00-2026 en double, le plus ancien gardé (« Rapport de gestion 2025 ») : Comptes 2025"
            in capsys.readouterr().err
        )


def test_une_recherche_vide_est_un_import_reussi_sans_seance(tmp_path, horloge):
    # Un conseil général qui n'a encore rien publié : « 0 éléments trouvés » n'est pas un échec.
    reseau = _reseau(horloge)
    reseau.pages[_recherche(reseau, ROPRAZ)] = Page(
        '<div class="tplDocumentConseil"><div class="col">0 à 0 sur 0 éléments trouvés</div></div>'
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5798"] == "2026-10-23T05:17:05Z"
    assert _lire(tmp_path, "conseils/5798/seances.json")["seances"] == []


def test_une_recherche_dont_aucun_document_ne_se_lit_met_l_import_en_echec(tmp_path, horloge, capsys):
    reseau = _reseau(horloge)
    url = _recherche(reseau, ROPRAZ)
    page = reseau.pages[url]
    reseau.pages[url] = Page(re.sub(rb'href="https://www.ropraz.ch/n\d+"', b'href="#"', page.corps), entetes=page.entetes)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert "Import en échec : Conseil général de Ropraz (site de la commune)" in capsys.readouterr().err
    assert "5798" not in _lire(tmp_path, "conseils/import.json")["conseils"]


def test_une_refonte_sans_section_de_recherche_est_un_marqueur_absent(tmp_path, horloge):
    reseau = _reseau(horloge)
    reseau.pages[f"{ROPRAZ}/documents-du-conseil"] = Page("<html><body><h1>Documents du Conseil</h1></body></html>")

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    assert _lire(tmp_path, "etat-sources.json")["sources"]["site-5798"]["motif"] == "marqueur absent"
    assert not any("/coreapi/" in r.url for r in reseau.journal)  # import sauté


def test_un_second_passage_coreapi_ne_reecrit_rien(tmp_path, horloge):
    reseau = _reseau(horloge)
    _founex_en_trois_pages(reseau)
    sources = _sources(_founex(), _ropraz())
    _passer(tmp_path, horloge, reseau, sources)
    avant = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}

    _passer(tmp_path, horloge, reseau, sources, heure=T0 + timedelta(days=1))

    apres = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}
    assert apres == avant


def test_la_recherche_est_demandee_avec_les_parametres_declares(tmp_path, horloge):
    reseau = _reseau(horloge)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz()))

    (recherche,) = [urlsplit(r.url) for r in reseau.journal if "/coreapi/" in r.url]
    assert recherche.path == "/coreapi/elasticsearch/projects/ropraz26/documentconseil/search"
    parametres = parse_qs(recherche.query, keep_blank_values=True)
    assert (parametres["elasticsearchNode"], parametres["elasticsearchPagesize"]) == (["748"], ["200"])
    assert parametres["elasticsearchSort"] == ["date_extid_desc_rank"]


# --- Deux recherches : préavis et procès-verbaux séparés (Duillier, Juriens) -------------------------------------


def _ropraz_en_deux_recherches(**options):
    """Ropraz déclarée comme Duillier et Juriens, qui séparent leurs préavis et leurs procès-verbaux : la recherche de
    l'échantillon (nœud 748) pour ses préavis, une seconde (nœud 749, 60 par page) pour ses procès-verbaux."""
    ropraz = _ropraz(**options)
    preavis = ropraz["site"]["coreapi"]
    ropraz["site"]["coreapi"] = [preavis, {**preavis, "noeud": 749, "taille": 60, "tri": "date_extid"}]
    return ropraz


def _deux_recherches(reseau):
    """Les URL des deux recherches de Ropraz : celle de l'échantillon, et la seconde, sur le nœud 749."""
    preavis = _recherche(reseau, ROPRAZ)
    proces_verbaux = (
        preavis.replace("=748&", "=749&").replace("Pagesize=200", "Pagesize=60").replace("_desc_rank", "")
    )
    return preavis, proces_verbaux


def _resultats(debut, fin, total, *documents):
    """Une page de résultats de la vue `documentconseil`, avec sa position dans le total."""
    return Page(
        f'<div class="tplDocumentConseil"><div>{debut} à {fin} sur {total} éléments trouvés</div>'
        + "".join(documents)
        + "</div>"
    )


def _duillier(reseau):
    """Les deux recherches de Ropraz, à la forme de celles de Duillier le 9 novembre 2026 : ses préavis, sans Séance,
    datés de leur mise en ligne, et ses procès-verbaux, chacun sous sa Séance."""
    preavis, proces_verbaux = _deux_recherches(reseau)
    reseau.pages[preavis] = _resultats(
        1, 3, 3,
        _document_par_type(1479, "Préavis 10-2026 Indemnités", "Préavis", "10-2026", "4 septembre 2026"),
        _document_par_type(1456, "Préavis 03-2026 Gestion et comptes 2025", "Préavis", "03-2026", "9 juin 2026"),
        _document_par_type(1455, "Rapport sur la gestion et les comptes 2025", "Rapport", "03-2026", "9 juin 2026"),
    )
    reseau.pages[proces_verbaux] = _resultats(
        1, 3, 3,
        _document_par_type(1483, "Extrait des décisions", "Extrait de décisions", "", "24 septembre 2026",
                           "Séance du 24 septembre 2026"),
        _document_par_type(1458, "Procès-verbal", "Procès-verbal", "", "18 juin 2026", "Séance du 18 juin 2026"),
        _document_par_type(1443, "Procès-verbal", "Procès-verbal", "", "26 mars 2026", "Séance du 26 mars 2026"),
    )
    return preavis, proces_verbaux


def test_une_commune_qui_separe_ses_preavis_et_ses_proces_verbaux_lit_ses_deux_recherches(tmp_path, horloge):
    reseau = _reseau(horloge)
    preavis, proces_verbaux = _duillier(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz_en_deux_recherches()))

    assert [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal] == [
        (f"{ROPRAZ}/robots.txt", "VigieVaud-sonde"),
        (f"{ROPRAZ}/documents-du-conseil", "VigieVaud-sonde"),  # la page des préavis, seule sondée
        (preavis, "VigieVaud-import"),
        (proces_verbaux, "VigieVaud-import"),
    ]
    heures = reseau.heures("www.ropraz.ch")
    assert all(b - a >= timedelta(seconds=5) for a, b in zip(heures, heures[1:]))
    # Les Séances viennent des procès-verbaux, celles de la fenêtre seulement (le 26 mars en est hors) ; les préavis,
    # sans Séance, de la recherche des préavis.
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5798/seances.json")["seances"]] == [
        "5798/2026-09-24",
        "5798/2026-06-18",
    ]
    seance = _lire(tmp_path, "conseils/5798/seances/2026-06-18.json")
    assert [d["lien"] for d in seance["documents"]] == [f"{ROPRAZ}/n1458"]
    gestion = _lire(tmp_path, "conseils/5798/objets/03-2026.json")
    assert (gestion["titre"], gestion["depose"]) == ("Gestion et comptes 2025", "2026-06-09")
    assert [d["lien"] for d in gestion["documents"]] == [f"{ROPRAZ}/n1456", f"{ROPRAZ}/n1455"]
    assert sorted(p.name for p in (tmp_path / "conseils/5798/objets").iterdir()) == ["03-2026.json", "10-2026.json"]


def test_les_documents_des_deux_recherches_sont_reunis_sous_les_regles_d_une_seule(tmp_path, horloge, capsys):
    # Duillier, le 9 novembre : deux « Préavis 01-2026 », l'un dans chaque recherche ; un préavis rangé sous sa Séance,
    # dont le procès-verbal est dans l'autre recherche ; un procès-verbal que les deux recherches donnent.
    reseau = _reseau(horloge)
    preavis, proces_verbaux = _deux_recherches(reseau)
    juin = "Séance du 18 juin 2026"
    proces_verbal = _document_par_type(1458, "Procès-verbal", "Procès-verbal", "", "18 juin 2026", juin)
    reseau.pages[preavis] = _resultats(
        1, 3, 3,
        _document_par_type(1454, "Préavis 01-2026 du bureau", "Préavis", "01-2026", "9 juin 2026"),
        _document_par_type(1456, "Préavis 03-2026 Gestion et comptes 2025", "Préavis", "03-2026", "9 juin 2026", juin),
        proces_verbal,
    )
    reseau.pages[proces_verbaux] = _resultats(
        1, 3, 3,
        proces_verbal,
        _document_par_type(1457, "Rapport de la commission de gestion", "Rapport", "03-2026", "18 juin 2026", juin),
        _document_par_type(1407, "Préavis 01-2026 Patrimoine arboré", "Préavis", "01-2026", "24 mars 2026"),
    )
    sources = _sources(_ropraz_en_deux_recherches())

    _passer(tmp_path, horloge, reseau, sources, rattrapage_cible="5798")

    # La Séance a ses documents des deux recherches, chacun une fois, dans l'ordre de leurs nœuds.
    seance = _lire(tmp_path, "conseils/5798/seances/2026-06-18.json")
    assert [d["lien"] for d in seance["documents"]] == [f"{ROPRAZ}/n{n}" for n in (1456, 1457, 1458)]
    # Le préavis garde le rapport de sa Séance que l'autre recherche donne.
    gestion = _lire(tmp_path, "conseils/5798/objets/03-2026.json")
    assert [d["lien"] for d in gestion["documents"]] == [f"{ROPRAZ}/n1456", f"{ROPRAZ}/n1457"]
    # De deux préavis de même numéro, le plus ancien l'emporte, quelle que soit la recherche qui le donne.
    assert _lire(tmp_path, "conseils/5798/objets/01-2026.json")["titre"] == "Patrimoine arboré"
    assert "Objet 01-2026 en double, le plus ancien gardé (« Patrimoine arboré ») : Préavis 01-2026 du bureau" in (
        capsys.readouterr().err
    )


def test_chaque_recherche_va_jusqu_a_sa_fin_meme_si_sa_premiere_page_ne_reprend_que_l_autre(tmp_path, horloge):
    # La seconde recherche n'a, en première page, qu'un document que la première a déjà donné : elle n'est pas finie
    # pour autant, sa page suivante est lue.
    reseau = _reseau(horloge)
    preavis, proces_verbaux = _deux_recherches(reseau)
    juin = "Séance du 18 juin 2026"
    proces_verbal = _document_par_type(1458, "Procès-verbal", "Procès-verbal", "", "18 juin 2026", juin)
    reseau.pages[preavis] = _resultats(1, 1, 1, proces_verbal)
    reseau.pages[proces_verbaux] = _resultats(1, 1, 2, proces_verbal)
    reseau.pages[_page_suivante(proces_verbaux, 2)] = _resultats(
        2, 2, 2, _document_par_type(1483, "Extrait des décisions", "", "", "", "Séance du 24 septembre 2026")
    )

    _passer(tmp_path, horloge, reseau, _sources(_ropraz_en_deux_recherches()))

    lues = [r.url for r in reseau.journal if "/coreapi/" in r.url]
    assert lues == [preavis, proces_verbaux, _page_suivante(proces_verbaux, 2)]
    assert [d["lien"] for d in _lire(tmp_path, "conseils/5798/seances/2026-06-18.json")["documents"]] == [
        f"{ROPRAZ}/n1458"
    ]
    assert (tmp_path / "conseils/5798/seances/2026-09-24.json").exists()


def test_une_seconde_recherche_qui_ne_se_lit_pas_met_l_import_en_echec(tmp_path, horloge, capsys):
    # Sans ses procès-verbaux, chaque Séance serait réécrite avec une partie de ses documents.
    reseau = _reseau(horloge)
    _preavis, proces_verbaux = _duillier(reseau)
    del reseau.pages[proces_verbaux]  # 404

    _passer(tmp_path, horloge, reseau, _sources(_ropraz_en_deux_recherches()))

    assert "Import en échec : Conseil général de Ropraz (site de la commune)" in capsys.readouterr().err
    assert "5798" not in _lire(tmp_path, "conseils/import.json")["conseils"]
    assert not (tmp_path / "conseils/5798/objets").exists()


def test_les_pages_des_deux_recherches_comptent_ensemble_dans_le_plafond_de_la_commune(tmp_path, horloge, capsys):
    # 30 pages de résultats par recherche : chacune tiendrait sous le plafond de 60 requêtes, pas les deux ensemble,
    # avec `robots.txt` et la sonde. Le rattrapage, sans plafond, les lit toutes.
    reseau = _reseau(horloge)
    for n, url in enumerate(_deux_recherches(reseau)):
        for page in range(1, 31):
            document = _document_par_type(1000 * (n + 1) + page, "Procès-verbal", "", "", "", "Séance du 18 juin 2026")
            reseau.pages[url if page == 1 else _page_suivante(url, page)] = _resultats(page, page, 30, document)
    sources = _sources(_ropraz_en_deux_recherches())

    _passer(tmp_path, horloge, reseau, sources)

    assert len(reseau.journal) == 60
    journal = capsys.readouterr().err
    assert "Import en échec : Conseil général de Ropraz (site de la commune)" in journal
    assert "plafond de 60 requêtes atteint" in journal
    assert not (tmp_path / "conseils/5798/seances").exists()

    _passer(tmp_path, horloge, reseau, sources, rattrapage_cible="5798", heure=T0 + timedelta(days=1))

    assert len(_lire(tmp_path, "conseils/5798/seances/2026-06-18.json")["documents"]) == 60


def test_les_deux_recherches_sont_demandees_chacune_avec_ses_parametres(tmp_path, horloge):
    reseau = _reseau(horloge)
    _duillier(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_ropraz_en_deux_recherches()))

    recherches = [parse_qs(urlsplit(r.url).query, keep_blank_values=True) for r in reseau.journal if "/coreapi/" in r.url]
    assert [(p["elasticsearchNode"], p["elasticsearchPagesize"], p["elasticsearchSort"]) for p in recherches] == [
        (["748"], ["200"], ["date_extid_desc_rank"]),
        (["749"], ["60"], ["date_extid"]),
    ]


# --- Ancienne génération : la bibliothèque d'Aigle -----------------------------------------------------------------

AIGLE = "https://www.aigle.ch"


def _aigle(**options):
    return _quicksite(5401, "Aigle", f"{AIGLE}/documents", variante="ancienne", **options)


def _piece(n, titre, type_, publie, reference="", description=""):
    """Un document de la bibliothèque, à la forme de ceux d'Aigle."""
    return (
        f'<div class="tplDocumentSummaryItem"><div class="col-md-6"><a href="/N{n}/x.html">'
        f'<h4 class="strNodeName"><strong>{titre}</strong></h4></a><p><span class="strBusinessID">{reference}</span>'
        f'<span id="doctype">{type_}</span></p></div><div class="col-md-3"><div class="strDescription"><small>'
        f'{description}</small></div></div><div class="col-md-3"><a href="/qsPortal/Home.asp?N={n}&amp;DocAction=Download">'
        f'</a><p><small class="dtmDocLastUpdate">{publie} 08:00:00</small></p></div></div>'
    )


def _bibliotheque(*pieces):
    return Page(f'<div class="tplListDocumentSummary"><div class="resultsFrame">{"".join(pieces)}</div></div>')


def _aigle_en_trois_pages(reseau):
    """La bibliothèque d'Aigle : l'échantillon en première page (mises en ligne de septembre à novembre 2026), une
    deuxième page mise en ligne avant la fenêtre, une troisième vide (après la dernière page, le site n'a plus rien)."""
    reseau.pages[f"{AIGLE}/documents?Page_0=2"] = _bibliotheque(
        _piece(19900, "Ordre du jour du Conseil communal du 12 mars 2026", "Ordre du jour", "02.03.2026"),
        _piece(19901, "Préavis 2026-12 première version", "Préavis", "01.03.2026"),
        _piece(19902, "Procès-verbal Installation des autorités communales", "PV du conseil", "01.03.2026"),
    )
    reseau.pages[f"{AIGLE}/documents?Page_0=3"] = _bibliotheque()


def test_une_commune_de_l_ancienne_generation_tire_ses_seances_des_titres_de_ses_documents(tmp_path, horloge):
    reseau = _reseau(horloge)
    _aigle_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_aigle()))

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5401/seances.json")["seances"]] == [
        "5401/2026-10-29",
        "5401/2026-10-01",
        "5401/2026-09-03",
    ]
    seance = _lire(tmp_path, "conseils/5401/seances/2026-10-01.json")
    assert (seance["nom"], seance["lien"], seance["ordre_du_jour"]) == ("Séance du 1er octobre 2026", None, [])
    lien = f"{AIGLE}/qsPortal/Home.asp?N={{}}&DocAction=Download"
    assert seance["documents"] == [
        {"titre": "Procès-Verbal du Conseil Communal du 1er octobre 2026", "date": "2026-11-04", "lien": lien.format(20354)},
        {"titre": "Extrait de décision préavis 2025-10", "date": "2026-10-05", "lien": lien.format(20280)},
        {"titre": "Ordre du jour de la séance du Conseil communal du 1er octobre 2026", "date": "2026-09-30", "lien": lien.format(20248)},
        {"titre": "Ordre du jour de la séance du Conseil communal du 1er octobre 2026", "date": "2026-09-30", "lien": lien.format(20249)},
    ]


def test_les_preavis_de_la_bibliotheque_sont_dates_de_leur_mise_en_ligne_avec_les_documents_qui_les_citent(
    tmp_path, horloge
):
    reseau = _reseau(horloge)
    _aigle_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_aigle()))

    preavis = _lire(tmp_path, "conseils/5401/objets/2026-12.json")
    assert (preavis["numero"], preavis["titre"], preavis["type"], preavis["depose"]) == (
        "2026-12",
        "Transition numérique",
        "Préavis",
        "2026-10-14",
    )
    assert [d["titre"] for d in preavis["documents"]] == ["Préavis 2026-12 - Transition numérique", "Annexe au préavis 2026-12"]
    assert (preavis["statut"], preavis["contributeurs"]) == (None, [])
    # Une interpellation, un rapport de commission : pas des préavis.
    assert sorted(p.name for p in (tmp_path / "conseils/5401/objets").iterdir()) == ["2026-12.json", "2026-14.json"]


def test_le_passage_ordinaire_s_arrete_a_la_premiere_page_mise_en_ligne_avant_la_fenetre(tmp_path, horloge):
    reseau = _reseau(horloge)
    _aigle_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_aigle()))

    assert [r.url for r in reseau.journal if "Page_0" in r.url] == [f"{AIGLE}/documents?Page_0=2"]
    assert len(reseau.journal) < 60
    assert not (tmp_path / "conseils/5401/seances/2026-03-12.json").exists()


def test_le_rattrapage_lit_la_bibliotheque_jusqu_a_sa_derniere_page(tmp_path, horloge, capsys):
    reseau = _reseau(horloge)
    _aigle_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_aigle()), rattrapage_cible="5401")

    assert [r.url for r in reseau.journal if "Page_0" in r.url] == [
        f"{AIGLE}/documents?Page_0=2",
        f"{AIGLE}/documents?Page_0=3",
    ]
    assert (tmp_path / "conseils/5401/seances/2026-03-12.json").exists()
    journal = capsys.readouterr().err
    # Le premier du site, le plus récent, l'emporte ; un procès-verbal sans date n'a pas de Séance.
    assert (
        "Objet 2026-12 en double, le premier du site gardé (« Transition numérique ») : "
        "Préavis 2026-12 première version"
    ) in journal
    assert "document de Séance sans date : Procès-verbal Installation des autorités communales" in journal
    assert _lire(tmp_path, "conseils/5401/objets/2026-12.json")["depose"] == "2026-10-14"


def test_une_commune_de_l_ancienne_generation_en_seances_seulement_n_importe_aucun_preavis(tmp_path, horloge):
    reseau = _reseau(horloge)
    _aigle_en_trois_pages(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_aigle(donne=("seances",))))

    assert (tmp_path / "conseils/5401/seances/2026-10-29.json").exists()
    assert not (tmp_path / "conseils/5401/objets").exists()


def test_une_bibliotheque_disparue_est_un_marqueur_absent(tmp_path, horloge):
    reseau = _reseau(horloge)
    reseau.pages[f"{AIGLE}/documents"] = Page("<html><body><h1>Documents</h1></body></html>")

    _passer(tmp_path, horloge, reseau, _sources(_aigle()))

    assert _lire(tmp_path, "etat-sources.json")["sources"]["site-5401"]["motif"] == "marqueur absent"


# --- Module Conseil : Montreux, Vevey ------------------------------------------------------------------------------

MONTREUX = "https://www.conseilmontreux.ch/conseilcommunal/public"
VEVEY = "https://www.vevey.ch/vie-politique/conseil-communal/seances-passees-et-videos"


def _montreux(**options):
    options.setdefault("donne", ("objets", "seances"))
    return _quicksite(
        5886, "Montreux", f"{MONTREUX}/ordredujour/", variante="conseil", membres=f"{MONTREUX}/conseillers/", **options
    )


def _vevey():
    return _quicksite(5890, "Vevey", VEVEY, variante="conseil-externe", donne=("seances",))


def _montreux_complet(reseau):
    """Le module de Montreux : l'échantillon, une Séance annoncée sans page le 9 décembre, et les pages des Séances
    voisines de celle de l'échantillon (9 septembre, 11 novembre), fabriquées."""
    url = f"{MONTREUX}/ordredujour/"
    page = reseau.pages[url]
    annoncee = (
        '<div class="col col-md-3 col-lg-2 text-center tmp4 date-future"><a href="#"><div class="bullet-date">'
        '<div class="day">09</div><label>Décembre</label></div></a></div>'
    )
    corps = page.corps.decode("utf-8")
    fin = corps.index('<div class="col col-md-3 col-lg-2 text-center tmp3 date-nextmeeting">')
    fin = corps.index("</div>\n</div>\n</div>", fin)  # la fin de la pastille du 11 novembre
    corps = corps[: fin + len("</div>\n</div>\n</div>")] + annoncee + corps[fin + len("</div>\n</div>\n</div>") :]
    reseau.pages[url] = Page(corps, entetes=page.entetes)
    for ident, titre in ((4311, "séance du 9 septembre 2026"), (4313, "séance du 11 novembre 2026")):
        reseau.pages[f"{MONTREUX}/ordredujour/?ID={ident}"] = Page(
            f'<div class="tplDetailBlade"><h1>{titre}</h1><div class="card"><div class="card-body">'
            f'<div class="box"><div class="description"><p>Ordre du jour</p></div></div>'
            f'<a href="https://www.conseilmontreux.ch/conseilcommunal/download.asp?d={ident}0" class="docname" '
            f'title="OJ_{ident}.pdf">OJ_{ident}.pdf</a></div></div></div>'
        )


def test_une_seance_du_module_conseil_a_ses_points_relies_a_leurs_objets_et_le_reste_de_ses_documents(
    tmp_path, horloge
):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    seance = _lire(tmp_path, "conseils/5886/seances/2026-10-07.json")
    assert (seance["nom"], seance["lien"]) == ("séance du 7 octobre 2026", f"{MONTREUX}/ordredujour/?ID=4312")
    points = [(p["titre"][:40], p["objet"]) for p in seance["ordre_du_jour"]]
    assert points == [
        ("Préambule", None),
        ("Approbation du procès-verbal de la séanc", None),
        ("Préavis 27/2026 renvoi commission Sur la", None),  # sa fiche n'a pas pu être lue
        ("Préavis 29/2026 relatif à la fixation de", "5886/29-2026"),
    ]
    # Les documents d'un point qui cite un Objet restent à l'Objet, même quand sa fiche ne se lit pas (27/2026) ;
    # ceux des points sans Objet vont à la Séance.
    assert [d["titre"] for d in seance["documents"]] == [
        "AG_OJCC_Seance_20261007_VF.pdf",
        "PV_9_SEPTEMBRE_2026_provisoire-VF.pdf",
    ]


def test_un_objet_du_module_conseil_a_son_auteur_ses_documents_dates_et_pas_de_statut(tmp_path, horloge):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    objet = _lire(tmp_path, "conseils/5886/objets/29-2026.json")
    assert (objet["numero"], objet["type"], objet["statut"], objet["depose"]) == ("29/2026", "Préavis", None, "2026-09-08")
    assert objet["titre"].startswith("relatif à la fixation de la rémunération")
    assert objet["lien"] == f"{MONTREUX}/documents/recherche/?id=3403"
    assert [(c["nom"], c["sorte"]) for c in objet["contributeurs"]] == [("Municipalité", "groupe")]
    assert [(d["titre"][:30], d["date"]) for d in objet["documents"]] == [
        ("9_1_Preavis_29_2026_Indemnites", "2026-09-08"),
        ("Rapport-relatif-a-la-fixation-", "2026-09-28"),
    ]


def test_les_documents_d_un_point_dont_la_fiche_ne_se_lit_pas_attendent_leur_objet(tmp_path, horloge, capsys):
    # La fiche du préavis 29/2026 en 404 un jour : ses documents ne vont pas à la Séance, où l'import, qui garde les
    # documents archivés, les laisserait pour toujours ; ils vont à l'Objet le jour où sa fiche se relit.
    reseau = _reseau(horloge)
    _montreux_complet(reseau)
    fiche = f"{MONTREUX}/documents/recherche/?id=3403"
    lisible = reseau.pages[fiche]
    reseau.pages[fiche] = Page("introuvable", statut=404)
    sources = _sources(_montreux())

    _passer(tmp_path, horloge, reseau, sources)

    assert f"élément sauté, Objet {fiche} non lu" in capsys.readouterr().err
    assert not (tmp_path / "conseils/5886/objets/29-2026.json").exists()
    reseau.pages[fiche] = lisible
    _passer(tmp_path, horloge, reseau, sources, heure=T0 + timedelta(days=1))

    seance = _lire(tmp_path, "conseils/5886/seances/2026-10-07.json")
    assert [d["titre"] for d in seance["documents"]] == [
        "AG_OJCC_Seance_20261007_VF.pdf",
        "PV_9_SEPTEMBRE_2026_provisoire-VF.pdf",
    ]
    assert [p["objet"] for p in seance["ordre_du_jour"]][-1] == "5886/29-2026"
    documents = _lire(tmp_path, "conseils/5886/objets/29-2026.json")["documents"]
    assert [d["lien"].rsplit("=", 1)[-1] for d in documents] == ["8614", "8622"]


def test_les_documents_d_un_point_dont_la_fiche_n_a_pas_de_numero_vont_a_la_seance(tmp_path, horloge, capsys):
    # Une interpellation sans numéro (fiche « <h1>Interpellation</h1> ») n'est pas importée : son point est un point
    # sans Objet, et ses documents (la réponse de la Municipalité) vont à la Séance, d'un passage à l'autre.
    reseau = _reseau(horloge)
    _montreux_complet(reseau)
    fiche = f"{MONTREUX}/documents/recherche/?id=3403"
    page = reseau.pages[fiche]
    corps = page.corps.decode("utf-8").replace("<h1>Préavis 29/2026</h1>", "<h1>Interpellation</h1>")
    reseau.pages[fiche] = Page(corps, entetes=page.entetes)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    assert "élément sauté, Objet sans numéro, non importé : Interpellation" in capsys.readouterr().err
    assert not (tmp_path / "conseils/5886/objets").exists()
    seance = _lire(tmp_path, "conseils/5886/seances/2026-10-07.json")
    assert [p["objet"] for p in seance["ordre_du_jour"]] == [None, None, None, None]
    assert [d["lien"].rsplit("=", 1)[-1] for d in seance["documents"]] == ["8636", "8637", "8614", "8622"]


def test_un_document_du_module_conseil_est_nomme_par_le_texte_de_son_lien_sinon_par_son_fichier(tmp_path, horloge):
    # ADR 0010 : le texte du lien (sans la taille du fichier), sinon le nom du fichier quand ce texte ne nomme rien.
    reseau = _reseau(horloge)
    _montreux_complet(reseau)
    telecharger = "https://www.conseilmontreux.ch/conseilcommunal/download.asp?d={}"
    reseau.pages[f"{MONTREUX}/ordredujour/?ID=4313"] = Page(
        '<div class="tplDetailBlade"><h1>séance du 11 novembre 2026</h1><div class="card"><div class="card-body">'
        '<div class="box"><div class="description"><p>Ordre du jour</p></div></div>'
        f'<a href="{telecharger.format(43130)}" class="docname" title="OJ_4313.pdf">Ordre du jour du 11 novembre '
        '<span class="badge badge-secondary ml-2">120.4 Kb</span></a>'
        f'<a href="{telecharger.format(43131)}" class="docname" title="PV_4313.pdf">'
        '<span class="badge badge-secondary ml-2">2.1 Mb</span></a>'
        f'<a href="{telecharger.format(43132)}" class="docname" title="Annexe_4313.pdf">Télécharger</a>'
        "</div></div></div>"
    )

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    titres = [d["titre"] for d in _lire(tmp_path, "conseils/5886/seances/2026-11-11.json")["documents"]]
    assert titres == ["Ordre du jour du 11 novembre", "PV_4313.pdf", "Annexe_4313.pdf"]


def test_le_module_conseil_lit_ses_conseillers_page_apres_page_et_les_epargne_dans_les_titres(tmp_path, horloge):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    assert _lire(tmp_path, "conseils/5886/membres.json")["membres"] == [
        "Ihab Al Jundi",
        "Jonathan Al Jundi",
        "Olivier Müller",
        "Tal Luder",
    ]
    (point,) = [p for p in _lire(tmp_path, "conseils/5886/seances/2026-10-07.json")["ordre_du_jour"] if p["objet"]]
    assert "(Rapp. M. Olivier Müller)" in point["titre"]  # un conseiller connu reste lisible


def test_le_module_conseil_garde_une_seance_annoncee_sans_page_et_s_en_tient_a_la_fenetre(tmp_path, horloge):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()))

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5886/seances.json")["seances"]] == [
        "5886/2026-12-09",
        "5886/2026-11-11",
        "5886/2026-10-07",
        "5886/2026-09-09",
    ]
    assert _lire(tmp_path, "conseils/5886/seances/2026-12-09.json")["lien"] is None
    # Les Séances de 2025, avant la fenêtre, ne sont pas ouvertes.
    assert not any("ID=415" in r.url for r in reseau.journal)


def test_au_rattrapage_le_module_conseil_ouvre_aussi_les_annees_precedentes(tmp_path, horloge, capsys):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux()), rattrapage_cible="5886")

    assert f"{MONTREUX}/ordredujour/?ID=4157" in [r.url for r in reseau.journal]
    assert f"{MONTREUX}/ordredujour/?ID=4157 non lue" in capsys.readouterr().err  # pas dans l'échantillon : sautée


def test_un_module_conseil_en_seances_seulement_n_ouvre_aucune_fiche_d_objet(tmp_path, horloge):
    reseau = _reseau(horloge)
    _montreux_complet(reseau)

    _passer(tmp_path, horloge, reseau, _sources(_montreux(donne=("seances",))))

    assert not any("/documents/recherche/" in r.url for r in reseau.journal)
    assert not (tmp_path / "conseils/5886/objets").exists()
    titres = [d["titre"] for d in _lire(tmp_path, "conseils/5886/seances/2026-10-07.json")["documents"]]
    assert "9_1_Preavis_29_2026_IndemnitesMembres_CC_VF.pdf" in titres


def test_vevey_lit_ses_seances_sur_le_site_de_la_ville_et_leur_ordre_du_jour_en_iso_8859_1(tmp_path, horloge):
    reseau = _reseau(horloge)

    _passer(tmp_path, horloge, reseau, _sources(_vevey()))

    seance = _lire(tmp_path, "conseils/5890/seances/2026-10-01.json")
    assert (seance["date"], seance["lien"]) == ("2026-10-01T19:30", "https://conseil.vevey.ch/ConseilCommunal/seances/?ID=157")
    assert seance["nom"] == "Séance du Conseil communal du jeudi 1er octobre 2026 - 19h30"
    assert [(p["numero"], p["titre"][:30]) for p in seance["ordre_du_jour"]] == [
        ("2.1", "Adoption de l’ordre du jour de"),
        ("9.1", "Réponse au postulat de [partic"),  # Vevey n'a pas de page des membres : masqué
        ("9.2", "Fixation des indemnités et jet"),
        ("10.1", "Arrêté communal d’imposition p"),
        ("10.2", "Crédits supplémentaires au bud"),
    ]
    assert [d["titre"] for d in seance["documents"]][:2] == [
        "OJ-CC_2026-10-01-octobre-2026-ID-7291272.pdf",
        "rp25_2026_RP-Reponse-postulat-J-Rilliet_Violences-domestiques.pdf",
    ]


def test_vevey_ne_demande_que_ce_que_son_robots_txt_autorise_a_la_casse_pres(tmp_path, horloge):
    reseau = _reseau(horloge)
    reseau.pages["https://conseil.vevey.ch/robots.txt"] = Page(
        "User-agent: *\nAllow: /ConseilCommunal/seances/\nAllow: /conseilcommunal/download.asp\nDisallow: /\n",
        entetes={"Content-Type": "text/plain"},
    )

    _passer(tmp_path, horloge, reseau, _sources(_vevey()))

    module = [r.url for r in reseau.journal if "conseil.vevey.ch" in r.url]
    # Le lien cassé du site de la Ville (`www.vevey.ch/conseil.vevey.ch/conseilcommunal/…`) est récrit à la casse
    # autorisée ; la Séance du 3 septembre, sans page dans l'échantillon, est sautée.
    assert module == [
        "https://conseil.vevey.ch/robots.txt",
        "https://conseil.vevey.ch/ConseilCommunal/seances/?ID=157",
        "https://conseil.vevey.ch/ConseilCommunal/seances/?ID=156",
    ]
    assert (tmp_path / "conseils/5890/seances/2026-10-01.json").exists()


SEANCE_VEVEY = "https://conseil.vevey.ch/ConseilCommunal/seances/?ID={}"


def test_une_page_de_seance_de_vevey_sans_points_est_sautee_et_notee_dans_le_journal(tmp_path, horloge, capsys):
    reseau = _reseau(horloge)
    page = reseau.pages[SEANCE_VEVEY.format(157)]
    reseau.pages[SEANCE_VEVEY.format(156)] = page  # le 3 septembre se lit
    reseau.pages[SEANCE_VEVEY.format(157)] = Page(
        '<html><body><div class="mainDiv"><h1>Ordre du jour</h1></div></body></html>', entetes=page.entetes
    )

    _passer(tmp_path, horloge, reseau, _sources(_vevey()))

    assert f"élément sauté, Séance {SEANCE_VEVEY.format(157)} illisible" in capsys.readouterr().err
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5890/seances.json")["seances"]] == ["5890/2026-09-03"]


def test_une_refonte_du_module_de_vevey_que_la_sonde_ne_voit_pas_met_l_import_en_echec(tmp_path, horloge, capsys):
    # La sonde lit la liste sur le site de la Ville : si aucune page de Séance du module ne se lit (le 1er octobre sans
    # points, le 3 septembre absent de l'échantillon), c'est l'import qui le dit, comme une liste illisible.
    reseau = _reseau(horloge)
    reseau.pages[SEANCE_VEVEY.format(157)] = Page('<html><body><main><h1>Nouveau site</h1></main></body></html>')

    _passer(tmp_path, horloge, reseau, _sources(_vevey()))

    assert "Import en échec : Conseil communal de Vevey (site de la commune)" in capsys.readouterr().err
    assert "5890" not in _lire(tmp_path, "conseils/import.json")["conseils"]
    assert _lire(tmp_path, "etat-sources.json")["sources"]["site-5890"]["etat"] == "disponible"  # pas une panne


def test_l_hote_du_module_se_lit_dans_le_lien_de_l_ordre_du_jour(tmp_path, horloge):
    # Rien n'est propre à Vevey : une ville dont la liste mène au module par un lien direct (le 1er octobre) donne
    # son hôte ; par un lien cassé qui le met en tête de son chemin (`www.ville.ch/conseil.ville.ch/…`, le
    # 3 septembre), le premier segment de ce chemin. L'un et l'autre sont récrits à la casse que `robots.txt` autorise.
    reseau = _reseau(horloge)
    reseau.adresses |= {"www.ville.ch": "5.102.147.10", "conseil.ville.ch": "5.102.147.20"}
    page = reseau.pages[VEVEY]
    liste = page.corps.replace(
        b"http://www.vevey.ch/conseil.vevey.ch/conseilcommunal/seances/?ID=157",
        b"https://conseil.ville.ch/conseilcommunal/seances/?ID=157",
    ).replace(b"http://www.vevey.ch/conseil.vevey.ch/", b"https://www.ville.ch/conseil.ville.ch/")
    reseau.pages["https://www.ville.ch/seances"] = Page(liste, entetes=page.entetes)
    reseau.pages["https://conseil.ville.ch/ConseilCommunal/seances/?ID=157"] = reseau.pages[SEANCE_VEVEY.format(157)]
    ville = _quicksite(5890, "Vevey", "https://www.ville.ch/seances", variante="conseil-externe", donne=("seances",))

    _passer(tmp_path, horloge, reseau, _sources(ville))

    assert [r.url for r in reseau.journal if "/seances/?ID=" in r.url] == [
        "https://conseil.ville.ch/ConseilCommunal/seances/?ID=157",
        "https://conseil.ville.ch/ConseilCommunal/seances/?ID=156",
    ]
    assert (tmp_path / "conseils/5890/seances/2026-10-01.json").exists()


@pytest.mark.parametrize(
    "href",
    [
        "http://www.vevey.ch/conseil.vevey.ch/conseilcommunal/seances/?ID=157&amp;DOC=1",  # cassé, l'hôte en chemin
        "https://conseil.vevey.ch/conseilcommunal/seances/?ID=157",  # direct
        "//conseil.vevey.ch/conseilcommunal/seances/?ID=157",  # sans schéma, à la racine
        "conseil.vevey.ch/conseilcommunal/seances/?ID=157",  # sans schéma ni barre : l'hôte, pas un chemin relatif
    ],
)
def test_le_lien_de_l_ordre_du_jour_mene_au_module_sous_chacune_de_ses_formes(tmp_path, horloge, href):
    reseau = _reseau(horloge)
    page = reseau.pages[VEVEY]
    casse = b"http://www.vevey.ch/conseil.vevey.ch/conseilcommunal/seances/?ID=157&amp;DOC=1"
    reseau.pages[VEVEY] = Page(page.corps.replace(casse, href.encode()), entetes=page.entetes)

    _passer(tmp_path, horloge, reseau, _sources(_vevey()))

    assert SEANCE_VEVEY.format(157) in [r.url for r in reseau.journal]
    assert (tmp_path / "conseils/5890/seances/2026-10-01.json").exists()
