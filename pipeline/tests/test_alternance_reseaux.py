"""L'alternance entre réseaux du robot communal (spec de J3, « Robot communal », « Débit » ; #178), par le passage du
cron : un fil par réseau /24 pour les sondes puis pour la lecture des sites, le robot n'envoyant jamais deux requêtes
à la fois ni deux requêtes à moins de 5 s vers un même /24. Le temps est celui de l'`Ordonnanceur` des tests : deux
réseaux qui attendent leurs 5 s en même temps ne font passer que 5 s.
"""

from datetime import timedelta
from urllib.parse import urlsplit

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page, echantillon
from passage_sites import BLONAY, PREVERENGES, SITE_PREVERENGES, T0, _lire, _passer, _preverenges, _site, _sources

AUTRE_RESEAU = "193.34.137.9"


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def _deux_reseaux(horloge, adresse_blonay=AUTRE_RESEAU):
    reseau = _preverenges(horloge)
    reseau.duree = 0.001  # chaque réponse prend un peu de temps réel : deux requêtes simultanées se verraient
    reseau.adresses["www.blonay-saint-legier.ch"] = adresse_blonay
    reseau.pages |= echantillon("i-web", "objets")
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")
    return reseau, _sources(SITE_PREVERENGES, blonay)


def _par_hote(reseau):
    hotes = {}
    for r in reseau.journal:
        hotes.setdefault(urlsplit(r.url).hostname, []).append(r.heure)
    return hotes


def test_deux_reseaux_sont_lus_en_meme_temps_sans_jamais_deux_requetes_a_la_fois(tmp_path, horloge):
    reseau, sources = _deux_reseaux(horloge)

    _passer(tmp_path, horloge, reseau, sources=sources)

    assert reseau.en_vol_max == 1
    hotes = _par_hote(reseau)
    preverenges, blonay = hotes["www.preverenges.ch"], hotes["www.blonay-saint-legier.ch"]
    # Chaque réseau garde ses 5 s entre deux requêtes…
    for heures in (preverenges, blonay):
        assert all(b - a >= timedelta(seconds=5) for a, b in zip(heures, heures[1:]))
    # … mais les deux réseaux commencent ensemble et se chevauchent : le passage dure ce que dure le plus long.
    assert preverenges[0] == blonay[0] == T0
    assert blonay[0] < preverenges[-1] and preverenges[0] < blonay[-1]
    assert max(preverenges[-1], blonay[-1]) - T0 < (preverenges[-1] - preverenges[0]) + (blonay[-1] - blonay[0])


def test_le_passage_ecrit_les_memes_fichiers_qu_un_reseau_apres_l_autre(tmp_path, horloge):
    # Les sites sont lus en même temps, mais les états et l'archive sont écrits dans l'ordre de `sources.json`.
    (tmp_path / "deux").mkdir(), (tmp_path / "un").mkdir()
    reseau, sources = _deux_reseaux(horloge)
    _passer(tmp_path / "deux", horloge, reseau, sources=sources)
    seul, sources_seul = _deux_reseaux(HorlogeFactice(T0), adresse_blonay="195.65.10.22")
    _passer(tmp_path / "un", seul.horloge, seul, sources=sources_seul)

    for chemin in ("conseils/5643/seances.json", "conseils/5892/seances.json", "conseils/index.json"):
        a, b = _lire(tmp_path / "deux", chemin), _lire(tmp_path / "un", chemin)
        a.pop("genere"), b.pop("genere")
        assert a == b, chemin
    assert list(_lire(tmp_path / "deux", "etat-sources.json")["sources"]) == ["site-5643", "site-5892"]


def test_un_reseau_bloque_n_arrete_pas_l_autre(tmp_path, horloge):
    reseau, sources = _deux_reseaux(horloge)
    reseau.pages[f"{BLONAY}/seances"] = Page(statut=503, entetes={"Retry-After": "3600"})

    _passer(tmp_path, horloge, reseau, sources=sources)

    assert _lire(tmp_path, "etat-sources.json")["reseaux"].keys() == {"193.34.137.0/24"}
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] is not None
    assert (tmp_path / "conseils/5643/seances/2026-09-10.json").exists()
    assert f"{PREVERENGES}/_rte/anlass/6987205" in [r.url for r in reseau.journal]
