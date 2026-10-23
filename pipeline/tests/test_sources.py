"""Déclaration des sources (`sources.json`), lue par le cron à travers le schéma commun."""

import json
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest
from pydantic import ValidationError

from schema import Conseil, lire_sources, nom_du_conseil

RACINE = Path(__file__).resolve().parents[2]


def test_sources_json_declare_les_sources_de_j0_la_dgmr_et_les_trois_conseils():
    fichier = lire_sources(RACINE / "sources.json")

    assert [s.id for s in fichier.sources] == [
        "camac-permis",
        "dgmr-restrictions",
        "swisstopo-fond",
        "swisstopo-recherche",
        "swisstopo-limites",
        "ucv-annuaire",
        "swisstopo-adresses",
        "swisstopo-lacs",
        "ofs-communes-historique",
        "openparldata-vd",
        "openparldata-5586",
        "openparldata-5938",
    ]
    assert all(s.nom_court for s in fichier.sources)


def test_la_camac_et_la_dgmr_couvrent_le_canton_et_chaque_conseil_communal_sa_commune():
    fichier = lire_sources(RACINE / "sources.json")

    couvertures = {s.id: s.couverture for s in fichier.sources if s.couverture is not None}
    assert {id: (c.communes, c.mode) for id, c in couvertures.items()} == {
        "camac-permis": ("canton", "api"),
        "dgmr-restrictions": ("canton", "api"),
        "openparldata-5586": ([5586], "api"),
        "openparldata-5938": ([5938], "api"),
    }


def test_les_trois_conseils_passent_par_le_cron_avec_l_attribution_d_openparldata():
    fichier = lire_sources(RACINE / "sources.json")

    conseils = {s.id: s for s in fichier.sources if s.conseil is not None}
    assert {id: (s.nom, s.nom_court) for id, s in conseils.items()} == {
        "openparldata-vd": ("Grand Conseil (OpenParlData)", "Grand Conseil"),
        "openparldata-5586": ("Conseil communal de Lausanne (OpenParlData)", "Conseil de Lausanne"),
        "openparldata-5938": ("Conseil communal d'Yverdon-les-Bains (OpenParlData)", "Conseil d'Yverdon"),
    }
    for s in conseils.values():
        assert s.voie_acces == "cron"
        assert s.fraicheur == "import"
        assert s.attribution.model_dump() == {
            "texte": "Source: OpenParlData.ch",
            "lien": "https://openparldata.ch",
            "licence": "CC BY 4.0",
        }
    assert {id: s.conseil.model_dump(exclude_none=True) for id, s in conseils.items()} == {
        "openparldata-vd": {"body_key": "VD", "donne": ["objets", "seances"], "groupe": 1965},
        "openparldata-5586": {"body_key": "5586", "donne": ["objets", "seances"]},
        # Yverdon ne donne que ses Séances : sa note de niveau renvoie à la page du conseil sur le site de la ville.
        "openparldata-5938": {
            "body_key": "5938",
            "donne": ["seances"],
            "page": "https://www.yverdon-les-bains.ch/vie-politique/conseil-communal",
        },
    }


def test_chaque_conseil_a_une_sonde_legere_sur_openparldata_qui_lit_data():
    fichier = lire_sources(RACINE / "sources.json")

    sondes = {s.id: s.sonde for s in fichier.sources if s.conseil is not None}
    assert {id: (str(s.url), s.champs) for id, s in sondes.items()} == {
        "openparldata-vd": (
            "https://api.openparldata.ch/v1/affairs/?body_key=VD&limit=1&fields=id,number,title&client=vigie-vaud",
            ["id", "number", "title"],
        ),
        "openparldata-5586": (
            "https://api.openparldata.ch/v1/affairs/?body_key=5586&limit=1&fields=id,number,title&client=vigie-vaud",
            ["id", "number", "title"],
        ),
        "openparldata-5938": (
            "https://api.openparldata.ch/v1/meetings/?body_key=5938&limit=1&fields=id,begin_date&client=vigie-vaud",
            ["id", "begin_date"],
        ),
    }
    assert all(s.enregistrements == "data" and s.jamais_vide for s in sondes.values())


def test_la_dgmr_est_une_source_direct_du_canton_sans_rediffusion_avec_ses_limites():
    fichier = lire_sources(RACINE / "sources.json")

    (dgmr,) = [s for s in fichier.sources if s.id == "dgmr-restrictions"]
    assert (dgmr.nom, dgmr.nom_court) == ("Restrictions de circulation DGMR (MapServer/596 et 595)", "DGMR")
    assert dgmr.attribution.model_dump() == {
        "texte": "Géodonnées État de Vaud (DGMR)",
        "lien": "https://www.vd.ch/mobilite/loffre-de-mobilite-a-votre-disposition/transports-individuels-motorises-tim/"
        "restrictions-de-circulation-et-travaux",
        "licence": "Norme DCG 8401, sans rediffusion",
    }
    assert (dgmr.voie_acces, dgmr.fraicheur) == ("direct", "requete")
    assert dgmr.limites == "surtout les routes cantonales ; les routes communales n'y figurent pas toujours"


def test_la_sonde_de_la_dgmr_lit_une_restriction_en_cours_et_ses_11_champs():
    fichier = lire_sources(RACINE / "sources.json")

    (sonde,) = [s.sonde for s in fichier.sources if s.id == "dgmr-restrictions"]
    url = urlsplit(str(sonde.url))
    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        "https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/596/query"
    )
    champs = [
        "OBJECTID",
        "NOM",
        "RESTRICTION",
        "RHRC",
        "DATE_DEBUT",
        "DATE_FIN",
        "HEURE_DEBUT",
        "HEURE_FIN",
        "WEEK_END",
        "TYPE",
        "REMARQUE",
    ]
    assert dict(parse_qsl(url.query)) == {
        "where": "1=1",
        "outFields": ",".join(champs),
        "returnGeometry": "false",
        "resultRecordCount": "1",
        "f": "json",
    }
    assert sonde.champs == champs
    assert (sonde.delai, sonde.enregistrements, sonde.jamais_vide) == (20, "features", True)


def test_seule_la_dgmr_declare_des_limites():
    fichier = lire_sources(RACINE / "sources.json")

    assert [s.id for s in fichier.sources if s.limites is not None] == ["dgmr-restrictions"]


def test_les_sondes_de_j0_lisent_toujours_features():
    fichier = lire_sources(RACINE / "sources.json")

    assert fichier.sources[0].sonde.enregistrements == "features"


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


def test_une_source_sans_couverture_qui_donne_un_conseil_est_lue(tmp_path):
    sans_couverture = {k: v for k, v in _source().items() if k != "couverture"}
    conseil = sans_couverture | {"fraicheur": "import", "conseil": {"body_key": "VD", "donne": ["objets", "seances"]}}

    (source,) = lire_sources(_ecrire(tmp_path, [conseil])).sources

    assert source.couverture is None
    assert source.conseil.groupe is None


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
        pytest.param([_source(conseil={"body_key": "VD", "donne": []})], id="conseil qui ne donne rien"),
        pytest.param([_source(conseil={"body_key": "VD", "donne": ["votes"]})], id="conseil qui donne l'inconnu"),
        pytest.param([_source(conseil={"donne": ["objets"]})], id="conseil sans body_key"),
        pytest.param([_source(limites="")], id="limites vides"),
    ],
)
def test_une_declaration_invalide_est_refusee(tmp_path, sources):
    with pytest.raises(ValidationError):
        lire_sources(_ecrire(tmp_path, sources))


@pytest.mark.parametrize(
    ("body_key", "cle", "commune"),
    [("VD", "vd", None), ("5586", "5586", 5586), ("5938", "5938", 5938)],
)
def test_la_cle_et_la_commune_d_un_conseil_se_tirent_de_son_body_key(body_key, cle, commune):
    conseil = Conseil(body_key=body_key, donne=["objets"])

    assert (conseil.cle, conseil.commune) == (cle, commune)


# Les mêmes cas que `nomDuConseil` du site (`web/src/lib/sources.test.ts`) : le nom de l'index est celui que le site
# affiche ailleurs. Un cas ajouté d'un côté s'ajoute de l'autre.
@pytest.mark.parametrize(
    ("nom_source", "nom"),
    [
        ("Grand Conseil (OpenParlData)", "Grand Conseil"),
        ("Conseil communal de Lausanne (OpenParlData)", "Conseil communal de Lausanne"),
        ("Conseil communal d'Yverdon-les-Bains (OpenParlData)", "Conseil communal d’Yverdon-les-Bains"),
        ("Conseil général de Nyon (OpenParlData, essai)", "Conseil général de Nyon"),
        ("Conseil communal (CC) de Morges", "Conseil communal (CC) de Morges"),
        ("Conseil communal de Pully", "Conseil communal de Pully"),
    ],
)
def test_le_nom_d_un_conseil_est_celui_de_sa_source_sans_la_mention_finale_entre_parentheses(nom_source, nom):
    assert nom_du_conseil(nom_source) == nom
