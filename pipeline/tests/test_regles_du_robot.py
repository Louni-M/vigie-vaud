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

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page
from schema import FichierSources
from test_sites_communaux import PLATEFORMES, PREVERENGES, SITE_PREVERENGES, T0, _opendata, _preverenges
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
