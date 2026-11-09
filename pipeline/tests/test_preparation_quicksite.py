"""Le script de préparation des sources sur Quicksite (`preparation_sources.py`, spec de J3, « Scripts de
préparation ») : la mesure du module de lecture Quicksite trouve la variante de chaque site (ancienne génération,
recherche `coreapi` et ses paramètres, module Conseil, module Conseil dont la liste est sur le site de la Ville),
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
