"""Tests de déclaration de `sources.json` (spec de J3, « Contrôles de CI ») : sur le fichier réel, sans réseau.

Chaque n° OFS déclaré existe dans `communes.json` ; un conseil n'a qu'une source ; chaque plateforme et variante
citées sont déclarées et permettent le niveau déclaré ; une commune non couverte a une raison et pas de conseil, une
commune couverte un conseil, une variante et une page `seances`. Chaque règle échoue sur un cas fabriqué.
"""

import json
from pathlib import Path

import pytest

from preparation_sources import verifier_declarations

RACINE = Path(__file__).resolve().parents[2]
SOURCES = RACINE / "sources.json"
COMMUNES = RACINE / "web" / "static" / "communes.json"


def test_le_sources_json_livre_respecte_toutes_les_regles_de_declaration():
    assert verifier_declarations(SOURCES, COMMUNES) == []


# Les 29 communes i-web du socle (recherche « Publications des conseils », #119), sans les 15 sites OIOI web que le
# recensement prenait pour i-web. Le Lieu (5873) disparaît au 1er janvier 2027 : elle n'est pas déclarée.
IWEB_COUVERTES = {
    5414, 5458, 5514, 5523, 5607, 5634, 5643, 5649, 5654, 5656, 5674, 5704, 5712, 5749, 5764, 5841, 5851, 5883, 5892,
}
IWEB_PREAVIS_SEULS = {5487, 5568, 5855}  # Lussery-Villars, Sainte-Croix, Dully
# Sans page des Séances mesurée le 23 octobre 2026 : Ormont-Dessous, Orny, Oulens-sous-Echallens, Saint-Cergue,
# Bofflens, Corcelles-le-Jorat.
IWEB_RIEN_EN_LIGNE = {5410, 5493, 5529, 5727, 5747, 5785}
OIOI_WEB = {5406, 5412, 5426, 5435, 5464, 5515, 5623, 5631, 5702, 5709, 5710, 5821, 5842, 5843, 5891}
LE_LIEU = 5873


def _sites(plateforme):
    fichier = json.loads(SOURCES.read_text(encoding="utf-8"))
    return [s for s in fichier["sources"] if s.get("site", {}).get("plateforme") == plateforme]


def test_chaque_commune_i_web_du_socle_est_declaree_couverte_ou_non_couverte_avec_sa_raison():
    sites = _sites("i-web")

    couvertes = {s["couverture"]["communes"][0] for s in sites if s["couverture"]["mode"] == "scrape"}
    non_couvertes = {
        s["couverture"]["communes"][0]: s["couverture"]["raison"]
        for s in sites
        if s["couverture"]["mode"] == "non_couvert"
    }
    assert couvertes == IWEB_COUVERTES
    assert non_couvertes == dict.fromkeys(IWEB_PREAVIS_SEULS, "preavis_seuls") | dict.fromkeys(
        IWEB_RIEN_EN_LIGNE, "rien_en_ligne"
    )
    assert len(sites) == 28


def test_ni_site_oioi_web_ni_le_lieu_ne_sont_declares():
    fichier = json.loads(SOURCES.read_text(encoding="utf-8"))

    declarees = {o for s in fichier["sources"] if s.get("couverture") for o in s["couverture"]["communes"]}
    assert not declarees & (OIOI_WEB | {LE_LIEU})


def test_une_commune_i_web_couverte_suit_la_forme_d_une_source_communale():
    for s in _sites("i-web"):
        ofs = s["couverture"]["communes"][0]
        assert s["id"] == f"site-{ofs}"
        assert (s["voie_acces"], s["fraicheur"]) == ("cron", "import")
        assert s["nom"].startswith(("Conseil communal d", "Conseil général d"))
        assert s["nom"].endswith(" (site de la commune)")
        assert s["nom_court"].startswith(("Site de ", "Site d'"))
        assert s["attribution"]["texte"].startswith(("Commune de ", "Commune d'"))
        assert s["attribution"]["licence"] == "Actes officiels (art. 5 LDA) : métadonnées et liens seulement"
        assert "sonde" not in s
        if "conseil" in s:
            assert s["conseil"]["body_key"] == str(ofs)


def test_la_section_plateformes_porte_i_web_et_ses_trois_variantes():
    fichier = json.loads(SOURCES.read_text(encoding="utf-8"))

    (iweb,) = [p for p in fichier["plateformes"] if p["id"] == "i-web"]
    assert {v["id"]: (v["marqueur"], v["niveaux"]) for v in iweb["variantes"]} == {
        "seances": ("icmsTablePastSitzungen", [["seances"]]),
        "objets": ("icmsTablePastSitzungen", [["objets", "seances"], ["seances"]]),
        "pages": ("icmsTablePastSitzungen", [["preavis", "seances"], ["seances"]]),
    }


# --- Chaque règle échoue sur un cas fabriqué ----------------------------------------------------------------------

PLATEFORMES = [
    {
        "id": "i-web",
        "nom": "i-web",
        "editeur": "Innovative Web AG",
        "variantes": [
            {"id": "seances", "marqueur": "icmsTablePastSitzungen", "niveaux": [["seances"]]},
            {"id": "pages", "marqueur": "icmsTablePastSitzungen", "niveaux": [["preavis", "seances"], ["seances"]]},
        ],
    }
]


def _couverte(ofs=5643, **modifs):
    return {
        "id": f"site-{ofs}",
        "nom": "Conseil communal de Préverenges (site de la commune)",
        "nom_court": "Site de Préverenges",
        "attribution": {
            "texte": "Commune de Préverenges",
            "lien": "https://www.preverenges.ch/conseil",
            "licence": "Actes officiels (art. 5 LDA) : métadonnées et liens seulement",
        },
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "scrape"},
        "conseil": {"body_key": str(ofs), "donne": ["seances"]},
        "site": {"plateforme": "i-web", "variante": "seances", "seances": "https://www.preverenges.ch/sitzung"},
    } | modifs


def _non_couverte(ofs=5568, **modifs):
    return {
        "id": f"site-{ofs}",
        "nom": "Conseil communal de Sainte-Croix (site de la commune)",
        "nom_court": "Site de Sainte-Croix",
        "attribution": {
            "texte": "Commune de Sainte-Croix",
            "lien": "https://www.sainte-croix.ch/conseil-communal",
            "licence": "Actes officiels (art. 5 LDA) : métadonnées et liens seulement",
        },
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "non_couvert", "raison": "preavis_seuls"},
        "site": {"plateforme": "i-web"},
    } | modifs


def _lausanne():
    return {
        "id": "openparldata-5586",
        "nom": "Conseil communal de Lausanne (OpenParlData)",
        "nom_court": "Conseil de Lausanne",
        "attribution": {"texte": "Source: OpenParlData.ch", "lien": "https://openparldata.ch", "licence": "CC BY 4.0"},
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [5586], "mode": "api"},
        "conseil": {"body_key": "5586", "donne": ["objets", "seances"]},
    }


def _verifier(tmp_path, sources, plateformes=PLATEFORMES):
    chemin = tmp_path / "sources.json"
    chemin.write_text(json.dumps({"plateformes": plateformes, "sources": sources}), encoding="utf-8")
    return verifier_declarations(chemin, COMMUNES)


def test_un_cas_fabrique_qui_suit_toutes_les_regles_passe(tmp_path):
    assert _verifier(tmp_path, [_lausanne(), _couverte(), _non_couverte()]) == []


@pytest.mark.parametrize(
    ("sources", "plateformes", "ecart"),
    [
        pytest.param(
            [_couverte(ofs=5999, conseil={"body_key": "5999", "donne": ["seances"]})],
            PLATEFORMES,
            "site-5999 : n° OFS 5999 absent de communes.json",
            id="n° OFS hors de communes.json",
        ),
        pytest.param(
            [_couverte(couverture={"communes": [5998], "mode": "scrape"})],
            PLATEFORMES,
            "site-5643 : n° OFS 5998 absent de communes.json",
            id="Couverture d'une commune hors de communes.json",
        ),
        pytest.param(
            [_lausanne(), _couverte(id="site-5586", conseil={"body_key": "5586", "donne": ["seances"]})],
            PLATEFORMES,
            "conseil 5586 déclaré par plusieurs sources : openparldata-5586, site-5586",
            id="un conseil, deux sources",
        ),
        pytest.param(
            [_couverte(site={"plateforme": "quicksite", "variante": "seances", "seances": "https://a.ch/s"})],
            PLATEFORMES,
            "site-5643 : plateforme quicksite non déclarée",
            id="plateforme non déclarée",
        ),
        pytest.param(
            [_non_couverte(site={"plateforme": "webcommunes"})],
            PLATEFORMES,
            "site-5568 : plateforme webcommunes non déclarée",
            id="plateforme d'une non couverte non déclarée",
        ),
        pytest.param(
            [_couverte(site={"plateforme": "i-web", "variante": "objets", "seances": "https://a.ch/s"})],
            PLATEFORMES,
            "site-5643 : variante objets non déclarée dans i-web",
            id="variante non déclarée",
        ),
        pytest.param(
            [_couverte(conseil={"body_key": "5643", "donne": ["preavis", "seances"]})],
            PLATEFORMES,
            "site-5643 : la variante i-web/seances ne permet pas le niveau séances et préavis",
            id="niveau que la variante ne permet pas",
        ),
        pytest.param(
            [_non_couverte(couverture={"communes": [5568], "mode": "non_couvert"})],
            PLATEFORMES,
            "sources.json invalide",
            id="non couverte sans raison",
        ),
        pytest.param(
            [_non_couverte(conseil={"body_key": "5568", "donne": ["seances"]})],
            PLATEFORMES,
            "sources.json invalide",
            id="non couverte avec conseil",
        ),
        pytest.param(
            [{k: v for k, v in _couverte().items() if k != "conseil"}],
            PLATEFORMES,
            "site-5643 : une commune couverte déclare son conseil",
            id="couverte sans conseil",
        ),
        pytest.param(
            [_couverte(site={"plateforme": "i-web", "seances": "https://www.preverenges.ch/sitzung"})],
            PLATEFORMES,
            "sources.json invalide",
            id="couverte sans variante",
        ),
        pytest.param(
            [_couverte(site={"plateforme": "i-web", "variante": "seances"})],
            PLATEFORMES,
            "sources.json invalide",
            id="couverte sans page des Séances",
        ),
    ],
)
def test_chaque_regle_echoue_sur_un_cas_fabrique(tmp_path, sources, plateformes, ecart):
    ecarts = _verifier(tmp_path, sources, plateformes)

    assert any(e.startswith(ecart) for e in ecarts), ecarts
