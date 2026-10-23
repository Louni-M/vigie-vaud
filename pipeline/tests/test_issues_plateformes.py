"""Les issues `import-conseils` et `a-verifier` par plateforme (spec de J3, « Issues par plateforme »), observées par
le passage du cron : les issues signalées au faux client d'issues, ou tenues par le GitHub factice.

Pour les communes scrapées, chaque sorte d'issue s'ouvre par plateforme (« Import en échec : i-web », « À vérifier :
i-web »), avec la liste des communes touchées, tenue à jour à chaque passage, et se ferme au retour de la dernière,
comme l'issue `panne-source` de la plateforme. Les conseils d'OpenParlData gardent leurs issues par source.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from cron import IssuesGitHub, passage
from faux_openparldata import HorlogeFactice
from faux_sites import Page, echantillon
from test_cron import DEPOT_DONNEES, JETON, GitHubFactice, IssuesFactices
from test_sites_communaux import (
    BLONAY,
    PREVERENGES,
    SITE_PREVERENGES,
    T0,
    _ligne,
    _liste_retouchee,
    _monde,
    _opendata,
    _preverenges,
    _seance_fabriquee,
    _site,
    _sources,
)

LISTE_PREVERENGES = f"{PREVERENGES}/sitzung"
LISTE_BLONAY = f"{BLONAY}/seances"
SITE_BLONAY = _site(5892, "Blonay - Saint-Légier", LISTE_BLONAY, f"{BLONAY}/conseil-communal")
J1 = T0 + timedelta(days=1)


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def _passer(depot, horloge, reseau, sources, heure, issues):
    horloge.heure = heure
    with httpx.Client(transport=reseau.transport(repli=_monde(horloge).transport())) as client:
        passage(
            depot, sources, client, horloge=horloge, issues=issues, attendre=horloge.attendre, resoudre=reseau.resoudre
        )


def _deux_communes(horloge):
    """Préverenges et Blonay - Saint-Légier, deux communes i-web, sur deux réseaux, et Lausanne par OpenParlData."""
    reseau = _preverenges(horloge)
    reseau.adresses["www.blonay-saint-legier.ch"] = "193.34.137.9"
    reseau.pages |= echantillon("i-web", "objets")
    return reseau, _sources(_opendata("5586"), SITE_PREVERENGES, SITE_BLONAY)


def _illisible(reseau, url):
    """Une page de liste qui porte encore le marqueur de la sonde, mais plus le tableau des Séances : la sonde
    réussit, l'import échoue."""
    reseau.pages[url] = Page('<div class="icmsTablePastSitzungen">Rien à lire</div>')


def _repare(reseau, url):
    reseau.pages[url] = (echantillon("i-web", "seances") | echantillon("i-web", "objets"))[url]


def _de(issues, etiquette):
    """Les signalements par plateforme d'une sorte d'issue, sans l'étiquette."""
    return [(s[0], *s[2:]) for s in issues.signalements if "plateforme" in s[0] and s[1] == etiquette]


# --- `import-conseils` par plateforme -----------------------------------------------------------------------------


def test_l_issue_import_conseils_d_une_plateforme_s_ouvre_avec_la_premiere_commune_et_se_ferme_avec_la_derniere(
    tmp_path, horloge
):
    reseau, sources = _deux_communes(horloge)
    issues = IssuesFactices()

    def passer(heure):
        _passer(tmp_path, horloge, reseau, sources, heure, issues)

    # Jour 0 : Préverenges, jamais importée, échoue dès son premier import ; Blonay est importée.
    _illisible(reseau, LISTE_PREVERENGES)
    passer(T0)
    # Jour 1 : Blonay échoue à son tour ; à 24 h passées de son dernier import, elle entre dans la liste.
    _illisible(reseau, LISTE_BLONAY)
    passer(J1)
    passer(J1 + timedelta(minutes=30))
    # Préverenges revient (sans retour signalé), puis Blonay.
    _repare(reseau, LISTE_PREVERENGES)
    passer(J1 + timedelta(minutes=60))
    _repare(reseau, LISTE_BLONAY)
    passer(J1 + timedelta(minutes=90))

    # Le client factice ne voit pas les issues : le passage les déduit des imports relus, comme pour une source. Une
    # commune jamais importée est donc signalée à chaque passage, et son premier import réussi passe sans retour.
    aucun = "aucun import réussi"
    blonay = "dernier import réussi le 2026-10-23 à 05:17 UTC"
    assert _de(issues, "import-conseils") == [
        ("plateforme_touchee", "i-web", [("site-5643", aucun)]),
        ("plateforme_touchee", "i-web", [("site-5643", aucun)]),
        ("liste_plateforme", "i-web", [("site-5643", aucun), ("site-5892", blonay)], []),
        ("retour_plateforme", "i-web", ["site-5892"]),
    ]
    # Les communes n'ont pas d'issue `import-conseils` à elles ; Lausanne, importée, n'en a pas non plus.
    assert not [s for s in issues.signalements if s[0] == "import_en_echec"]
