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


def _issues(github, etiquette):
    return [i for i in github.issues if etiquette in [e["name"] for e in i["labels"]]]


def test_dans_github_l_issue_import_conseils_de_la_plateforme_liste_ses_communes_et_se_ferme_avec_la_derniere(
    tmp_path, horloge
):
    reseau, sources = _deux_communes(horloge)
    github = GitHubFactice()

    def passer(heure):
        with github.client() as client:
            _passer(tmp_path, horloge, reseau, sources, heure, IssuesGitHub(client, DEPOT_DONNEES, JETON))

    _illisible(reseau, LISTE_PREVERENGES)
    passer(T0)
    (issue,) = _issues(github, "import-conseils")
    assert issue["title"] == "Import en échec : i-web"
    assert issue["body"] == (
        "Aucun import du conseil de ces communes de i-web n'a réussi depuis plus de 24 h, ou aucun encore pour un "
        "conseil jamais importé :\n\n"
        "- Site de Préverenges (aucun import réussi)\n\n"
        "Le cron réessaie l'import à chaque passage ; le journal du workflow donne la cause de chaque échec. Une "
        "commune n'est pas en panne pour autant : le site garde ce qui a déjà été importé et seul le badge de "
        "fraîcheur vieillit. Le cron tient cette liste à jour à chaque passage et fermera l'issue au retour de la "
        "dernière commune.\n\n"
        "<!-- sources : site-5643 -->"
    )

    _illisible(reseau, LISTE_BLONAY)
    passer(J1)
    assert issue["commentaires"] == []  # à 24 h tout juste, Blonay n'y est pas encore
    passer(J1 + timedelta(minutes=30))
    assert "- Site de Blonay - Saint-Légier (dernier import réussi le 2026-10-23 à 05:17 UTC)\n" in issue["body"]
    assert issue["commentaires"] == ["Communes sans import réussi : Site de Préverenges, Site de Blonay - Saint-Légier."]

    _repare(reseau, LISTE_PREVERENGES)
    passer(J1 + timedelta(minutes=60))
    assert "Préverenges" not in issue["body"]
    assert issue["commentaires"][-1] == (
        "Communes sans import réussi : Site de Blonay - Saint-Légier.\nDe nouveau importées : Site de Préverenges."
    )

    _repare(reseau, LISTE_BLONAY)
    passer(J1 + timedelta(minutes=90))
    assert issue["state"] == "closed"
    assert issue["commentaires"][-1] == (
        "Le conseil de chaque commune de i-web est de nouveau importé.\n"
        "De nouveau importées : Site de Blonay - Saint-Légier."
    )
    # Une seule issue `import-conseils` pendant tout ce temps, et aucune par commune.
    assert [i["title"] for i in _issues(github, "import-conseils")] == ["Import en échec : i-web"]


# --- `a-verifier` par plateforme ----------------------------------------------------------------------------------


def _a_7_h_17(jour):
    """Le premier passage après 7 h à Lausanne (heure d'été), le `jour` donné."""
    return datetime(jour.year, jour.month, jour.day, 5, 17, tzinfo=UTC)


def test_a_verifier_s_ouvre_9_mois_apres_le_premier_import_d_un_conseil_sans_seance_et_pas_avant(tmp_path, horloge):
    # Un conseil général entre deux séances, qui n'en annonce plus aucune : sa liste reste vide.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [])
    sources = _sources(_opendata("5586"), SITE_PREVERENGES)
    issues = IssuesFactices()

    for jour in (T0, datetime(2027, 7, 22), datetime(2027, 7, 23)):
        _passer(tmp_path, horloge, reseau, sources, _a_7_h_17(jour), issues)
        if jour.year == 2027 and jour.day == 22:
            assert _de(issues, "a-verifier") == []

    assert _de(issues, "a-verifier") == [
        ("plateforme_touchee", "i-web", [("site-5643", "aucune Séance depuis le premier import, le 2026-10-23")]),
    ]
    # La Couverture ne change pas : la commune reste disponible.
    assert not [s for s in issues.signalements if s[1] == "panne-source"]


def test_a_verifier_compte_depuis_la_derniere_seance_annoncee_et_se_ferme_avec_une_nouvelle_seance(tmp_path, horloge):
    # La dernière Séance de l'échantillon est celle, annoncée, du 29 octobre 2026.
    reseau = _preverenges(horloge)
    sources = _sources(_opendata("5586"), SITE_PREVERENGES)
    github = GitHubFactice()

    def passer(jour):
        with github.client() as client:
            _passer(tmp_path, horloge, reseau, sources, _a_7_h_17(jour), IssuesGitHub(client, DEPOT_DONNEES, JETON))

    passer(T0)
    passer(datetime(2027, 7, 28))
    assert _issues(github, "a-verifier") == []

    passer(datetime(2027, 7, 29))
    (issue,) = _issues(github, "a-verifier")
    assert issue["title"] == "À vérifier : i-web"
    assert issue["body"] == (
        "Le site de ces communes de i-web ne montre aucune nouvelle Séance, tenue ou annoncée, depuis 9 mois :\n\n"
        "- Site de Préverenges (dernière Séance le 2026-10-29)\n\n"
        "La page de liste répond et se lit, mais elle est peut-être figée alors que le conseil publie ailleurs : à "
        "vérifier sur le site de la commune. La Couverture ne change pas. Le cron tient cette liste à jour à chaque "
        "passage et fermera l'issue quand la dernière commune aura de nouveau une Séance.\n\n"
        "<!-- sources : site-5643 -->"
    )
    passer(datetime(2027, 7, 30))
    assert len(_issues(github, "a-verifier")) == 1 and issue["commentaires"] == []

    # Le site annonce enfin une Séance.
    _liste_retouchee(
        reseau, lambda tableau, lignes: lignes + [_ligne(7500001, "02.09.2027")] if "Future" in tableau else lignes
    )
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7500001"] = _seance_fabriquee("7500002", "Ordre du jour")
    passer(datetime(2027, 7, 31))

    assert issue["state"] == "closed"
    assert issue["commentaires"] == [
        "Chaque commune de i-web a de nouveau une Séance de moins de 9 mois.\n"
        "Avec une nouvelle Séance : Site de Préverenges."
    ]
