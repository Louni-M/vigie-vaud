"""Le script de préparation des sources (`preparation_sources.py`, spec de J3, « Scripts de préparation »), par ses
deux opérations : `verifier` (revérifie `sources.json` sans l'écrire) et `brouillon` (écrit le brouillon des sources
d'une plateforme). Le réseau est le faux réseau des sites (`faux_sites.Reseau`), qui sert l'échantillon i-web
enregistré (Préverenges, Blonay - Saint-Légier, Puidoux) et des pages du conseil fabriquées ; on observe les écarts
signalés, le brouillon écrit et les requêtes reçues par les sites (URL, User-Agent, heure).
"""

import copy
import csv
import html
import json
import re
from datetime import UTC, date, datetime

import httpx

import sites_communaux
from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau, echantillon
from mesure_sites import Mesure
from preparation_sources import Candidat, brouillon, candidats_du_recensement, verifier
from robot_communal import Robot
from schema import FichierSources

T0 = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)
JOUR = date(2026, 10, 23)  # la fenêtre du passage ordinaire part du 23 avril 2026

PREVERENGES = "https://www.preverenges.ch"
BLONAY = "https://www.blonay-saint-legier.ch"
PUIDOUX = "https://www.puidoux.ch"
OIOI = "https://www.exemple-oioi.ch"
LICENCE = "Actes officiels (art. 5 LDA) : métadonnées et liens seulement"

PLATEFORMES = [
    {
        "id": "i-web",
        "nom": "i-web",
        "editeur": "Innovative Web AG",
        "variantes": [
            {"id": "seances", "marqueur": "icmsTablePastSitzungen", "niveaux": [["seances"]]},
            {"id": "objets", "marqueur": "icmsTablePastSitzungen", "niveaux": [["objets", "seances"], ["seances"]]},
            {"id": "pages", "marqueur": "icmsTablePastSitzungen", "niveaux": [["preavis", "seances"], ["seances"]]},
        ],
    }
]


def _conseil_fabrique(liens, contenu=""):
    """Une page du conseil i-web, réduite à son menu (`liens` : chemin, texte) et à `contenu`."""
    menu = "".join(f'<li><a href="{chemin}">{texte}</a></li>' for chemin, texte in liens)
    return Page(
        '<html><body><nav class="icms-nav"><ul><li><a href="/_rtr/home">Accueil</a></li>'
        f"{menu}</ul></nav><div class=\"icms-content\"><h1>Conseil</h1>{contenu}</div></body></html>"
    )


MENU = [("/conseil", "Conseil communal"), ("/municipalite", "Municipalité"), ("/informations", "Actualités")]


def _reseau(horloge):
    """Les trois sites de l'échantillon i-web, sur le /24 d'i-web, avec la page du conseil de chacun."""
    reseau = Reseau(
        horloge,
        adresses={
            "www.preverenges.ch": "195.65.10.20",
            "www.blonay-saint-legier.ch": "195.65.10.22",
            "www.puidoux.ch": "195.65.10.23",
            "www.exemple-oioi.ch": "164.128.171.231",
        },
    )
    for variante in ("seances", "objets", "pages"):
        reseau.pages |= echantillon("i-web", variante)
    reseau.pages[f"{BLONAY}/conseil-communal"] = _conseil_fabrique(
        [*MENU, ("/seances", "Séances"), ("/objets-politiques", "Objets politiques")]
    )
    reseau.pages[f"{PUIDOUX}/conseil"] = _conseil_fabrique([*MENU, ("/seances", "Séances du Conseil")])
    reseau.pages[f"{OIOI}/conseil-general"] = Page(
        '<html><body><a href="/uploads/3f2a/documents/pv.pdf">PV</a> Réalisation OIOI web</body></html>'
    )
    return reseau


def _source(ofs, commune, page, site, conseil="Conseil communal", donne=("seances",)):
    de = f"d'{commune}" if commune[0] in "AEIOU" else f"de {commune}"
    source = {
        "id": f"site-{ofs}",
        "nom": f"{conseil} {de} (site de la commune)",
        "nom_court": f"Site {de}",
        "attribution": {"texte": f"Commune {de}", "lien": page, "licence": LICENCE},
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "scrape"},
        "conseil": {"body_key": str(ofs), "donne": list(donne)},
        "site": {"plateforme": "i-web", **site},
    }
    if site.get("variante") is None:
        source["couverture"] = {"communes": [ofs], "mode": "non_couvert", "raison": "preavis_seuls"}
        del source["conseil"]
    return source


SITE_PREVERENGES = _source(
    5643, "Préverenges", f"{PREVERENGES}/conseil",
    {"variante": "seances", "seances": f"{PREVERENGES}/sitzung", "membres": f"{PREVERENGES}/conseil"},
)
SITE_BLONAY = _source(
    5892, "Blonay - Saint-Légier", f"{BLONAY}/conseil-communal",
    {"variante": "objets", "seances": f"{BLONAY}/seances", "objets": f"{BLONAY}/objets-politiques"},
    donne=("objets", "seances"),
)
SITE_PUIDOUX = _source(
    5607, "Puidoux", f"{PUIDOUX}/conseil",
    {"variante": "pages", "seances": f"{PUIDOUX}/seances", "objets": f"{PUIDOUX}/seances"},
    donne=("preavis", "seances"),
)


def _fichier(*sources):
    return FichierSources.model_validate({"plateformes": PLATEFORMES, "sources": list(sources)})


def _robot(reseau, horloge):
    return Robot(httpx.Client(transport=reseau.transport()), horloge, horloge.attendre, reseau.resoudre)


def _verifier(reseau, horloge, *sources):
    return verifier(_robot(reseau, horloge), _fichier(*sources), "i-web", JOUR)


def _sans_marqueur(reseau, url):
    """La page de liste des Séances après une refonte : plus de tableau du module Séances."""
    reseau.pages[url] = Page("<html><body><div class='nouveau-site'>Séances du Conseil</div></body></html>")


def _seances_dans_la_fenetre(reseau, url, nombre):
    """La liste des Séances de Préverenges, avec `nombre` Séances passées de plus, toutes dans la fenêtre."""
    page = reseau.pages[url]
    texte = page.corps.decode("utf-8") if isinstance(page.corps, bytes) else page.corps

    def remplacer(m):
        donnees = json.loads(html.unescape(m[2]))
        donnees["data"] += [
            {"name": f'<a href="/_rte/anlass/{8000000 + i}">Séance</a>', "_datum": f"{1 + i % 28:02d}.09.2026, 20h00"}
            for i in range(nombre)
        ]
        return m[1] + html.escape(json.dumps(donnees), quote=True) + m[3]

    texte = re.sub(r'(<table[^>]*id="icmsTablePastSitzungen"[^>]*data-entities=")([^"]*)(")', remplacer, texte)
    reseau.pages[url] = Page(texte, entetes=page.entetes, gzip=page.gzip)


# --- Vérification -----------------------------------------------------------------------------------------------


def test_des_declarations_justes_ne_donnent_aucun_ecart():
    horloge = HorlogeFactice(T0)

    assert _verifier(_reseau(horloge), horloge, SITE_PREVERENGES, SITE_BLONAY, SITE_PUIDOUX) == []


def test_la_verification_passe_par_le_robot_une_requete_par_page_cinq_secondes_d_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)

    _verifier(reseau, horloge, SITE_PREVERENGES, SITE_BLONAY, SITE_PUIDOUX)

    urls = [r.url for r in reseau.journal]
    assert len(urls) == len(set(urls))
    assert {f"{PREVERENGES}/sitzung", f"{BLONAY}/objets-politiques", f"{PUIDOUX}/seances"} <= set(urls)
    assert not any("/_rte/anlass/" in u or "/_rte/information/" in u for u in urls)  # ni Séance ni Objet ouverts
    secondes = [(r.heure - T0).total_seconds() for r in reseau.journal]
    assert secondes == [5 * i for i in range(len(secondes))]  # un seul /24 : 5 s entre deux requêtes
    assert all(r.user_agent.startswith("VigieVaud-import ") for r in reseau.journal)


def test_une_page_des_seances_sans_le_marqueur_est_un_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _sans_marqueur(reseau, f"{PREVERENGES}/sitzung")

    assert _verifier(reseau, horloge, SITE_PREVERENGES) == [
        "site-5643 (Préverenges) : page des Séances déclarée https://www.preverenges.ch/sitzung, mesurée aucune"
    ]


def test_un_site_qui_n_est_pas_sur_la_plateforme_declaree_est_un_ecart():
    horloge = HorlogeFactice(T0)
    oioi = _source(5999, "Exemple", f"{OIOI}/conseil-general", {"variante": "seances", "seances": f"{OIOI}/seances"})

    assert _verifier(_reseau(horloge), horloge, oioi) == [
        "site-5999 (Exemple) : le site n'est pas sur i-web (aucune trace d'i-web sur https://www.exemple-oioi.ch"
        "/conseil-general)"
    ]


def test_une_page_du_conseil_non_lue_est_un_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    del reseau.pages[f"{PUIDOUX}/conseil"]

    assert _verifier(reseau, horloge, SITE_PUIDOUX) == [
        "site-5607 (Puidoux) : page du conseil https://www.puidoux.ch/conseil non lue (HTTP 404)"
    ]


def test_une_variante_ou_une_page_qui_ne_correspond_plus_au_site_est_un_ecart():
    horloge = HorlogeFactice(T0)
    seances_seules = copy.deepcopy(SITE_BLONAY)
    seances_seules["site"] = {"plateforme": "i-web", "variante": "seances", "seances": f"{BLONAY}/seances"}
    seances_seules["conseil"]["donne"] = ["seances"]
    membres = copy.deepcopy(SITE_PUIDOUX)
    membres["site"]["membres"] = f"{PUIDOUX}/conseil"

    assert _verifier(_reseau(horloge), horloge, seances_seules, membres) == [
        "site-5892 (Blonay - Saint-Légier) : variante déclarée seances, mesurée objets",
        "site-5892 (Blonay - Saint-Légier) : page des Objets déclarée aucune, mesurée "
        "https://www.blonay-saint-legier.ch/objets-politiques",
        "site-5607 (Puidoux) : page des membres déclarée https://www.puidoux.ch/conseil, mesurée aucune",
    ]


def test_une_commune_au_dela_du_plafond_de_60_requetes_est_un_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    # 3 Séances de la liste dans la fenêtre, et 28 de plus : chacune est lue par son lien stable, redirigé (2 requêtes) ;
    # avec robots.txt, la sonde, la liste et la page des membres (redirigée), 67 requêtes.
    _seances_dans_la_fenetre(reseau, f"{PREVERENGES}/sitzung", 28)

    assert _verifier(reseau, horloge, SITE_PREVERENGES) == [
        "site-5643 (Préverenges) : 67 requêtes au passage ordinaire, au-delà du plafond de 60"
    ]


def test_une_commune_non_couverte_dont_le_site_a_maintenant_ses_seances_est_un_ecart():
    horloge = HorlogeFactice(T0)
    non_couverte = _source(5607, "Puidoux", f"{PUIDOUX}/conseil", {})

    assert _verifier(_reseau(horloge), horloge, non_couverte) == [
        "site-5607 (Puidoux) : non couverte, mais une page des Séances est mesurée : https://www.puidoux.ch/seances"
    ]


# --- Brouillon --------------------------------------------------------------------------------------------------


def _candidats():
    return [
        Candidat(5643, "Préverenges", "Conseil communal", f"{PREVERENGES}/conseil"),
        Candidat(5892, "Blonay - Saint-Légier", "Conseil communal", f"{BLONAY}/conseil-communal"),
        Candidat(5607, "Puidoux", "Conseil communal", f"{PUIDOUX}/conseil"),
        Candidat(5999, "Exemple", "Conseil général", f"{OIOI}/conseil-general"),
    ]


def _preverenges_avec_menu(reseau):
    """La page du conseil de Préverenges (le bureau, en `personList`) avec le menu de son site."""
    url = f"{PREVERENGES}/conseil/29471"
    texte = reseau.pages[url].corps.decode("utf-8")
    menu = '<nav><a href="/sitzung">Séances</a> <a href="/preavis">Préavis</a> <a href="/municipalite">Municipalité</a></nav>'
    reseau.pages[url] = Page(texte.replace("<body>", "<body>" + menu, 1))
    reseau.pages[f"{PREVERENGES}/preavis"] = Page(
        '<html><body><div class="icms-content"><a href="/_rte/publikation/1">Préavis 2026</a></div></body></html>'
    )


def test_le_brouillon_declare_chaque_commune_de_la_plateforme_d_apres_son_site():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _preverenges_avec_menu(reseau)

    sources, remarques = brouillon(_robot(reseau, horloge), _candidats(), _fichier().plateformes[0], JOUR)

    assert sources == [SITE_PREVERENGES, SITE_BLONAY, SITE_PUIDOUX]
    assert remarques == {
        "site-5999": ["Exemple : pas sur i-web (aucune trace d'i-web sur https://www.exemple-oioi.ch/conseil-general),"
                      " non déclarée"],
    }


def test_une_commune_sans_page_des_seances_est_proposee_non_couverte_a_relire():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _sans_marqueur(reseau, f"{PUIDOUX}/seances")

    sources, remarques = brouillon(_robot(reseau, horloge), _candidats()[2:3], _fichier().plateformes[0], JOUR)

    assert sources == [_source(5607, "Puidoux", f"{PUIDOUX}/conseil", {}) | {
        "couverture": {"communes": [5607], "mode": "non_couvert", "raison": "rien_en_ligne"}
    }]
    assert remarques == {"site-5607": ["Puidoux : aucune page des Séances i-web trouvée ; raison à relire"]}


def test_le_brouillon_passe_la_verification_sans_ecart():
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    _preverenges_avec_menu(reseau)
    sources, _ = brouillon(_robot(reseau, horloge), _candidats(), _fichier().plateformes[0], JOUR)

    assert _verifier(reseau, horloge, *sources) == []


def test_les_candidats_du_recensement_sont_les_communes_de_la_plateforme_sauf_celles_qui_disparaissent(tmp_path):
    chemin = tmp_path / "sites-communaux.csv"
    with chemin.open("w", encoding="utf-8", newline="") as f:
        ecrire = csv.DictWriter(f, ["ofs", "commune", "conseil", "url_finale", "plateforme", "page_conseil"])
        ecrire.writeheader()
        ecrire.writerows([
            {"ofs": 5643, "commune": "Préverenges", "conseil": "conseil communal", "url_finale": PREVERENGES,
             "plateforme": "i-web", "page_conseil": f"{PREVERENGES}/conseil"},
            {"ofs": 5873, "commune": "Le Lieu", "conseil": "conseil communal", "url_finale": "https://www.lelieu.ch",
             "plateforme": "i-web", "page_conseil": "https://www.lelieu.ch/legislative"},
            {"ofs": 5843, "commune": "Rougemont", "conseil": "conseil communal", "url_finale": "https://rougemont.ch/",
             "plateforme": "i-web", "page_conseil": ""},
            {"ofs": 5401, "commune": "Aigle", "conseil": "conseil communal", "url_finale": "https://www.aigle.ch",
             "plateforme": "Quicksite", "page_conseil": "https://www.aigle.ch/N387/conseil-communal.html"},
        ])

    assert candidats_du_recensement(chemin, "i-web") == [
        Candidat(5643, "Préverenges", "Conseil communal", f"{PREVERENGES}/conseil"),
        Candidat(5843, "Rougemont", "Conseil communal", "https://rougemont.ch/"),  # sans page du conseil : l'accueil
    ]


# --- Une autre plateforme : son seul module de lecture ----------------------------------------------------------


class _ModuleExemple:
    """Le module de lecture d'une plateforme fictive, « exemple » : ce que Quicksite ajoutera, et rien d'autre. Sa
    page du conseil porte la trace `exemple-cms`, sa liste des Séances le marqueur `exemple-seances` ; une lecture
    coûte 3 requêtes au niveau « séances et préavis », 70 au niveau « objets et séances »."""

    @staticmethod
    def lire(robot, source, depuis):
        raise AssertionError("le script ne lit pas le conseil, il le mesure")

    @staticmethod
    def mesurer(pages, page_du_conseil, declare, plateforme):
        if "exemple-cms" not in (pages.texte(page_du_conseil) or ""):
            return Mesure("autre", remarques=["aucune trace d'exemple"])
        seances = page_du_conseil.rsplit("/", 1)[0] + "/seances"
        return Mesure(plateforme.id, variante="liste", seances=seances if pages.texte(seances) else None)

    @staticmethod
    def requetes(pages, source, depuis):
        return 70 if "objets" in source.conseil.donne else 3


def test_une_autre_plateforme_n_ajoute_que_son_module_de_lecture(monkeypatch):
    monkeypatch.setitem(sites_communaux.LECTEURS, "exemple", _ModuleExemple)
    horloge = HorlogeFactice(T0)
    reseau = Reseau(horloge, adresses={"www.exemple.ch": "203.0.113.5"})
    reseau.pages["https://www.exemple.ch/conseil"] = Page("<p class='exemple-cms'>Conseil</p>")
    reseau.pages["https://www.exemple.ch/seances"] = Page("<table class='exemple-seances'></table>")
    niveaux = [["objets", "seances"], ["preavis", "seances"], ["seances"]]
    (exemple,) = FichierSources.model_validate(
        {
            "plateformes": [
                {
                    "id": "exemple",
                    "nom": "Exemple",
                    "editeur": "Exemple SA",
                    "variantes": [{"id": "liste", "marqueur": "exemple-seances", "niveaux": niveaux}],
                }
            ],
            "sources": [],
        }
    ).plateformes
    candidat = Candidat(5999, "Exemple", "Conseil général", "https://www.exemple.ch/conseil")

    sources, remarques = brouillon(_robot(reseau, horloge), [candidat], exemple, JOUR)

    assert sources[0]["site"] == {"plateforme": "exemple", "variante": "liste", "seances": "https://www.exemple.ch/seances"}
    # Le niveau le plus complet dépasserait le plafond : la commune est déclarée au suivant, et le brouillon le dit.
    assert sources[0]["conseil"] == {"body_key": "5999", "donne": ["preavis", "seances"]}
    assert remarques == {
        "site-5999": [
            "Exemple : 72 requêtes au niveau objets + seances, au-delà du plafond de 60 ; déclarée au niveau "
            "preavis + seances"
        ]
    }
