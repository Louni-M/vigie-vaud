"""La déclaration des plateformes (`socle_lecture.PlateformeLue`, `sites_communaux.PLATEFORMES`) : une variante s'ajoute
à sa plateforme par sa seule déclaration (`VarianteLue`), que lisent le script de préparation des sources (mesure du
site, niveau, vérification), la sonde et l'import. Le réseau est le faux réseau des sites, qui sert une commune
fabriquée.
"""

import dataclasses
from datetime import UTC, date, datetime

import httpx
import pytest
from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau

import sites_communaux
from bruts import Bruts
from mesure_sites import Mesure
from preparation_sources import Candidat, brouillon, verifier
from robot_communal import Robot
from schema import FichierSources
from socle_lecture import VarianteLue, meeting
from sonde_sites import sonder_site

T0 = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)
JOUR = date(2026, 10, 23)
EXEMPLE = "https://www.exemple.ch"
MARQUEUR = "vvListeFactice"


def _lire_factice(robot, source, site, conseil, depuis):
    """La lecture de la variante factice : une Séance par page de liste, liée à cette page."""
    liste = robot.lire(site.seances, "import")
    return Bruts(conseil, seances=[meeting("Séance factice", date(2026, 10, 1), [], lien=liste.url)])


def _reconnaitre_factice(pages, url, texte, liens_du_conseil):
    """La page des Séances de la variante factice : celle qui porte son marqueur."""
    return Mesure(None, seances=url) if MARQUEUR in texte else None


FACTICE = VarianteLue(
    "factice",
    marqueur=MARQUEUR,
    niveaux=(("objets", "seances"), ("seances",)),
    lire=_lire_factice,
    reconnaitre=_reconnaitre_factice,
)

# La page du conseil d'une commune de chaque plateforme : la trace de la plateforme, et un lien vers la liste des
# Séances dans son menu.
CONSEILS = {
    "i-web": '<html><body><div class="icms-content"><a href="/seances">Séances du Conseil</a></div></body></html>',
    "quicksite": (
        '<html><head><meta name="generator" content="CMS - Quicksite www.quicksite.ch"></head><body>'
        '<nav><a href="/">Accueil</a><a href="/seances">Séances du Conseil</a></nav></body></html>'
    ),
}


def _ajouter_factice(monkeypatch, id_plateforme):
    """La variante factice, ajoutée à sa plateforme : sa déclaration, et rien d'autre."""
    plateforme = sites_communaux.PLATEFORMES[id_plateforme]
    avec_factice = dataclasses.replace(plateforme, variantes=(*plateforme.variantes, FACTICE))
    monkeypatch.setitem(sites_communaux.PLATEFORMES, id_plateforme, avec_factice)
    return avec_factice


def _commune(id_plateforme, liste=f"<table class='{MARQUEUR}'></table>"):
    horloge = HorlogeFactice(T0)
    reseau = Reseau(horloge, adresses={"www.exemple.ch": "203.0.113.5"})
    reseau.pages[f"{EXEMPLE}/conseil"] = Page(CONSEILS[id_plateforme])
    reseau.pages[f"{EXEMPLE}/seances"] = Page(f"<html><body>{liste}</body></html>")
    robot = Robot(httpx.Client(transport=reseau.transport()), horloge, horloge.attendre, reseau.resoudre)
    return reseau, robot


def _source(id_plateforme):
    """La source d'une commune déclarée dans la variante factice."""
    source = {
        "id": "site-5999",
        "nom": "Conseil communal d'Exemple (site de la commune)",
        "nom_court": "Site d'Exemple",
        "attribution": {"texte": "Commune d'Exemple", "lien": f"{EXEMPLE}/conseil", "licence": "LDA"},
        "voie_acces": "cron",
        "fraicheur": "import",
        "conseil": {"body_key": "5999", "donne": ["seances"]},
        "site": {"plateforme": id_plateforme, "variante": "factice", "seances": f"{EXEMPLE}/seances"},
    }
    return FichierSources.model_validate({"sources": [source]}).sources[0]


@pytest.mark.parametrize("id_plateforme", ["i-web", "quicksite"])
def test_une_variante_factice_ne_demande_que_sa_declaration(monkeypatch, id_plateforme):
    plateforme = _ajouter_factice(monkeypatch, id_plateforme)
    _, robot = _commune(id_plateforme)
    candidat = Candidat(5999, "Exemple", "Conseil communal", f"{EXEMPLE}/conseil")

    # Le script de préparation la mesure : sa page des Séances, reconnue, et son niveau le plus complet, sous le plafond.
    [declaree], remarques = brouillon(robot, [candidat], plateforme, JOUR)
    assert remarques == {}
    assert declaree["site"] == {"plateforme": id_plateforme, "variante": "factice", "seances": f"{EXEMPLE}/seances"}
    assert declaree["conseil"] == {"body_key": "5999", "donne": ["objets", "seances"]}
    # puis la revérifie sans écart.
    fichier = FichierSources.model_validate({"sources": [declaree]})
    assert verifier(robot, fichier, id_plateforme, JOUR) == []

    # La sonde cherche son marqueur, et l'import la lit.
    (source,) = fichier.sources
    assert sonder_site(robot, source) is None
    bruts = sites_communaux.lire_site(robot, source, JOUR)
    assert [s["url_external"] for s in bruts.seances] == [{"fr": f"{EXEMPLE}/seances"}]


@pytest.mark.parametrize("id_plateforme", ["i-web", "quicksite"])
def test_sans_son_marqueur_la_variante_factice_n_est_ni_mesuree_ni_sondee(monkeypatch, id_plateforme):
    plateforme = _ajouter_factice(monkeypatch, id_plateforme)
    _, robot = _commune(id_plateforme, liste="<table class='refonte'></table>")
    candidat = Candidat(5999, "Exemple", "Conseil communal", f"{EXEMPLE}/conseil")
    source = _source(id_plateforme)

    [declaree], _ = brouillon(robot, [candidat], plateforme, JOUR)

    assert declaree["couverture"]["mode"] == "non_couvert"
    assert sonder_site(robot, source) == "marqueur absent"


def test_une_variante_que_sa_plateforme_ne_declare_pas_n_est_pas_lue():
    _, robot = _commune("i-web")
    source = _source("i-web")

    assert sonder_site(robot, source) == "variante i-web/factice non déclarée"
    with pytest.raises(ValueError, match="variante factice non déclarée dans i-web"):
        sites_communaux.lire_site(robot, source, JOUR)
    with pytest.raises(ValueError, match="variante i-web factice non lue"):
        sites_communaux.PLATEFORMES["i-web"].lire(robot, source, None)
