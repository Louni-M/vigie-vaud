"""Le script de préparation des sources sur Quicksite (`preparation_sources.py`, spec de J3, « Scripts de
préparation ») : la mesure du module de lecture Quicksite trouve la variante de chaque site (ancienne génération,
recherche `coreapi` et ses paramètres, ou ses deux recherches quand la commune sépare ses préavis et ses
procès-verbaux, module Conseil, module Conseil dont la liste est sur le site de la Ville),
le brouillon déclare chaque commune, et la vérification le relit sans écart. Le réseau est le faux réseau des sites,
qui sert l'échantillon Quicksite et des pages du conseil fabriquées.
"""

from datetime import UTC, date, datetime

import httpx

from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau, echantillon
from preparation_sources import Candidat, brouillon, verifier
from robot_communal import Robot
from schema import FichierSources

T0 = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)
JOUR = date(2026, 10, 23)
LICENCE = "Actes officiels (art. 5 LDA) : métadonnées et liens seulement"
AIGLE, FOUNEX, MONTREUX = "https://www.aigle.ch", "https://www.founex.ch", "https://www.conseilmontreux.ch"
VEVEY = "https://www.vevey.ch/vie-politique/conseil-communal/seances-passees-et-videos"
RECHERCHE_FOUNEX = (
    f"{FOUNEX}/coreapi/elasticsearch/projects/founex25/documentconseildates/search?q=&elasticsearchProject="
    "&elasticsearchNode=640&elasticsearchPagesize=60&elasticsearchNodetype=&elasticsearchParentnode=640"
    "&elasticsearchSort=date_extid&elasticsearchView=documentconseildates&elasticsearchQuery=input.query-full"
    "&elasticsearchResult=%23search-result-list-full&elasticsearchFiltertags=&elasticsearchInitresult=true"
    "&query=&date_from=&date_to="
)

PLATEFORMES = [
    {
        "id": "quicksite",
        "nom": "Quicksite",
        "editeur": "eAdmin Solutions SA",
        "variantes": [
            {"id": "ancienne", "marqueur": "tplListDocumentSummary", "niveaux": [["preavis", "seances"], ["seances"]]},
            {"id": "coreapi", "marqueur": "tplDeepsearch", "niveaux": [["preavis", "seances"], ["seances"]]},
            {"id": "conseil", "marqueur": "tplCCIBPublicOrdreJour", "niveaux": [["objets", "seances"], ["seances"]]},
            {"id": "conseil-externe", "marqueur": "teaser-agenda", "niveaux": [["seances"]]},
        ],
    }
]


def _page_quicksite(menu, contenu=""):
    """Une page du conseil Quicksite, réduite à sa balise `generator` et à son menu (`menu` : chemin, texte)."""
    liens = "".join(f'<li><a href="{chemin}">{texte}</a></li>' for chemin, texte in menu)
    return Page(
        '<html><head><meta name="generator" content="CMS - Quicksite www.quicksite.ch"></head><body>'
        f'<nav><ul><li><a href="/">Accueil</a></li>{liens}</ul></nav><main><h1>Conseil</h1>{contenu}</main></body></html>'
    )


def _reseau(horloge):
    reseau = Reseau(
        horloge,
        adresses={
            "www.aigle.ch": "185.54.6.109",
            "www.founex.ch": "193.34.137.65",
            "www.conseilmontreux.ch": "185.54.6.110",
            "www.vevey.ch": "5.102.146.10",
            "conseil.vevey.ch": "5.102.146.20",
            "www.exemple.ch": "5.102.146.30",
        },
    )
    for variante in ("ancienne", "coreapi", "conseil", "conseil-externe"):
        reseau.pages |= echantillon("quicksite", variante)
    reseau.pages[f"{AIGLE}/N387/conseil-communal.html"] = _page_quicksite(
        [("/N389/membres.html", "Membres"), ("/documents", "Documents du Conseil")]
    )
    reseau.pages[f"{FOUNEX}/N1487/conseil-communal.html"] = _page_quicksite(
        [("/N639/membres.html", "Membres"), ("/N640/documents.html", "Documents"), ("/N646/x.html", "Prochaines séances")]
    )
    # La page des documents de Founex appelle le script de sa recherche (retiré de l'échantillon, comme tout script).
    page = reseau.pages[f"{FOUNEX}/N640/documents.html"]
    script = b'<script src="/coreapi/elasticsearch/projects/founex25/assets/js/elasticsearch.js?ts=1"></script>'
    reseau.pages[f"{FOUNEX}/N640/documents.html"] = Page(page.corps.replace(b"<main>", script + b"<main>", 1))
    reseau.pages[f"{RECHERCHE_FOUNEX}&page=2"] = Page(
        '<div class="tplDocumentConseil">61 à 120 sur 399 éléments trouvés<div class="accordion-item"><h2>'
        '<button>Séance du 2 mars 2026</button></h2><div class="qs-edit" data-qsedit-editnode="1776">'
        f'<a href="{FOUNEX}/n1776"><h6>Ordre du jour du 02.03.2026</h6></a></div></div></div>'
    )
    reseau.pages[f"{MONTREUX}/"] = _page_quicksite(
        [("/conseilcommunal/public/ordredujour/", "Séances"), ("/conseilcommunal/public/conseillers", "Conseillers")]
    )
    reseau.pages["https://www.exemple.ch/conseil"] = Page("<html><body><p>Site WordPress</p></body></html>")
    return reseau


def _robot(reseau, horloge):
    return Robot(httpx.Client(transport=reseau.transport()), horloge, horloge.attendre, reseau.resoudre)


def _fichier(*sources):
    return FichierSources.model_validate({"plateformes": PLATEFORMES, "sources": list(sources)})


CANDIDATS = [
    Candidat(5401, "Aigle", "Conseil communal", f"{AIGLE}/N387/conseil-communal.html"),
    Candidat(5717, "Founex", "Conseil communal", f"{FOUNEX}/N1487/conseil-communal.html"),
    Candidat(5886, "Montreux", "Conseil communal", f"{MONTREUX}/"),
    Candidat(5890, "Vevey", "Conseil communal", VEVEY),
    Candidat(5999, "Exemple", "Conseil général", "https://www.exemple.ch/conseil"),
]


def _declaration(ofs, commune, page, donne, site):
    de = f"d'{commune}" if commune[0] in "AEIOU" else f"de {commune}"
    return {
        "id": f"site-{ofs}",
        "nom": f"Conseil communal {de} (site de la commune)",
        "nom_court": f"Site {de}",
        "attribution": {"texte": f"Commune {de}", "lien": page, "licence": LICENCE},
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "scrape"},
        "conseil": {"body_key": str(ofs), "donne": donne},
        "site": {"plateforme": "quicksite", **site},
    }


def test_le_brouillon_trouve_la_variante_de_chaque_site_quicksite_et_ses_parametres():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)

    sources, remarques = brouillon(_robot(reseau, horloge), CANDIDATS, _fichier().plateformes[0], JOUR)

    assert sources == [
        _declaration(
            5401, "Aigle", f"{AIGLE}/N387/conseil-communal.html", ["preavis", "seances"],
            {"variante": "ancienne", "seances": f"{AIGLE}/documents"},
        ),
        _declaration(
            5717, "Founex", f"{FOUNEX}/N1487/conseil-communal.html", ["preavis", "seances"],
            {
                "variante": "coreapi",
                "seances": f"{FOUNEX}/N640/documents.html",
                "coreapi": {"projet": "founex25", "vue": "documentconseildates", "noeud": 640, "taille": 60,
                            "tri": "date_extid"},
            },
        ),
        _declaration(
            5886, "Montreux", f"{MONTREUX}/", ["objets", "seances"],
            {
                "variante": "conseil",
                "seances": f"{MONTREUX}/conseilcommunal/public/ordredujour/",
                "membres": f"{MONTREUX}/conseilcommunal/public/conseillers/",
            },
        ),
        _declaration(5890, "Vevey", VEVEY, ["seances"], {"variante": "conseil-externe", "seances": VEVEY}),
    ]
    assert remarques == {
        "site-5999": ["Exemple : pas sur Quicksite (aucune trace de Quicksite sur https://www.exemple.ch/conseil), "
                      "non déclarée"],
    }


def test_le_brouillon_quicksite_passe_la_verification_sans_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    sources, _ = brouillon(_robot(reseau, horloge), CANDIDATS, _fichier().plateformes[0], JOUR)

    assert verifier(_robot(reseau, horloge), _fichier(*sources), "quicksite", JOUR) == []


def test_des_parametres_coreapi_qui_ne_sont_plus_ceux_du_site_sont_un_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    (founex,) = brouillon(_robot(reseau, horloge), CANDIDATS[1:2], _fichier().plateformes[0], JOUR)[0]
    founex["site"]["coreapi"]["projet"] = "founex24"

    (ecart,) = verifier(_robot(reseau, horloge), _fichier(founex), "quicksite", JOUR)
    assert ecart.startswith("site-5717 (Founex) : recherche coreapi déclarée {'projet': 'founex24'")


def test_la_mesure_cherche_le_marqueur_que_la_section_plateformes_declare():
    # Le marqueur de sonde de chaque variante n'est déclaré qu'une fois, dans `sources.json` (ADR 0010) : une
    # bibliothèque qui n'a pas celui de sa variante n'est pas une page des Séances.
    horloge = HorlogeFactice(T0)
    variantes = [
        {**v, "marqueur": "tplAutreBibliotheque"} if v["id"] == "ancienne" else v for v in PLATEFORMES[0]["variantes"]
    ]
    plateforme = FichierSources.model_validate(
        {"plateformes": [{**PLATEFORMES[0], "variantes": variantes}], "sources": []}
    ).plateformes[0]

    (aigle,), remarques = brouillon(_robot(_reseau(horloge), horloge), CANDIDATS[:1], plateforme, JOUR)

    assert aigle["couverture"]["mode"] == "non_couvert"
    assert remarques == {"site-5401": ["Aigle : aucune page des Séances Quicksite trouvée ; raison à relire"]}


# --- Deux recherches : préavis et procès-verbaux séparés (Duillier, Juriens) -------------------------------------

DUILLIER = "https://www.duillier.ch"
CANDIDAT_DUILLIER = Candidat(5715, "Duillier", "Conseil communal", f"{DUILLIER}/N528/conseil-communal.html")
PREAVIS_DUILLIER = {
    "projet": "duillier25", "vue": "documentconseil", "noeud": 543, "taille": 60, "tri": "date_extid_desc_doctag_rank"
}
PROCES_VERBAUX_DUILLIER = PREAVIS_DUILLIER | {"noeud": 720, "tri": "date_extid"}
DEUX_RECHERCHES_A_RELIRE = (
    "Duillier : 2 recherches coreapi (nœuds 543, 720), préavis et procès-verbaux séparés ; à relire : leurs documents "
    "ne doivent pas se reprendre"
)


def _recherche_de_duillier(noeud, tri, page=1):
    url = (
        f"{DUILLIER}/coreapi/elasticsearch/projects/duillier25/documentconseil/search?q=&elasticsearchProject="
        f"&elasticsearchNode={noeud}&elasticsearchPagesize=60&elasticsearchNodetype=&elasticsearchParentnode={noeud}"
        f"&elasticsearchSort={tri}&elasticsearchView=documentconseil&elasticsearchQuery=input.query-full"
        "&elasticsearchResult=%23search-result-list-full&elasticsearchFiltertags=&elasticsearchInitresult=true"
        "&query=&date_from=&date_to="
    )
    return url if page == 1 else f"{url}&page={page}"


def _page_des_documents(reseau, noeud, tri):
    """La page des documents de Founex retouchée pour Duillier : sa recherche sur le nœud `noeud`, triée par `tri`."""
    founex = reseau.pages[f"{FOUNEX}/N640/documents.html"].corps.decode("utf-8")
    return Page(
        founex.replace("founex25", "duillier25")
        .replace('"640"', f'"{noeud}"')
        .replace('sort="date_extid"', f'sort="{tri}"')
        .replace("documentconseildates", "documentconseil")
    )


def _duillier(reseau, pages=1, avant=()):
    """Duillier, qui sépare ses préavis et ses procès-verbaux : la page des documents de Founex retouchée en deux
    pages de son menu, chacune avec sa recherche (nœud 543, puis 720 sans tri déclaré), de `pages` pages de
    résultats chacune. Sa page des assemblées, sans recherche, n'est pas servie ; les liens `avant` (chemin, texte)
    précèdent les siens dans le menu."""
    reseau.adresses["www.duillier.ch"] = "193.34.137.66"
    reseau.pages[CANDIDAT_DUILLIER.page] = _page_quicksite(
        [
            *avant,
            ("/N543/preavis-municipaux.html", "Préavis municipaux"),
            ("/N720/proces-verbaux-du-conseil-communal.html", "Procès-verbaux du Conseil communal"),
            ("/N530/assemblees-du-conseil-communal.html", "Assemblées du Conseil communal - ordre du jour"),
        ]
    )
    for chemin, recherche, tri in (
        ("/N543/preavis-municipaux.html", PREAVIS_DUILLIER, PREAVIS_DUILLIER["tri"]),
        ("/N720/proces-verbaux-du-conseil-communal.html", PROCES_VERBAUX_DUILLIER, ""),
    ):
        noeud = recherche["noeud"]
        reseau.pages[f"{DUILLIER}{chemin}"] = _page_des_documents(reseau, noeud, tri)
        for page in range(1, pages + 1):
            reseau.pages[_recherche_de_duillier(noeud, recherche["tri"], page)] = Page(
                f'<div class="tplDocumentConseil"><div>{page} à {page} sur {pages} éléments trouvés</div>'
                f'<div class="qs-edit" data-qsedit-editnode="{noeud}{page}"><a href="{DUILLIER}/n{noeud}{page}">'
                f"<h5>Préavis {page:02d}-2026</h5></a></div></div>"
            )


def test_la_mesure_declare_les_deux_recherches_d_une_commune_qui_separe_preavis_et_proces_verbaux():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau)

    (duillier,), remarques = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)

    assert duillier == _declaration(
        5715, "Duillier", CANDIDAT_DUILLIER.page, ["preavis", "seances"],
        {
            "variante": "coreapi",
            "seances": f"{DUILLIER}/N543/preavis-municipaux.html",
            "coreapi": [PREAVIS_DUILLIER, PROCES_VERBAUX_DUILLIER],
        },
    )
    assert remarques == {"site-5715": [DEUX_RECHERCHES_A_RELIRE]}
    assert verifier(_robot(reseau, horloge), _fichier(duillier), "quicksite", JOUR) == []


def test_la_verification_ne_tient_pas_compte_de_l_ordre_des_recherches():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau)
    (duillier,), _ = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)
    duillier["site"]["coreapi"] = [PROCES_VERBAUX_DUILLIER, PREAVIS_DUILLIER]

    assert verifier(_robot(reseau, horloge), _fichier(duillier), "quicksite", JOUR) == []


def test_la_page_des_proces_verbaux_est_trouvee_au_dela_des_premiers_liens_du_menu():
    # Cinq pages de documents avant celles des préavis et des procès-verbaux : ces derniers sont le 7e lien du menu.
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau, avant=[(f"/N60{i}/documents-du-conseil-{i}.html", f"Documents du conseil {i}") for i in range(5)])

    (duillier,), _ = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)

    assert duillier["site"]["coreapi"] == [PREAVIS_DUILLIER, PROCES_VERBAUX_DUILLIER]


def test_une_page_generale_des_documents_du_conseil_n_appelle_pas_les_recherches_de_ses_parties():
    # Les pages des préavis et des procès-verbaux ne sont qu'une partie de la page des documents du conseil : la lire
    # en plus en reprendrait les documents.
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau, avant=[("/N500/documents-du-conseil.html", "Documents du Conseil communal")])
    reseau.pages[f"{DUILLIER}/N500/documents-du-conseil.html"] = _page_des_documents(reseau, 500, "date_extid")
    for noeud in (500, 543, 720):
        reseau.pages[_recherche_de_duillier(noeud, "date_extid")] = Page(
            f'<div class="tplDocumentConseil"><div>1 à 1 sur 1 éléments trouvés</div><div class="qs-edit" '
            f'data-qsedit-editnode="{noeud}"><a href="{DUILLIER}/n{noeud}1"><h5>Préavis 01-2026</h5></a></div></div>'
        )

    (duillier,), remarques = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)

    assert duillier["site"]["seances"] == f"{DUILLIER}/N500/documents-du-conseil.html"
    assert duillier["site"]["coreapi"] == PREAVIS_DUILLIER | {"noeud": 500, "tri": "date_extid"}
    assert remarques == {}


def test_une_commune_declaree_avec_une_seule_de_ses_deux_recherches_est_un_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau)
    (duillier,), _ = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)
    duillier["site"]["coreapi"] = PREAVIS_DUILLIER

    (ecart,) = verifier(_robot(reseau, horloge), _fichier(duillier), "quicksite", JOUR)

    assert ecart == (
        f"site-5715 (Duillier) : recherche coreapi déclarée {PREAVIS_DUILLIER}, "
        f"mesurée {[PREAVIS_DUILLIER, PROCES_VERBAUX_DUILLIER]}"
    )


def test_les_pages_des_deux_recherches_comptent_ensemble_face_au_plafond():
    # 30 pages de résultats par recherche : 62 requêtes au passage ordinaire, `robots.txt` et sonde compris, à tous
    # les niveaux (la recherche est lue en entier, même pour les seules Séances).
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _duillier(reseau, pages=30)

    (duillier,), remarques = brouillon(_robot(reseau, horloge), [CANDIDAT_DUILLIER], _fichier().plateformes[0], JOUR)

    assert remarques == {
        "site-5715": ["Duillier : 62 requêtes au passage ordinaire, au-delà du plafond de 60", DEUX_RECHERCHES_A_RELIRE]
    }
    assert duillier["conseil"]["donne"] == ["seances"]  # le moins complet de sa variante, à relire
