"""Les sites communaux dans le passage du cron (spec de J3, « Import des sites ») : une commune i-web en séances
seules, déclarée dans un `sources.json` de test, lue par le robot communal sur l'échantillon enregistré
(`echantillon-sites/i-web/`), archivée et listée comme un conseil d'OpenParlData.

C'est le seul seam du cron : le passage reçoit un seul transport, qui sert à la fois le faux OpenParlData de J1 et
les pages de l'échantillon (`faux_sites.Reseau`), une résolution d'adresse factice pour le /24 du robot, et une
horloge que l'attente fait avancer. On observe les fichiers écrits, le journal du passage et les requêtes reçues par
les sites (URL, User-Agent, heure). Les cas instables sont fabriqués par de petites retouches de l'échantillon.
"""

from datetime import timedelta
from pathlib import Path

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau, echantillon
from passage_sites import (
    BLONAY,
    PREVERENGES,
    S,
    SITE_PREVERENGES,
    T0,
    _ligne,
    _lire,
    _liste_retouchee,
    _opendata,
    _passer,
    _preverenges,
    _seance_fabriquee,
    _site,
    _sources,
)


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_une_commune_i_web_en_seances_seules_est_archivee_avec_ses_documents_et_son_lien_stable(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge))

    seance = _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")
    del seance["genere"]
    assert seance == {
        "version": 1,
        "id": None,
        "date": "2026-09-10T20:00",
        "nom": "Séance du Conseil communal",
        "lien": f"{PREVERENGES}/_rte/anlass/6987205",
        "ordre_du_jour": [],
        "documents": [
            {"titre": "1. Ordre du jour", "date": None, "lien": f"{PREVERENGES}/_doc/7223149"},
            {
                "titre": "2. Préavis 6-26_Autorisations_generales 2026-2031",
                "date": None,
                "lien": f"{PREVERENGES}/_doc/7223152",
            },
            {"titre": "4. Décision CC 10.09.26", "date": None, "lien": f"{PREVERENGES}/_doc/7223158"},
            {
                "titre": "5. PV 25.6.26 installations des Autorités approuvé le 10.9.26",
                "date": None,
                "lien": f"{PREVERENGES}/_doc/7223161",
            },
        ],
    }


def test_les_seances_de_la_fenetre_sont_listees_dans_l_ordre_des_dates_malgre_le_desordre_du_site(tmp_path, horloge):
    # La liste passée du site donne le 18 juin, le 10 septembre, puis le 5 février : hors de la fenêtre (avant le
    # 23 avril), la Séance de février n'est ni ouverte ni importée.
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau)

    assert _lire(tmp_path, "conseils/5643/seances.json")["seances"] == [
        {
            "cle": "5643/2026-10-29",
            "date": "2026-10-29T20:00",
            "points": 0,
            "documents": [{"titre": "Ordre du jour", "date": None, "lien": f"{PREVERENGES}/_doc/7300001"}],
        },
        {
            "cle": "5643/2026-09-10",
            "date": "2026-09-10T20:00",
            "points": 0,
            "documents": _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")["documents"],
        },
        {
            "cle": "5643/2026-06-18",
            "date": "2026-06-18T19:00",
            "points": 0,
            "documents": [{"titre": "Procès-verbal", "date": None, "lien": f"{PREVERENGES}/_doc/7100001"}],
        },
    ]
    assert not any("7273262" in r.url for r in reseau.journal)
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert (conseil["source"], conseil["nom"], conseil["commune"], conseil["donne"]) == (
        "site-5643",
        "Conseil communal de Préverenges",
        5643,
        ["seances"],
    )
    assert (conseil["prochaine_seance"], conseil["derniere_seance"]) == ("5643/2026-10-29", "5643/2026-09-10")
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"


def test_le_meme_passage_importe_les_conseils_d_openparldata_comme_sans_site(tmp_path, horloge):
    seul, avec_site = tmp_path / "seul", tmp_path / "avec-site"
    seul.mkdir()
    avec_site.mkdir()

    # La sonde du site (robots.txt, puis la page de liste 5 s plus tard) précède l'import : sans site, le passage
    # part 5 s plus tard pour importer à la même heure.
    _passer(seul, horloge, _preverenges(horloge), sources=_sources(_opendata("5586")), heure=T0 + 5 * S)
    horloge.heure = T0
    _passer(avec_site, horloge, _preverenges(horloge))

    lausanne = sorted(p.relative_to(seul) for p in (seul / "conseils/5586").rglob("*.json"))
    assert lausanne == [
        Path("conseils/5586/objets/POS25-115.json"),
        Path("conseils/5586/objets-2026.json"),
        Path("conseils/5586/seances.json"),
    ]
    for chemin in lausanne:
        assert _lire(avec_site, chemin) == _lire(seul, chemin)
    # Le premier import d'un conseil scrapé est noté à part, pour l'issue `a-verifier` (#155) ; Lausanne n'en a pas.
    assert _lire(avec_site, "conseils/import.json") == _lire(seul, "conseils/import.json") | {
        "conseils": {"5586": "2026-10-23T05:17:05Z", "5643": "2026-10-23T05:17:05Z"},
        "premiers": {"5643": "2026-10-23T05:17:05Z"},
    }


def test_un_second_passage_ne_reecrit_rien(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge))
    avant = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}

    reseau = _preverenges(horloge)
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(days=1))

    assert any("/_rte/anlass/" in r.url for r in reseau.journal)  # les pages ont bien été relues
    apres = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}
    assert apres == avant
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-24T05:17:05Z"


def test_une_seance_disparue_du_site_reste_dans_l_archive_et_les_listes(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge))
    juin = _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")

    # Le lendemain, le site a retiré la Séance du 18 juin de sa liste.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [ligne for ligne in lignes if "6987193" not in ligne["name"]])
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(days=1))

    assert not any("6987193" in r.url for r in reseau.journal)
    assert _lire(tmp_path, "conseils/5643/seances/2026-06-18.json") == juin
    assert "5643/2026-06-18" in [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]]


def test_un_site_qui_ne_garde_que_les_seances_a_venir_est_archive_depuis_le_premier_import(tmp_path, horloge):
    # Comme Lovatens : la liste ne montre que la prochaine Séance, et l'efface une fois tenue.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: lignes if "Future" in tableau else [])
    _passer(tmp_path, horloge, reseau)
    assert [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]] == ["5643/2026-10-29"]

    # Une semaine plus tard, la Séance du 29 octobre est tenue : le site ne montre plus que celle du 26 novembre.
    reseau = _preverenges(horloge)
    _liste_retouchee(
        reseau, lambda tableau, lignes: [_ligne(7400001, "26.11.2026")] if "Future" in tableau else []
    )
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = _seance_fabriquee("7400002", "Ordre du jour")
    _passer(tmp_path, horloge, reseau, heure=T0 + timedelta(days=7))

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]] == [
        "5643/2026-11-26",
        "5643/2026-10-29",
    ]
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert (conseil["prochaine_seance"], conseil["derniere_seance"]) == ("5643/2026-11-26", "5643/2026-10-29")


def test_une_commune_non_couverte_n_est_ni_sondee_ni_importee(tmp_path, horloge):
    # Une commune i-web qui ne publie que des préavis : déclarée avec sa plateforme, sa page de liste et sa raison,
    # mais sans conseil ni sonde. Son site n'est jamais lu, même s'il répond.
    sainte_croix = "https://www.sainte-croix.ch"
    reseau = _preverenges(horloge)
    reseau.adresses["www.sainte-croix.ch"] = "193.34.137.9"
    reseau.pages[f"{sainte_croix}/seances"] = reseau.pages[f"{PREVERENGES}/sitzung"]
    non_couverte = {
        k: v for k, v in _site(5568, "Sainte-Croix", f"{sainte_croix}/seances", f"{sainte_croix}/conseil").items()
        if k != "conseil"
    } | {"couverture": {"communes": [5568], "mode": "non_couvert", "raison": "preavis_seuls"}}

    sources = _sources(_opendata("5586"), SITE_PREVERENGES, non_couverte)

    _passer(tmp_path, horloge, reseau, sources=sources)

    assert not any(r.url.startswith(sainte_croix) for r in reseau.journal)
    assert any(r.url.startswith(PREVERENGES) for r in reseau.journal)
    assert "site-5568" not in _lire(tmp_path, "etat-sources.json")["sources"]
    assert [c["cle"] for c in _lire(tmp_path, "conseils/index.json")["conseils"]] == ["5586", "5643"]
    assert set(_lire(tmp_path, "conseils/import.json")["conseils"]) == {"5586", "5643"}
    assert not (tmp_path / "conseils/5568").exists()


def test_une_commune_passee_non_couverte_garde_en_ligne_ce_qui_a_ete_importe_sans_import_ni_sonde(tmp_path, horloge):
    # Préverenges est importée, puis demande que son site ne soit plus lu : une PR la déclare non couverte.
    _passer(tmp_path, horloge, _preverenges(horloge))
    lecture = ["conseils/5643/seances.json", "conseils/5643/seances/2026-09-10.json"]
    avant = {chemin: _lire(tmp_path, chemin) for chemin in lecture}
    non_couverte = {k: v for k, v in SITE_PREVERENGES.items() if k not in ("conseil", "site")} | {
        "couverture": {"communes": [5643], "mode": "non_couvert", "raison": "demande_commune"},
        "site": {"plateforme": "i-web"},
    }
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau, sources=_sources(_opendata("5586"), non_couverte),
            heure=T0 + timedelta(days=1))

    assert not any(r.url.startswith(PREVERENGES) for r in reseau.journal)
    assert "site-5643" not in _lire(tmp_path, "etat-sources.json")["sources"]
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"  # pas réimportée
    for chemin in lecture:
        assert _lire(tmp_path, chemin) | {"genere": None} == avant[chemin] | {"genere": None}
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert (conseil["source"], conseil["commune"], conseil["donne"], conseil["seances"]) == (
        "site-5643",
        5643,
        ["seances"],
        3,
    )
    assert any(e["conseil"] == "5643" for e in _lire(tmp_path, "conseils/fil.json")["entrees"])


# --- Cas instables, fabriqués par retouche de l'échantillon ---------------------------------------------------------


def test_une_date_fictive_est_importee_telle_quelle(tmp_path, horloge):
    # « Séance du 1er janvier » : une date que le site n'a pas corrigée, annoncée à venir.
    reseau = _preverenges(horloge)
    _liste_retouchee(
        reseau, lambda tableau, lignes: lignes + [_ligne(7400001, "01.01.2030", "00h00")] if "Future" in tableau else lignes
    )
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = _seance_fabriquee("7400002", "Ordre du jour")

    _passer(tmp_path, horloge, reseau)

    assert _lire(tmp_path, "conseils/5643/seances/2030-01-01.json")["date"] == "2030-01-01"
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert conseil["prochaine_seance"] == "5643/2026-10-29"


def test_un_element_illisible_est_saute_et_note_dans_le_journal(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    # Une ligne sans date, et la page du 18 juin qui ne répond plus.
    _liste_retouchee(
        reseau, lambda tableau, lignes: lignes + [_ligne(7400001, "", "")] if "Past" in tableau else lignes
    )
    del reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"]

    _passer(tmp_path, horloge, reseau)

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]] == [
        "5643/2026-10-29",
        "5643/2026-09-10",
    ]
    journal = capsys.readouterr().err
    assert "Conseil communal de Préverenges (site de la commune) : élément sauté" in journal
    assert "/_rte/anlass/7400001" in journal
    assert f"{PREVERENGES}/_rte/anlass/6987193 non lue" in journal
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"


def test_une_liste_dont_aucune_ligne_ne_se_lit_met_l_import_de_la_commune_en_echec(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [{"name": "Séance", "_datum": ligne["_datum"]} for ligne in lignes])

    _passer(tmp_path, horloge, reseau)

    assert "Import en échec : Conseil communal de Préverenges (site de la commune)" in capsys.readouterr().err
    assert _lire(tmp_path, "conseils/import.json")["conseils"] == {"5586": "2026-10-23T05:17:05Z"}
    assert not (tmp_path / "conseils/5643/seances").exists()


def test_une_liste_vide_est_un_import_reussi_sans_seance(tmp_path, horloge):
    # Un conseil général entre deux séances : le site ne liste rien, ce n'est pas un échec.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [])

    _passer(tmp_path, horloge, reseau)

    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"
    assert _lire(tmp_path, "conseils/5643/seances.json")["seances"] == []


def test_deux_seances_d_un_meme_jour_n_en_font_qu_une_avec_tous_leurs_points_et_documents(tmp_path, horloge):
    # Une Séance extraordinaire à 18 h, listée après celle de 20 h du même 10 septembre : l'heure fait la première.
    reseau = _preverenges(horloge)
    extraordinaire = _ligne(7400001, "10.09.2026", "18h00 - 19h00", "Séance extraordinaire")
    _liste_retouchee(reseau, lambda tableau, lignes: lignes + [extraordinaire] if "Past" in tableau else lignes)
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = _seance_fabriquee(
        "7400002", "Ordre du jour extraordinaire", points=[("1", "Assermentation"), ("2", "Préavis 7-26")]
    )

    _passer(tmp_path, horloge, reseau)

    seance = _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")
    assert (seance["id"], seance["date"], seance["nom"], seance["lien"]) == (
        None,
        "2026-09-10T18:00",
        "Séance extraordinaire",
        f"{PREVERENGES}/_rte/anlass/7400001",
    )
    assert [p["titre"] for p in seance["ordre_du_jour"]] == ["Assermentation", "Préavis 7-26"]
    assert [d["lien"].rsplit("/", 1)[1] for d in seance["documents"]] == [
        "7400002",
        "7223149",
        "7223152",
        "7223158",
        "7223161",
    ]
    lignes = _lire(tmp_path, "conseils/5643/seances.json")["seances"]
    assert {"cle": "5643/2026-09-10", "date": "2026-09-10T18:00", "points": 2} in lignes


def test_les_titres_des_documents_d_une_seance_sont_masques(tmp_path, horloge):
    reseau = _preverenges(horloge)
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"] = _seance_fabriquee(
        "7100001", "Préavis 4-26 - Succession de M. Paul Exemple, vente de la parcelle 12"
    )

    _passer(tmp_path, horloge, reseau)

    assert _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")["documents"] == [
        {
            "titre": "Préavis 4-26 - Succession de [particulier], vente de la parcelle 12",
            "date": None,
            "lien": f"{PREVERENGES}/_doc/7100001",
        }
    ]


# --- Le robot communal, vu depuis le site ---------------------------------------------------------------------------


def test_le_robot_lit_le_site_une_page_toutes_les_5_s_sous_le_nom_vigievaud_import(tmp_path, horloge):
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau)

    s = timedelta(seconds=1)
    assert [(r.url.removeprefix(PREVERENGES), r.heure - T0, r.user_agent.split(" ")[0]) for r in reseau.journal] == [
        ("/robots.txt", 0 * s, "VigieVaud-sonde"),  # lu une fois, avant la sonde (test_regles_du_robot.py)
        ("/sitzung", 5 * s, "VigieVaud-sonde"),  # la sonde, juste avant l'import (test_sondes_sites.py)
        ("/sitzung", 10 * s, "VigieVaud-import"),
        ("/_rte/anlass/6987214", 15 * s, "VigieVaud-import"),  # à venir, puis les passées dans l'ordre du site
        ("/_rte/anlass/6987193", 20 * s, "VigieVaud-import"),
        ("/_rte/anlass/6987205", 25 * s, "VigieVaud-import"),
        ("/sitzung/6987205", 30 * s, "VigieVaud-import"),  # la redirection du lien stable, au même débit
    ]
    assert reseau.journal[-1].user_agent == (
        "VigieVaud-import (+https://louni-m.github.io/vigie-vaud/a-propos#robot; vigievaud.gentile263@passinbox.com)"
    )


@pytest.mark.parametrize(
    ("adresse", "attente"),
    [("195.65.10.22", 5), ("193.34.137.9", 0)],
    ids=["meme-24", "autre-reseau"],
)
def test_deux_communes_d_un_meme_24_s_attendent_et_celles_d_un_autre_reseau_non(tmp_path, horloge, adresse, attente):
    reseau = _preverenges(horloge)
    reseau.duree = 0.001  # chaque réponse prend un peu de temps réel : deux requêtes simultanées se verraient
    reseau.adresses["www.blonay-saint-legier.ch"] = adresse
    reseau.pages |= echantillon("i-web", "objets")
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_PREVERENGES, blonay))

    heures = {r.url: r.heure for r in reseau.journal}
    assert heures[f"{BLONAY}/seances"] - heures[f"{PREVERENGES}/sitzung/6987205"] == timedelta(seconds=attente)
    assert reseau.en_vol_max == 1  # jamais deux requêtes à la fois, même vers deux réseaux


def test_une_page_en_iso_8859_1_est_lue_selon_son_content_type(tmp_path, horloge):
    # Les pages de l'échantillon sont servies compressées, avec `content-encoding: gzip` en minuscules ; celle-ci
    # l'est aussi, mais encodée en ISO-8859-1.
    reseau = _preverenges(horloge)
    url = f"{PREVERENGES}/sitzung/6987205"
    texte = reseau.pages[url].corps.decode("utf-8")
    reseau.pages[url] = Page(
        texte.encode("iso-8859-1"), entetes={"Content-Type": "text/html; charset=ISO-8859-1"}, gzip=True
    )

    _passer(tmp_path, horloge, reseau)

    titres = [d["titre"] for d in _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")["documents"]]
    assert titres[1:] == [
        "2. Préavis 6-26_Autorisations_generales 2026-2031",
        "4. Décision CC 10.09.26",
        "5. PV 25.6.26 installations des Autorités approuvé le 10.9.26",
    ]


def test_les_points_d_une_seance_publies_en_html_sont_archives(tmp_path, horloge):
    # Blonay - Saint-Légier publie l'ordre du jour de ses Séances en HTML ; lue en séances seules, sans ses Objets.
    reseau = Reseau(horloge, adresses={"www.blonay-saint-legier.ch": "195.65.10.22"})
    reseau.pages |= echantillon("i-web", "objets")
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")

    _passer(tmp_path, horloge, reseau, sources=_sources(blonay))

    seance = _lire(tmp_path, "conseils/5892/seances/2026-09-29.json")
    assert seance["ordre_du_jour"] == [
        {
            "numero": "01",
            "titre": "Adoption de l'ordre du jour définitif",
            "categorie": None,
            "resultat": None,
            "objet": None,
        },
        {"numero": "05", "titre": "Communications de la Municipalité", "categorie": None, "resultat": None, "objet": None},
        {
            "numero": "06",
            "titre": "Préavis 23-2026 concernant un crédit d'étude pour le renouvellement des infrastructures routières "
            "et souterraines communales ainsi que la réfection du Pont de Brent, pour un montant de CF 1'387'000.-",
            "categorie": None,
            "resultat": None,
            "objet": None,
        },
    ]
    assert [d["titre"] for d in seance["documents"]] == ["Ordre du jour", "Procès-verbal de la séance du 8 septembre 2026"]
    assert _lire(tmp_path, "conseils/5892/seances.json")["seances"][0] == {
        "cle": "5892/2026-09-29",
        "date": "2026-09-29T20:00",
        "points": 3,
    }
