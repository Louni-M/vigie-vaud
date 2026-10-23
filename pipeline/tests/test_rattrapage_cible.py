"""Le rattrapage ciblé des sites communaux (ADR 0010 ; spec de J3, « Cron et rattrapage »), observé par le passage
du cron : lancé à la main sur une plateforme ou un n° OFS, il rouvre toutes les pages des communes visées, hors de la
fenêtre de 6 mois et sans plafond, au même débit, et note l'heure du rattrapage dans `conseils/import.json`
(`rattrapages`). Il ne touche ni OpenParlData ni les autres communes. Le rattrapage d'OpenParlData, lui, ne relit
plus aucun site.
"""

from datetime import timedelta

import pytest

from faux_openparldata import HorlogeFactice
from schema import FichierSources
from passage_sites import (
    BLONAY,
    PLATEFORMES,
    PREVERENGES,
    SITE_PREVERENGES,
    T0,
    _lire,
    _monde,
    _opendata,
    _passer,
    _seance_fabriquee,
    _site,
)
from test_sondes_sites import _deux_communes

QUICKSITE = "https://www.exemple-quicksite.ch"
# Une seconde plateforme déclarée, pour vérifier qu'un rattrapage d'i-web ne la lit pas.
PLATEFORMES_ET_QUICKSITE = PLATEFORMES + [
    {
        "id": "quicksite",
        "nom": "Quicksite",
        "editeur": "Exemple SA",
        "variantes": [{"id": "seances", "marqueur": "qs-seances", "niveaux": [["seances"]]}],
    }
]
SITE_QUICKSITE = _site(5999, "Exemple", f"{QUICKSITE}/seances", f"{QUICKSITE}/conseil") | {
    "site": {"plateforme": "quicksite", "variante": "seances", "seances": f"{QUICKSITE}/seances"}
}
FEVRIER = f"{PREVERENGES}/_rte/anlass/7273262"  # la Séance du 5 février, hors de la fenêtre du 23 octobre


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def _reseau(horloge):
    """Préverenges et Blonay - Saint-Légier (i-web, deux réseaux), avec la page de la Séance de février de
    Préverenges, et un site Quicksite qui n'est jamais servi."""
    reseau, _ = _deux_communes(horloge)
    reseau.pages[FEVRIER] = _seance_fabriquee("7000001", "Procès-verbal de février")
    reseau.adresses["www.exemple-quicksite.ch"] = "203.0.113.5"
    return reseau


def _sources():
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")
    return FichierSources.model_validate(
        {
            "plateformes": PLATEFORMES_ET_QUICKSITE,
            "sources": [_opendata("5586"), SITE_PREVERENGES, blonay, SITE_QUICKSITE],
        }
    )


def _rattraper(depot, horloge, reseau, heure, **options):
    """Un passage sur les sources de ces tests, à `heure` ; rend le faux OpenParlData, qui note ses requêtes."""
    monde = _monde(horloge)
    _passer(depot, horloge, reseau, _sources(), monde=monde, heure=heure, **options)
    return monde


def _hotes(reseau, monde):
    """Les hôtes qui ont reçu une requête : sites du faux réseau, et `openparldata` pour le faux OpenParlData."""
    return {r.url.split("/")[2] for r in reseau.journal} | ({"openparldata"} if monde.requetes else set())


def test_le_rattrapage_d_une_commune_rouvre_tout_son_site_et_ne_touche_ni_openparldata_ni_les_autres(
    tmp_path, horloge
):
    reseau = _reseau(horloge)
    _rattraper(tmp_path, horloge, reseau, T0)  # passage ordinaire : la fenêtre de 6 mois seulement
    avant = _lire(tmp_path, "conseils/import.json")
    assert not (tmp_path / "conseils/5643/seances/2026-02-05.json").exists()

    reseau.journal.clear()
    monde = _rattraper(tmp_path, horloge, reseau, T0 + timedelta(hours=3), rattrapage_cible="5643")

    assert _hotes(reseau, monde) == {"www.preverenges.ch"}
    assert FEVRIER in [r.url for r in reseau.journal]
    seance = _lire(tmp_path, "conseils/5643/seances/2026-02-05.json")
    assert seance["documents"][0]["titre"] == "Procès-verbal de février"
    apres = _lire(tmp_path, "conseils/import.json")
    assert apres["rattrapages"] == {"5643": "2026-10-23T08:17:00Z"}
    assert apres["conseils"] == avant["conseils"] | {"5643": "2026-10-23T08:17:00Z"}


def test_le_rattrapage_d_une_plateforme_lit_toutes_ses_communes_et_seulement_elles(tmp_path, horloge):
    reseau = _reseau(horloge)

    monde = _rattraper(tmp_path, horloge, reseau, T0, rattrapage_cible="i-web")

    assert _hotes(reseau, monde) == {"www.preverenges.ch", "www.blonay-saint-legier.ch"}
    assert (tmp_path / "conseils/5643/seances/2026-02-05.json").exists()
    imports = _lire(tmp_path, "conseils/import.json")
    assert set(imports["rattrapages"]) == {"5643", "5892"}
    assert set(imports["conseils"]) == {"5643", "5892"}
    assert "site-5999" not in _lire(tmp_path, "etat-sources.json")["sources"]


def test_un_rattrapage_ne_signale_pas_en_echec_les_communes_qu_il_ne_tente_pas(tmp_path, horloge):
    reseau = _reseau(horloge)
    monde = _monde(horloge)

    issues = _passer(tmp_path, horloge, reseau, _sources(), monde=monde, heure=T0, rattrapage_cible="5643")

    # Blonay - Saint-Légier et Exemple n'ont jamais été importés, mais ce rattrapage ne les visait pas.
    assert issues.signalements == []


def test_le_rattrapage_d_openparldata_ne_touche_aucun_site(tmp_path, horloge):
    reseau = _reseau(horloge)

    monde = _rattraper(tmp_path, horloge, reseau, T0, rattrapage=True)

    assert reseau.journal == []
    assert monde.requetes
    imports = _lire(tmp_path, "conseils/import.json")
    assert imports["conseils"] == {"5586": "2026-10-23T05:17:00Z"}
    assert imports["rattrapages"] == {"5586": "2026-10-23T05:17:00Z"}


def test_une_cible_qui_n_est_ni_une_plateforme_ni_une_commune_scrapee_arrete_le_passage_sans_rien_ecrire(
    tmp_path, horloge
):
    reseau = _reseau(horloge)

    with pytest.raises(ValueError, match="« 9999 »"):
        _rattraper(tmp_path, horloge, reseau, T0, rattrapage_cible="9999")

    assert reseau.journal == []
    assert list(tmp_path.iterdir()) == []
