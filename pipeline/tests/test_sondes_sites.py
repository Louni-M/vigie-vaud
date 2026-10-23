"""La sonde des sites communaux et les pannes par plateforme (spec de J3, « Sondes et pannes des sites » et « Issues
par plateforme »), observées par le passage du cron : `etat-sources.json`, les requêtes reçues par les sites (URL,
User-Agent, heure), les fichiers d'import et les issues signalées au faux client d'issues.

Une commune scrapée est sondée une fois par jour, juste avant son import : la sonde lit sa page de liste
(`site.seances`) par le robot communal et y cherche le marqueur de sa variante, déclaré dans `plateformes`.
"""

import json
from datetime import timedelta

import httpx
import pytest

from cron import IssuesGitHub, passage
from faux_openparldata import HorlogeFactice
from faux_sites import DELAI, REFUS, Page, echantillon
from test_cron import DEPOT_DONNEES, JETON, GitHubFactice, IssuesFactices
from test_sites_communaux import (
    BLONAY,
    PREVERENGES,
    SITE_PREVERENGES,
    T0,
    _liste_retouchee,
    _monde,
    _opendata,
    _preverenges,
    _site,
    _sources,
)

UA_SONDE = "VigieVaud-sonde (+https://louni-m.github.io/vigie-vaud/a-propos#robot; vigievaud.gentile263@passinbox.com)"
LISTE = f"{PREVERENGES}/sitzung"
ROBOTS = f"{PREVERENGES}/robots.txt"
S = timedelta(seconds=1)
SITE_BLONAY = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def _passer(depot, horloge, reseau, sources=None, heure=None, issues=None):
    horloge.heure = heure or horloge.heure
    issues = issues if issues is not None else IssuesFactices()
    with httpx.Client(transport=reseau.transport(repli=_monde(horloge).transport())) as client:
        passage(
            depot,
            sources or _sources(_opendata("5586"), SITE_PREVERENGES),
            client,
            horloge=horloge,
            issues=issues,
            attendre=horloge.attendre,
            resoudre=reseau.resoudre,
        )
    return issues


def _lire(depot, chemin):
    return json.loads((depot / chemin).read_text(encoding="utf-8"))


def _etat(depot, source="site-5643"):
    return _lire(depot, "etat-sources.json")["sources"].get(source)


def _importe(depot, cle="5643"):
    return _lire(depot, "conseils/import.json")["conseils"].get(cle)


def _sans_marqueur(reseau, url=LISTE):
    """La page de liste après une refonte : le tableau des Séances passées a changé d'identifiant."""
    page = reseau.pages[url]
    texte = page.corps.decode("utf-8").replace("icmsTablePastSitzungen", "tableauSeances")
    reseau.pages[url] = Page(texte, entetes=page.entetes, gzip=True)


def _pannes(github):
    """Les issues `panne-source` du GitHub factice (une commune jamais importée a aussi son issue `import-conseils`)."""
    return [i for i in github.issues if "panne-source" in [e["name"] for e in i["labels"]]]


def _deux_communes(horloge):
    """Préverenges et Blonay - Saint-Légier, deux communes i-web, sur deux réseaux."""
    reseau = _preverenges(horloge)
    reseau.adresses["www.blonay-saint-legier.ch"] = "193.34.137.9"
    reseau.pages |= echantillon("i-web", "objets")
    return reseau, _sources(_opendata("5586"), SITE_PREVERENGES, SITE_BLONAY)


def test_la_sonde_lit_la_page_de_liste_sous_le_nom_vigievaud_sonde_avant_l_import(tmp_path, horloge):
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau)

    sonde, import_ = reseau.journal[1], reseau.journal[2]
    assert (sonde.url, sonde.user_agent, sonde.heure) == (LISTE, UA_SONDE, T0 + timedelta(seconds=5))
    assert (import_.url, import_.user_agent.split(" ")[0], import_.heure) == (
        LISTE,
        "VigieVaud-import",
        T0 + timedelta(seconds=10),
    )
    assert _etat(tmp_path) == {
        "etat": "disponible",
        "depuis": "2026-10-23T05:17:05Z",
        "derniere_sonde": "2026-10-23T05:17:05Z",
        "dernier_succes": "2026-10-23T05:17:05Z",
        "echecs_consecutifs": 0,
        "motif": None,
    }
    assert _importe(tmp_path) == "2026-10-23T05:17:05Z"


def test_un_marqueur_absent_saute_l_import_du_jour_et_deux_echecs_mettent_la_commune_en_panne(
    tmp_path, horloge, capsys
):
    # Une refonte du site : la page répond, mais sans le tableau que lit le module i-web.
    reseau = _preverenges(horloge)
    _sans_marqueur(reseau)

    _passer(tmp_path, horloge, reseau)

    assert [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal] == [(ROBOTS, "VigieVaud-sonde"), (LISTE, "VigieVaud-sonde")]
    assert _etat(tmp_path) == {
        "etat": "disponible",
        "depuis": None,
        "derniere_sonde": "2026-10-23T05:17:05Z",
        "dernier_succes": None,
        "echecs_consecutifs": 1,
        "motif": "marqueur absent",
    }
    assert _importe(tmp_path) is None
    assert _importe(tmp_path, "5586") == "2026-10-23T05:17:05Z"  # OpenParlData n'en souffre pas
    assert "Import sauté : Conseil communal de Préverenges (site de la commune) (sonde en échec : marqueur absent)" in (
        capsys.readouterr().err
    )

    # Au passage suivant, la sonde est refaite ; second échec : la commune est en panne depuis la première.
    reseau.journal.clear()
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=30))

    assert [r.url for r in reseau.journal] == [ROBOTS, LISTE]
    etat = _etat(tmp_path)
    assert (etat["etat"], etat["depuis"], etat["echecs_consecutifs"]) == ("en_panne", "2026-10-23T05:17:05Z", 2)
    assert _importe(tmp_path) is None


@pytest.mark.parametrize(
    ("page", "motif"),
    [
        (Page("", statut=503), "HTTP 503"),
        (Page("introuvable", statut=404), "HTTP 404"),
        (DELAI, "délai dépassé"),
        (REFUS, "site injoignable"),
        # Compression annoncée, corps qui n'en est pas une : la page arrive mais ne se lit pas.
        (
            Page("icmsTablePastSitzungen", entetes={"Content-Type": "text/html", "Content-Encoding": "gzip"}),
            "page illisible",
        ),
    ],
    ids=["503", "404", "delai", "refus", "illisible"],
)
def test_une_page_de_liste_en_erreur_est_un_echec_de_la_sonde_qui_dit_son_motif(tmp_path, horloge, page, motif):
    reseau = _preverenges(horloge)
    reseau.pages[LISTE] = page

    _passer(tmp_path, horloge, reseau)

    assert (_etat(tmp_path)["echecs_consecutifs"], _etat(tmp_path)["motif"]) == (1, motif)
    assert len(reseau.journal) == 2  # robots.txt, puis la page de liste
    assert _importe(tmp_path) is None


def test_une_liste_vide_n_est_pas_une_panne(tmp_path, horloge):
    # Un conseil général entre deux séances : le tableau est là, sans ligne.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [])

    _passer(tmp_path, horloge, reseau)

    assert (_etat(tmp_path)["etat"], _etat(tmp_path)["echecs_consecutifs"]) == ("disponible", 0)
    assert _importe(tmp_path) == "2026-10-23T05:17:05Z"


def test_une_liste_illisible_met_l_import_en_echec_sans_panne_et_n_est_pas_resondee_le_meme_jour(tmp_path, horloge):
    # Aucune ligne ne se lit, mais le tableau est là : la sonde réussit, l'import échoue et sera refait.
    reseau = _preverenges(horloge)
    _liste_retouchee(
        reseau, lambda tableau, lignes: [{"name": "Séance", "_datum": ligne["_datum"]} for ligne in lignes]
    )

    _passer(tmp_path, horloge, reseau)
    reseau.journal.clear()
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=30))

    assert _etat(tmp_path)["etat"] == "disponible"
    assert _etat(tmp_path)["derniere_sonde"] == "2026-10-23T05:17:05Z"
    assert [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal] == [(ROBOTS, "VigieVaud-import"), (LISTE, "VigieVaud-import")]
    assert _importe(tmp_path) is None


def test_une_commune_n_est_sondee_qu_une_fois_par_jour_juste_avant_son_import(tmp_path, horloge):
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau)
    for minutes in (30, 60, 23 * 60):  # jusqu'à 6 h 17 le lendemain, avant 7 h : rien
        _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=minutes))
    du_premier_jour = list(reseau.journal)
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(days=1))

    sondes = [r.heure for r in reseau.journal if r.url == LISTE and r.user_agent.startswith("VigieVaud-sonde")]
    assert sondes == [T0 + 5 * S, T0 + timedelta(days=1) + 5 * S]  # après robots.txt
    assert [r.heure for r in du_premier_jour if r.url == LISTE] == [T0 + 5 * S, T0 + 10 * S]
    assert _etat(tmp_path)["derniere_sonde"] == "2026-10-24T05:17:05Z"


def test_une_commune_sondee_a_un_passage_precedent_garde_son_etat_dans_etat_sources(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _passer(tmp_path, horloge, reseau)
    etat = _etat(tmp_path)

    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(hours=3))

    assert _etat(tmp_path) == etat
    assert _lire(tmp_path, "etat-sources.json")["genere"] == "2026-10-23T08:17:00Z"


def test_une_commune_revient_a_la_premiere_sonde_reussie_et_son_import_reprend(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _sans_marqueur(reseau)
    _passer(tmp_path, horloge, reseau)
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=30))

    reseau.pages |= echantillon("i-web", "seances")  # le site réparé, ou la PR qui corrige le scraper
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=60))

    assert _etat(tmp_path) == {
        "etat": "disponible",
        "depuis": "2026-10-23T06:17:05Z",
        "derniere_sonde": "2026-10-23T06:17:05Z",
        "dernier_succes": "2026-10-23T06:17:05Z",
        "echecs_consecutifs": 0,
        "motif": None,
    }
    assert _importe(tmp_path) is not None


def test_une_source_communale_sans_conseil_n_est_pas_sondee(tmp_path, horloge):
    # Une commune non couverte d'une plateforme retenue (#154) a son bloc `site`, mais ni conseil ni sonde.
    reseau = _preverenges(horloge)
    sans_conseil = {k: v for k, v in SITE_PREVERENGES.items() if k != "conseil"}

    _passer(tmp_path, horloge, reseau, sources=_sources(_opendata("5586"), sans_conseil))

    assert reseau.journal == []
    assert _etat(tmp_path) is None


# --- Une issue `panne-source` par plateforme --------------------------------------------------------------------------


def test_une_seule_issue_par_plateforme_ouverte_avec_la_premiere_commune_tenue_a_jour_et_fermee_avec_la_derniere(
    tmp_path, horloge
):
    reseau, sources = _deux_communes(horloge)
    issues = IssuesFactices()
    J1 = T0 + timedelta(days=1)

    def passer(heure):
        _passer(tmp_path, horloge, reseau, sources=sources, heure=heure, issues=issues)

    # Jour 0 : Préverenges est refondue, en panne au second passage ; Blonay est importée.
    _sans_marqueur(reseau)
    passer(T0)
    passer(T0 + timedelta(minutes=30))
    # Jour 1 : Blonay est refondue à son tour ; Préverenges revient, puis Blonay.
    _sans_marqueur(reseau, f"{BLONAY}/seances")
    passer(J1)
    passer(J1 + timedelta(minutes=30))
    reseau.pages[LISTE] = echantillon("i-web", "seances")[LISTE]
    passer(J1 + timedelta(minutes=60))
    reseau.pages[f"{BLONAY}/seances"] = echantillon("i-web", "objets")[f"{BLONAY}/seances"]
    passer(J1 + timedelta(minutes=90))

    plateformes = [s for s in issues.signalements if s[0].endswith("_plateforme")]
    assert plateformes == [
        ("panne_plateforme", "i-web", [("site-5643", "2026-10-23T05:17:05+00:00")]),
        (
            "liste_plateforme",
            "i-web",
            [("site-5643", "2026-10-23T05:17:05+00:00"), ("site-5892", "2026-10-24T05:17:10+00:00")],
            [],
        ),
        ("liste_plateforme", "i-web", [("site-5892", "2026-10-24T05:17:10+00:00")], ["site-5643"]),
        ("retour_plateforme", "i-web", ["site-5892"]),
    ]
    # Les communes n'ont pas d'issue `panne-source` à elles.
    assert not [s for s in issues.signalements if s[0] in ("panne", "retour")]


def test_dans_github_l_issue_de_la_plateforme_liste_les_communes_en_panne_et_se_ferme_au_retour_de_la_derniere(
    tmp_path, horloge
):
    reseau, sources = _deux_communes(horloge)
    github = GitHubFactice()
    J1 = T0 + timedelta(days=1)

    def passer(heure):
        with github.client() as client:
            issues = IssuesGitHub(client, DEPOT_DONNEES, JETON)
            _passer(tmp_path, horloge, reseau, sources=sources, heure=heure, issues=issues)

    _sans_marqueur(reseau)
    passer(T0)
    passer(T0 + timedelta(minutes=30))
    (issue,) = _pannes(github)
    assert (issue["title"], [e["name"] for e in issue["labels"]]) == ("Panne : i-web", ["panne-source"])
    assert issue["body"] == (
        "La sonde du site de ces communes de i-web échoue :\n\n"
        "- Site de Préverenges (depuis le 2026-10-23 à 05:17 UTC, marqueur absent)\n\n"
        "Tant que la sonde d'une commune échoue, son import du jour est sauté ; le site garde ce qui a déjà été "
        "importé. Le cron tient cette liste à jour à chaque passage et fermera l'issue au retour de la dernière "
        "commune.\n\n"
        "<!-- sources : site-5643 -->"
    )

    _sans_marqueur(reseau, f"{BLONAY}/seances")
    passer(J1)
    passer(J1 + timedelta(minutes=30))
    assert "- Site de Préverenges (depuis le 2026-10-23 à 05:17 UTC, marqueur absent)\n" in issue["body"]
    assert "- Site de Blonay - Saint-Légier (depuis le 2026-10-24 à 05:17 UTC, marqueur absent)\n" in issue["body"]
    assert issue["commentaires"] == ["Communes en panne : Site de Préverenges, Site de Blonay - Saint-Légier."]

    reseau.pages[LISTE] = echantillon("i-web", "seances")[LISTE]
    passer(J1 + timedelta(minutes=60))
    assert "Préverenges" not in issue["body"]
    assert issue["commentaires"][-1] == (
        "Communes en panne : Site de Blonay - Saint-Légier.\nDe nouveau disponibles : Site de Préverenges."
    )

    reseau.pages[f"{BLONAY}/seances"] = echantillon("i-web", "objets")[f"{BLONAY}/seances"]
    passer(J1 + timedelta(minutes=90))
    assert issue["state"] == "closed"
    assert issue["commentaires"][-1] == (
        "Plus aucune commune de i-web n'est en panne : Site de Blonay - Saint-Légier de nouveau disponible(s)."
    )
    assert len(_pannes(github)) == 1


def test_une_liste_que_l_api_github_n_a_pas_laisse_mettre_a_jour_l_est_au_passage_suivant(tmp_path, horloge):
    reseau, sources = _deux_communes(horloge)
    github = GitHubFactice()
    J1 = T0 + timedelta(days=1)

    def passer(heure):
        with github.client() as client:
            issues = IssuesGitHub(client, DEPOT_DONNEES, JETON)
            _passer(tmp_path, horloge, reseau, sources=sources, heure=heure, issues=issues)

    _sans_marqueur(reseau)
    _sans_marqueur(reseau, f"{BLONAY}/seances")
    passer(T0)
    passer(T0 + timedelta(minutes=30))
    reseau.pages[LISTE] = echantillon("i-web", "seances")[LISTE]
    github.hors_service = True
    passer(T0 + timedelta(minutes=60))  # Préverenges revient, l'issue n'est pas mise à jour

    github.hors_service = False
    passer(T0 + timedelta(minutes=90))

    (issue,) = _pannes(github)
    assert issue["body"].endswith("<!-- sources : site-5892 -->")
    assert issue["state"] == "open"


def test_les_issues_des_sources_openparldata_restent_par_source(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _sans_marqueur(reseau)
    # La sonde d'OpenParlData ne passe pas par le robot : elle reçoit une 503 du même faux réseau.
    reseau.adresses["sonde.exemple.ch"] = "192.0.2.1"
    reseau.pages["https://sonde.exemple.ch/bodies"] = Page("", statut=503)
    sondee = _opendata("5586") | {"sonde": {"url": "https://sonde.exemple.ch/bodies", "delai": 20, "champs": ["id"]}}
    issues = IssuesFactices()
    sources = _sources(sondee, SITE_PREVERENGES)

    for minutes in (0, 30):
        _passer(tmp_path, horloge, reseau, sources=sources, heure=T0 + timedelta(minutes=minutes), issues=issues)

    assert [s[:2] for s in issues.signalements if s[0] in ("panne", "panne_plateforme")] == [
        ("panne", "openparldata-5586"),
        ("panne_plateforme", "i-web"),
    ]
