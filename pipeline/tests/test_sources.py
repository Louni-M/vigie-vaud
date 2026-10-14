"""Déclaration des sources (`sources.json`), lue par le cron à travers le schéma commun."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from schema import lire_sources

RACINE = Path(__file__).resolve().parents[2]


def test_sources_json_declare_les_huit_sources_de_j0():
    fichier = lire_sources(RACINE / "sources.json")

    assert [s.id for s in fichier.sources] == [
        "camac-permis",
        "swisstopo-fond",
        "swisstopo-recherche",
        "swisstopo-limites",
        "ucv-annuaire",
        "swisstopo-adresses",
        "swisstopo-lacs",
        "ofs-communes-historique",
    ]
    assert all(s.nom_court for s in fichier.sources)
    assert all(s.couverture.communes == "canton" for s in fichier.sources)


def test_seule_la_source_des_permis_est_sondee_et_jamais_vide():
    fichier = lire_sources(RACINE / "sources.json")

    sondees = {s.id: s.sonde for s in fichier.sources if s.sonde is not None}
    assert list(sondees) == ["camac-permis"]
    assert sondees["camac-permis"].jamais_vide


def _source(**modifs):
    source = {
        "id": "exemple",
        "nom": "Exemple",
        "nom_court": "Ex.",
        "attribution": {"texte": "© Exemple", "lien": "https://exemple.ch", "licence": "CC BY 4.0"},
        "voie_acces": "direct",
        "fraicheur": "donnee",
        "couverture": {"communes": [5586, 5938], "mode": "scrape"},
    }
    return source | modifs


def _ecrire(tmp_path, sources):
    chemin = tmp_path / "sources.json"
    chemin.write_text(json.dumps({"$schema": "./schema/sources.schema.json", "sources": sources}))
    return chemin


def test_une_source_couvrant_une_liste_de_communes_est_lue(tmp_path):
    fichier = lire_sources(_ecrire(tmp_path, [_source()]))

    assert fichier.sources[0].couverture.communes == [5586, 5938]
    assert fichier.sources[0].sonde is None


@pytest.mark.parametrize(
    "sources",
    [
        pytest.param([_source(id="Camac_Permis")], id="id hors kebab-case"),
        pytest.param([_source(), _source()], id="id en double"),
        pytest.param([_source(voie_acces="proxy")], id="voie d'accès inconnue"),
        pytest.param([_source(fraicheur="hier")], id="sorte de fraîcheur inconnue"),
        pytest.param([_source(couverture={"communes": "suisse", "mode": "api"})], id="couverture inconnue"),
        pytest.param([_source(couverture={"communes": [], "mode": "api"})], id="liste de communes vide"),
        pytest.param([_source(inconnu=1)], id="champ inconnu"),
        pytest.param([{k: v for k, v in _source().items() if k != "nom_court"}], id="sans nom_court"),
        pytest.param([_source(attribution={"texte": "x", "lien": "exemple.ch", "licence": "x"})], id="lien sans https"),
        pytest.param([_source(sonde={"url": "https://exemple.ch", "delai": 0})], id="délai de sonde nul"),
    ],
)
def test_une_declaration_invalide_est_refusee(tmp_path, sources):
    with pytest.raises(ValidationError):
        lire_sources(_ecrire(tmp_path, sources))
