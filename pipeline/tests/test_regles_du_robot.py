"""Les règles du robot communal (ADR 0006 ; spec de J3, « Robot communal »), observées par le passage du cron : les
requêtes reçues par les sites (URL, User-Agent, heure), `etat-sources.json`, les fichiers d'import, le journal et
les issues signalées au faux client d'issues.

- `robots.txt` est lu une fois par hôte et par passage, avant la sonde (RFC 9309 : une erreur 4xx permet tout, une
  erreur 5xx interdit tout), pour le nom `VigieVaud`, sinon `*` ;
- `Crawl-delay` plus grand que 5 s, et l'intervalle de la section `reseaux` de `sources.json`, espacent les requêtes ;
- une 429, une 503, une connexion refusée ou un délai dépassé bloque le /24 jusqu'à la fin du passage (ou plus si
  `Retry-After`) ; au passage suivant, une seule sonde teste le réseau ;
- 60 requêtes au plus par commune et par passage ordinaire.
"""

from datetime import timedelta

import httpx
import pytest

from cron import passage
from faux_openparldata import HorlogeFactice
from faux_sites import DELAI, REFUS, Page, echantillon
from schema import FichierSources
from test_cron import IssuesFactices
from test_sites_communaux import (
    BLONAY,
    PLATEFORMES,
    PREVERENGES,
    SITE_PREVERENGES,
    T0,
    _ligne,
    _liste_retouchee,
    _monde,
    _opendata,
    _preverenges,
    _site,
    _sources,
)
from test_sondes_sites import LISTE, UA_SONDE, _etat, _importe, _lire, _passer

ROBOTS = f"{PREVERENGES}/robots.txt"
S = timedelta(seconds=1)


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def _robots(reseau, texte, statut=200):
    reseau.pages[ROBOTS] = Page(texte, statut=statut, entetes={"Content-Type": "text/plain"})


def _lues(reseau, hote=PREVERENGES):
    """Les requêtes reçues par un site : (chemin, secondes depuis T0, rôle)."""
    return [
        (r.url.removeprefix(hote), (r.heure - T0) / S, r.user_agent.split(" ")[0].removeprefix("VigieVaud-"))
        for r in reseau.journal
        if r.url.startswith(hote)
    ]


# --- robots.txt -----------------------------------------------------------------------------------------------------


def test_robots_txt_est_lu_avant_la_sonde_et_une_erreur_4xx_permet_tout(tmp_path, horloge):
    reseau = _preverenges(horloge)  # le faux site n'a pas de robots.txt : 404

    _passer(tmp_path, horloge, reseau)

    assert _lues(reseau)[:3] == [("/robots.txt", 0, "sonde"), ("/sitzung", 5, "sonde"), ("/sitzung", 10, "import")]
    assert reseau.journal[0].user_agent == UA_SONDE
    assert [r.url for r in reseau.journal].count(ROBOTS) == 1
    assert _etat(tmp_path)["echecs_consecutifs"] == 0
    assert _importe(tmp_path) is not None


def test_une_erreur_5xx_de_robots_txt_interdit_tout_et_la_page_de_liste_n_est_pas_demandee(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    _robots(reseau, "", statut=500)

    _passer(tmp_path, horloge, reseau)

    assert _lues(reseau) == [("/robots.txt", 0, "sonde")]
    assert (_etat(tmp_path)["echecs_consecutifs"], _etat(tmp_path)["motif"]) == (1, "robots.txt en erreur (HTTP 500)")
    assert _importe(tmp_path) is None
    assert "Import sauté : Conseil communal de Préverenges (site de la commune)" in capsys.readouterr().err


@pytest.mark.parametrize(
    "robots",
    [
        "User-agent: VigieVaud\nDisallow: /sitzung\n",
        "User-agent: vigievaud\nUser-agent: Googlebot\nDisallow: /\n",
        "User-agent: *\nDisallow: /\n",
        # Le groupe de `VigieVaud` l'emporte sur celui de `*`, même plus permissif.
        "User-agent: *\nAllow: /\n\nUser-agent: VigieVaud\nDisallow: /sitzung$\n",
    ],
    ids=["vigievaud", "casse-et-groupe-partage", "tous", "groupe-propre"],
)
def test_une_page_de_liste_interdite_n_est_jamais_demandee_et_le_site_refuse_les_robots(tmp_path, horloge, robots):
    reseau = _preverenges(horloge)
    _robots(reseau, robots)

    _passer(tmp_path, horloge, reseau)
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(minutes=30))

    assert LISTE not in [r.url for r in reseau.journal]
    etat = _etat(tmp_path)
    assert (etat["etat"], etat["motif"]) == ("en_panne", "le site refuse les robots")
    assert _importe(tmp_path) is None


@pytest.mark.parametrize(
    "robots",
    [
        # Les interdictions faites nommément aux robots d'IA ne visent pas Vigie Vaud.
        "User-agent: GPTBot\nDisallow: /\n\nUser-agent: CCBot\nDisallow: /\n",
        # Le plus long motif l'emporte : la liste est permise malgré `Disallow: /`.
        "User-agent: *\nDisallow: /\nAllow: /sitzung\nAllow: /_rte/anlass/\n",
        # Un motif `*` qui ne vise que les recherches.
        "User-agent: *\nDisallow: /*?suche=\n",
    ],
    ids=["robots-d-ia", "plus-long-motif", "joker"],
)
def test_une_page_permise_est_lue(tmp_path, horloge, robots):
    reseau = _preverenges(horloge)
    _robots(reseau, robots)

    _passer(tmp_path, horloge, reseau)

    assert _etat(tmp_path)["echecs_consecutifs"] == 0
    assert _importe(tmp_path) is not None


def test_un_document_interdit_garde_son_lien_sans_etre_ouvert(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _robots(reseau, "User-agent: *\nDisallow: /_doc/\n")

    _passer(tmp_path, horloge, reseau)

    assert not any("/_doc/" in r.url for r in reseau.journal)
    documents = _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")["documents"]
    assert [d["lien"] for d in documents] == [f"{PREVERENGES}/_doc/{n}" for n in (7223149, 7223152, 7223158, 7223161)]


def test_une_page_de_seance_interdite_apres_redirection_n_est_pas_demandee_et_la_seance_est_sautee(
    tmp_path, horloge, capsys
):
    # Le lien stable `/_rte/anlass/6987205` est permis, mais il renvoie à `/sitzung/6987205`, interdite.
    reseau = _preverenges(horloge)
    _robots(reseau, "User-agent: *\nDisallow: /sitzung/\n")

    _passer(tmp_path, horloge, reseau)

    assert f"{PREVERENGES}/sitzung/6987205" not in [r.url for r in reseau.journal]
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]] == [
        "5643/2026-10-29",
        "5643/2026-06-18",
    ]
    assert "/sitzung/6987205 : interdite par robots.txt" in capsys.readouterr().err
    assert _importe(tmp_path) is not None


# --- Débit : Crawl-delay et section `reseaux` -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("robots", "intervalle"),
    [
        ("User-agent: *\nCrawl-delay: 12\n", 12),
        ("User-agent: *\nCrawl-delay: 30\n\nUser-agent: VigieVaud\nCrawl-delay: 8\n", 8),
        ("User-agent: *\nCrawl-delay: 2\n", 5),  # jamais moins que 5 s
    ],
    ids=["plus-grand", "groupe-vigievaud", "plus-petit"],
)
def test_un_crawl_delay_plus_grand_que_5_s_espace_les_requetes(tmp_path, horloge, robots, intervalle):
    reseau = _preverenges(horloge)
    _robots(reseau, robots)

    _passer(tmp_path, horloge, reseau)

    heures = [secondes for _, secondes, _ in _lues(reseau)]
    assert heures == [0] + [intervalle * i for i in range(1, len(heures))]
    assert len(heures) == 7  # robots.txt, la sonde, la liste, trois Séances et une redirection


@pytest.mark.parametrize(
    ("robots", "reseau_lent", "intervalle"),
    [
        ("", "195.65.10.0/24", 20),
        ("User-agent: *\nCrawl-delay: 30\n", "195.65.10.0/24", 30),  # le plus grand des deux
        ("", "195.65.11.0/24", 5),  # un autre réseau
    ],
    ids=["ralenti", "crawl-delay-plus-grand", "autre-reseau"],
)
def test_un_reseau_ralenti_a_la_main_dans_sources_json_espace_ses_requetes(
    tmp_path, horloge, robots, reseau_lent, intervalle
):
    reseau = _preverenges(horloge)
    _robots(reseau, robots)
    sources = FichierSources.model_validate(
        {
            "plateformes": PLATEFORMES,
            "reseaux": [{"reseau": reseau_lent, "intervalle": 20}],
            "sources": [_opendata("5586"), SITE_PREVERENGES],
        }
    )

    _passer(tmp_path, horloge, reseau, sources=sources)

    heures = [secondes for _, secondes, _ in _lues(reseau)]
    assert heures == [intervalle * i for i in range(len(heures))]
    assert len(heures) == 7


# --- Blocage d'un /24 -----------------------------------------------------------------------------------------------

SITE_BLONAY_MEME_24 = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")
SOURCES_MEME_24 = _sources(_opendata("5586"), SITE_PREVERENGES, SITE_BLONAY_MEME_24)


def _meme_24(horloge):
    """Préverenges et Blonay - Saint-Légier, deux communes i-web sur le même /24 (la plage d'i-web)."""
    reseau = _preverenges(horloge)
    reseau.adresses["www.blonay-saint-legier.ch"] = "195.65.10.22"
    reseau.pages |= echantillon("i-web", "objets")
    return reseau


def _reseaux_bloques(depot):
    return _lire(depot, "etat-sources.json").get("reseaux", {})


@pytest.mark.parametrize(
    ("page", "motif", "blocage"),
    [
        (Page("", statut=429), "HTTP 429", "HTTP 429"),
        (Page("", statut=503), "HTTP 503", "HTTP 503"),
        (REFUS, "site injoignable", "connexion refusée"),
        (DELAI, "délai dépassé", "délai dépassé"),
    ],
    ids=["429", "503", "refus", "delai"],
)
def test_une_429_une_503_un_refus_ou_un_delai_bloque_le_24_et_les_communes_non_sondees_ont_l_acces_refuse(
    tmp_path, horloge, page, motif, blocage
):
    reseau = _meme_24(horloge)
    reseau.pages[LISTE] = page

    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24)

    assert [r.url for r in reseau.journal] == [ROBOTS, LISTE]  # rien vers Blonay, ni sonde ni import
    assert (_etat(tmp_path)["motif"], _etat(tmp_path, "site-5892")["motif"]) == (motif, "accès refusé")
    assert _importe(tmp_path) is None and _importe(tmp_path, "5892") is None
    assert _importe(tmp_path, "5586") is not None  # OpenParlData n'en souffre pas
    assert _reseaux_bloques(tmp_path) == {
        "195.65.10.0/24": {"depuis": "2026-10-23T05:17:05Z", "jusqu_a": None, "motif": blocage}
    }


@pytest.mark.parametrize("page", [Page("", statut=404), Page("", statut=403)], ids=["404", "403"])
def test_une_404_ou_une_403_reste_une_erreur_de_la_commune(tmp_path, horloge, page):
    reseau = _meme_24(horloge)
    reseau.pages[LISTE] = page

    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24)

    assert _etat(tmp_path)["echecs_consecutifs"] == 1
    assert _etat(tmp_path, "site-5892")["echecs_consecutifs"] == 0
    assert _importe(tmp_path, "5892") is not None
    assert _reseaux_bloques(tmp_path) == {}


def test_au_passage_suivant_une_seule_sonde_teste_le_reseau_avant_les_autres(tmp_path, horloge):
    reseau = _meme_24(horloge)
    reseau.pages[LISTE] = Page("", statut=429)
    issues = IssuesFactices()
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, issues=issues)

    # 30 minutes plus tard, le site refuse toujours : une seule sonde, et Blonay passe en panne, dans l'issue d'i-web.
    reseau.journal.clear()
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, heure=T0 + timedelta(minutes=30), issues=issues)

    assert [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal] == [
        (ROBOTS, "VigieVaud-sonde"),
        (LISTE, "VigieVaud-sonde"),
    ]
    etat = _etat(tmp_path, "site-5892")
    assert (etat["etat"], etat["motif"]) == ("en_panne", "accès refusé")
    plateforme = [s for s in issues.signalements if s[0].endswith("_plateforme")]
    assert plateforme[-1][:2] == ("panne_plateforme", "i-web")
    assert [s for s, _ in plateforme[-1][2]] == ["site-5643", "site-5892"]

    # Le site répond de nouveau : la sonde qui teste le réseau rouvre le réseau à toutes les communes.
    reseau.pages |= echantillon("i-web", "seances")
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, heure=T0 + timedelta(minutes=60), issues=issues)

    assert _importe(tmp_path) is not None and _importe(tmp_path, "5892") is not None
    assert _reseaux_bloques(tmp_path) == {}
    plateforme = [s for s in issues.signalements if s[0].endswith("_plateforme")]
    assert plateforme[-1] == ("retour_plateforme", "i-web", ["site-5643", "site-5892"])


def test_retry_after_prolonge_le_blocage_au_dela_du_passage_sans_aucune_requete(tmp_path, horloge):
    reseau = _meme_24(horloge)
    reseau.pages[LISTE] = Page("", statut=503, entetes={"Retry-After": "7200"})
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24)
    assert _reseaux_bloques(tmp_path)["195.65.10.0/24"]["jusqu_a"] == "2026-10-23T07:17:05Z"

    reseau.pages |= echantillon("i-web", "seances")  # le site répond, mais le robot attend 2 h
    for minutes in (30, 60, 90):
        reseau.journal.clear()
        _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, heure=T0 + timedelta(minutes=minutes))
        assert not any(r.url.startswith((PREVERENGES, BLONAY)) for r in reseau.journal)

    assert (_etat(tmp_path)["etat"], _etat(tmp_path)["motif"]) == ("en_panne", "accès refusé")
    reseau.journal.clear()
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, heure=T0 + timedelta(minutes=150))

    assert _lues(reseau)[:2] == [("/robots.txt", 150 * 60, "sonde"), ("/sitzung", 150 * 60 + 5, "sonde")]
    assert _etat(tmp_path)["etat"] == "disponible"
    assert _importe(tmp_path) is not None and _importe(tmp_path, "5892") is not None


def test_un_blocage_pendant_l_import_met_les_imports_du_reseau_en_echec_et_une_sonde_teste_le_reseau_au_suivant(
    tmp_path, horloge, capsys
):
    reseau = _meme_24(horloge)
    seance = f"{PREVERENGES}/_rte/anlass/6987193"
    page = reseau.pages[seance]
    reseau.pages[seance] = Page("", statut=429)

    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24)

    assert seance in [r.url for r in reseau.journal]
    assert not any(r.url.startswith(BLONAY) and "import" in r.user_agent for r in reseau.journal)
    assert _importe(tmp_path) is None and _importe(tmp_path, "5892") is None
    journal = capsys.readouterr().err
    assert "Import en échec : Conseil communal de Préverenges (site de la commune)" in journal
    assert "Import en échec : Conseil communal de Blonay - Saint-Légier (site de la commune)" in journal
    assert _etat(tmp_path)["echecs_consecutifs"] == 0  # les deux sondes avaient réussi

    # Au passage suivant, les deux imports sont refaits, mais une sonde teste d'abord le réseau.
    reseau.pages[seance] = page
    reseau.journal.clear()
    _passer(tmp_path, horloge, reseau, sources=SOURCES_MEME_24, heure=T0 + timedelta(minutes=30))

    roles = [(r.url, r.user_agent.split(" ")[0]) for r in reseau.journal if r.url.startswith((PREVERENGES, BLONAY))]
    assert roles[:3] == [(ROBOTS, "VigieVaud-sonde"), (LISTE, "VigieVaud-sonde"), (LISTE, "VigieVaud-import")]
    assert [u for u, role in roles if role == "VigieVaud-sonde"] == [ROBOTS, LISTE]
    assert _importe(tmp_path) is not None and _importe(tmp_path, "5892") is not None


# --- Plafond de 60 requêtes par commune -----------------------------------------------------------------------------


def _soixante_seances_de_plus(reseau):
    """60 Séances à venir de plus dans la liste de Préverenges, dont les pages ne répondent pas (404) : le passage
    ordinaire ouvre chacune d'elles, au-delà des 7 requêtes habituelles."""
    _liste_retouchee(
        reseau,
        lambda tableau, lignes: lignes + [_ligne(7400000 + i, "26.11.2026") for i in range(60)]
        if "Future" in tableau
        else lignes,
    )


def test_une_commune_qui_depasse_60_requetes_a_son_import_en_echec_note_dans_le_journal(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    _soixante_seances_de_plus(reseau)

    _passer(tmp_path, horloge, reseau)

    assert len(_lues(reseau)) == 60  # robots.txt et la sonde compris
    assert _importe(tmp_path) is None
    assert _importe(tmp_path, "5586") is not None
    journal = capsys.readouterr().err
    assert "Import en échec : Conseil communal de Préverenges (site de la commune)" in journal
    assert "plafond de 60 requêtes atteint" in journal
    assert _etat(tmp_path)["echecs_consecutifs"] == 0  # pas une panne
    assert not (tmp_path / "conseils/5643/seances").exists()


def test_le_rattrapage_n_a_pas_de_plafond(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _soixante_seances_de_plus(reseau)

    with httpx.Client(transport=reseau.transport(repli=_monde(horloge).transport())) as client:
        passage(
            tmp_path,
            _sources(_opendata("5586"), SITE_PREVERENGES),
            client,
            horloge=horloge,
            issues=IssuesFactices(),
            attendre=horloge.attendre,
            rattrapage=True,
            resoudre=reseau.resoudre,
        )

    assert len(_lues(reseau)) == 68  # les 7 habituelles, la Séance de février hors de la fenêtre, et les 60
    assert _importe(tmp_path) is not None


def test_une_requete_en_echec_n_est_pas_refaite_pendant_le_passage(tmp_path, horloge):
    # La même Séance listée deux fois (à venir et passée), dont la page ne répond pas.
    reseau = _preverenges(horloge)
    _liste_retouchee(
        reseau,
        lambda tableau, lignes: lignes + [_ligne(7400001, "26.11.2026" if "Future" in tableau else "01.10.2026")],
    )
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = Page("", statut=500)

    _passer(tmp_path, horloge, reseau)

    assert [r.url for r in reseau.journal].count(f"{PREVERENGES}/_rte/anlass/7400001") == 1
    assert _importe(tmp_path) is not None
