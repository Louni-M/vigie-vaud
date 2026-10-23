"""Le script d'échantillon des sites communaux (`echantillon_sites.py`, ADR 0010), par son opération `enregistrer` :
il lit les pages d'une variante par le robot communal, sur un faux réseau, et écrit l'échantillon réduit.
"""

import json
from datetime import UTC, datetime

import httpx
import pytest

from echantillon_sites import Echantillon, PageEchantillon, enregistrer
from faux_openparldata import HorlogeFactice
from faux_sites import REFUS, Page, Reseau
from robot_communal import Injoignable, Robot

T0 = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)

LISTE = """<!DOCTYPE html>
<html lang="fr"><head><title>Séances</title><script>var x = 1;</script><style>p{}</style></head>
<body>
<nav class="menu"><ul><li><a href="/accueil">Accueil</a></li></ul></nav>
<div id="content" class="icms-content" style="margin:0">
  <p>Le Conseil communal se réunit en principe cinq fois par an.</p>
  <div class="icms-table-wrapper">
    <table id="icmsTablePastSitzungen" class="icms-dt" data-entities="{&quot;data&quot;:[{&quot;_id&quot;:11,&quot;name&quot;:&quot;S&#233;ance du 10.09.2026&quot;},{&quot;_id&quot;:12,&quot;name&quot;:&quot;S&#233;ance du 30.04.2026&quot;},{&quot;_id&quot;:13,&quot;name&quot;:&quot;S&#233;ance du 5.02.2026&quot;}]}"></table>
    <script>initTable()</script>
  </div>
</div>
<footer>Commune d'Exemple, rue du Village 1</footer>
</body></html>
"""

SEANCE = """<html><body><div id="content">
<h1 class="icms-title">Séance du Conseil communal</h1>
<div class="icms-description"><p>Texte rédigé par la commune.</p></div>
<ul class="icms-docs">
  <li class="doc"><a href="/_doc/101">Ordre du jour</a></li>
  <li class="doc"><a href="/_doc/102">Procès-verbal</a></li>
  <li class="doc"><a href="/_doc/103">Lettre de M. Exemple</a></li>
</ul>
</div></body></html>
"""

ECHANTILLON = Echantillon(
    plateforme="i-web",
    variante="seances",
    commune="Exemple",
    ofs=9999,
    pages=(
        PageEchantillon("seances", "https://www.exemple.ch/seances", ("table#icmsTablePastSitzungen",), ("11", "13")),
        PageEchantillon(
            "seance", "https://www.exemple.ch/seances/11", ("h1", "ul.icms-docs"), ("101", "102"), lignes="li"
        ),
    ),
)


def _reseau(horloge):
    reseau = Reseau(horloge, adresses={"www.exemple.ch": "195.65.10.20"})
    reseau.pages["https://www.exemple.ch/seances"] = Page(LISTE)
    reseau.pages["https://www.exemple.ch/seances/11"] = Page(
        SEANCE, entetes={"Content-Type": "text/html; charset=utf-8", "Set-Cookie": "session=1"}
    )
    return reseau


def _enregistrer(reseau, horloge, dossier, brut, echantillon=ECHANTILLON):
    robot = Robot(httpx.Client(transport=reseau.transport()), horloge, horloge.attendre, reseau.resoudre)
    return enregistrer(robot, echantillon, dossier, brut, horloge)


def test_une_liste_est_reduite_au_bloc_lu_avec_son_chemin_de_balises_et_les_lignes_choisies(tmp_path):
    horloge = HorlogeFactice(T0)

    _enregistrer(_reseau(horloge), horloge, tmp_path / "echantillon", tmp_path / "brut")

    page = (tmp_path / "echantillon/i-web/seances/seances.html").read_text(encoding="utf-8")
    assert page == (
        "<!--\n"
        "  Échantillon i-web, variante seances : Exemple (OFS 9999), page seances.\n"
        "  URL : https://www.exemple.ch/seances\n"
        "  Enregistrée le 2026-10-23 par pipeline/echantillon_sites.py.\n"
        "  Réduction : blocs table#icmsTablePastSitzungen et leur chemin de balises ; lignes gardées : 11, 13 ;\n"
        "  sans scripts, styles, menus ni textes rédigés.\n"
        "-->\n"
        "<html>\n"
        "<body>\n"
        '<div id="content" class="icms-content">\n'
        '<div class="icms-table-wrapper">\n'
        '<table id="icmsTablePastSitzungen" class="icms-dt" data-entities="{&quot;data&quot;:[{&quot;_id&quot;:11,'
        "&quot;name&quot;:&quot;Séance du 10.09.2026&quot;},{&quot;_id&quot;:13,&quot;name&quot;:&quot;Séance du "
        '5.02.2026&quot;}]}"></table>\n'
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def test_une_page_de_seance_ne_garde_que_ses_blocs_et_les_documents_choisis(tmp_path):
    horloge = HorlogeFactice(T0)

    _enregistrer(_reseau(horloge), horloge, tmp_path / "echantillon", tmp_path / "brut")

    page = (tmp_path / "echantillon/i-web/seances/seance.html").read_text(encoding="utf-8")
    assert page.split("-->\n", 1)[1] == (
        "<html>\n"
        "<body>\n"
        '<div id="content">\n'
        '<h1 class="icms-title">Séance du Conseil communal</h1>\n'
        '<ul class="icms-docs">\n'
        '<li class="doc"><a href="/_doc/101">Ordre du jour</a></li>\n'
        '<li class="doc"><a href="/_doc/102">Procès-verbal</a></li>\n'
        "</ul>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )
    assert "Exemple" not in page.split("-->\n", 1)[1]


def test_l_index_de_la_variante_garde_les_urls_le_statut_et_les_en_tetes_utiles(tmp_path):
    horloge = HorlogeFactice(T0)

    _enregistrer(_reseau(horloge), horloge, tmp_path / "echantillon", tmp_path / "brut")

    index = json.loads((tmp_path / "echantillon/i-web/seances/index.json").read_text(encoding="utf-8"))
    assert index == {
        "plateforme": "i-web",
        "variante": "seances",
        "commune": "Exemple",
        "ofs": 9999,
        "pages": [
            {"sorte": "seances", "url": "https://www.exemple.ch/seances", "finale": "https://www.exemple.ch/seances",
             "statut": 200, "entetes": {"content-type": "text/html; charset=utf-8"}, "fichier": "seances.html"},
            {"sorte": "seance", "url": "https://www.exemple.ch/seances/11",
             "finale": "https://www.exemple.ch/seances/11", "statut": 200,
             "entetes": {"content-type": "text/html; charset=utf-8"}, "fichier": "seance.html"},
        ],
    }


def test_relance_sur_les_memes_pages_le_script_produit_les_memes_fichiers(tmp_path):
    horloge = HorlogeFactice(T0)
    _enregistrer(_reseau(horloge), horloge, tmp_path / "premier", tmp_path / "brut-1")
    horloge.attendre(3600)
    _enregistrer(_reseau(horloge), horloge, tmp_path / "second", tmp_path / "brut-2")

    premiers = {p.relative_to(tmp_path / "premier"): p.read_bytes() for p in (tmp_path / "premier").rglob("*.*")}
    seconds = {p.relative_to(tmp_path / "second"): p.read_bytes() for p in (tmp_path / "second").rglob("*.*")}
    assert premiers == seconds
    assert len(premiers) == 3


def test_hors_ligne_la_reduction_est_refaite_depuis_les_pages_brutes_sans_aucune_requete(tmp_path):
    horloge = HorlogeFactice(T0)
    _enregistrer(_reseau(horloge), horloge, tmp_path / "premier", tmp_path / "brut")

    reseau = _reseau(horloge)
    ecrits = _enregistrer(reseau, horloge, tmp_path / "second", tmp_path / "brut")
    enregistrer(None, ECHANTILLON, tmp_path / "troisieme", tmp_path / "brut")

    assert reseau.journal == []
    for chemin in ecrits:
        relatif = chemin.relative_to(tmp_path / "second")
        assert chemin.read_bytes() == (tmp_path / "premier" / relatif).read_bytes()
        assert chemin.read_bytes() == (tmp_path / "troisieme" / relatif).read_bytes()


def test_les_pages_sont_lues_par_le_robot_pour_l_import_cinq_secondes_d_ecart(tmp_path):
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)

    _enregistrer(reseau, horloge, tmp_path / "echantillon", tmp_path / "brut")

    assert [(r.url, (r.heure - T0).total_seconds()) for r in reseau.journal] == [
        ("https://www.exemple.ch/seances", 0),
        ("https://www.exemple.ch/seances/11", 5),
    ]
    assert all(r.user_agent.startswith("VigieVaud-import ") for r in reseau.journal)


def test_une_page_non_lue_arrete_le_script_sans_nouvel_essai_ni_fichier_ecrit(tmp_path):
    horloge = HorlogeFactice(T0)
    reseau = _reseau(horloge)
    reseau.pages["https://www.exemple.ch/seances"] = REFUS

    with pytest.raises(Injoignable):
        _enregistrer(reseau, horloge, tmp_path / "echantillon", tmp_path / "brut")

    assert [r.url for r in reseau.journal] == ["https://www.exemple.ch/seances"]
    assert not (tmp_path / "echantillon").exists()


@pytest.mark.parametrize(
    ("blocs", "ids", "message"),
    [
        (("table#icmsTableFutureSitzungen",), (), "aucun bloc"),
        (("table#icmsTablePastSitzungen",), ("14",), "identifiants absents des blocs : 14"),
    ],
)
def test_un_bloc_ou_un_identifiant_absent_arrete_le_script_sans_rien_ecrire(tmp_path, blocs, ids, message):
    horloge = HorlogeFactice(T0)
    page = PageEchantillon("seances", "https://www.exemple.ch/seances", blocs, ids)
    echantillon = Echantillon("i-web", "seances", "Exemple", 9999, (page,))

    with pytest.raises(ValueError, match=message):
        _enregistrer(_reseau(horloge), horloge, tmp_path / "echantillon", tmp_path / "brut", echantillon)

    assert not (tmp_path / "echantillon").exists()


def test_une_page_en_iso_8859_1_est_ecrite_dans_son_encodage(tmp_path):
    horloge = HorlogeFactice(T0)
    reseau = Reseau(horloge, adresses={"conseil.exemple.ch": "185.54.6.10"})
    reseau.pages["https://conseil.exemple.ch/seances.asp"] = Page(
        "<html><body><table class='seances'><tr><td>Séance du 6 octobre</td></tr></table></body></html>".encode(
            "iso-8859-1"
        ),
        entetes={"Content-Type": "text/html; charset=ISO-8859-1"},
    )
    page = PageEchantillon("seances", "https://conseil.exemple.ch/seances.asp", ("table.seances",))
    echantillon = Echantillon("quicksite", "conseil", "Exemple", 9999, (page,))

    _enregistrer(reseau, horloge, tmp_path / "echantillon", tmp_path / "brut", echantillon)

    octets = (tmp_path / "echantillon/quicksite/conseil/seances.html").read_bytes()
    assert "<td>Séance du 6 octobre</td>".encode("iso-8859-1") in octets
    assert "Échantillon quicksite".encode("iso-8859-1") in octets
