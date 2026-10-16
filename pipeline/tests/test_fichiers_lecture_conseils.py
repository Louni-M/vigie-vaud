"""Les fichiers de lecture des conseils (ticket #65), reconstruits depuis l'archive à chaque passage complet de
l'import, contre un dossier temporaire qui tient lieu de clone du dépôt de données (spec de J1, « Dépôt de
données », fichiers de lecture ; ADR 0017).

Le monde de base est celui de `test_import_conseils` ; l'horloge est fixée au vendredi 16 octobre 2026, 7 h 05 UTC.
"""

from faux_openparldata import Affaire, Contributeur, Etape, HorlogeFactice, Point, Reunion
from test_import_conseils import T0, _lire, _monde, _passer


def test_les_seances_de_chaque_conseil_sont_listees_en_lignes_legeres_de_la_plus_recente_a_la_plus_ancienne(
    tmp_path,
):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.reunions += [
        Reunion(id=1033900, body_key="VD", group_id=1965, name="Séance", begin_date="2026-10-20T09:30:00"),
        Reunion(
            id=1030000,
            body_key="VD",
            group_id=1965,
            name="Séance",
            begin_date="2026-09-08T00:00:00",
            points=[Point(1, "Communications"), Point(2, "Divers")],
        ),
    ]

    _passer(tmp_path, monde, horloge)

    assert _lire(tmp_path, "conseils/vd/seances.json") == {
        "version": 1,
        "genere": "2026-10-16T07:05:00Z",
        "conseil": "vd",
        "seances": [
            {"cle": "vd/2026-10-20", "date": "2026-10-20T09:30", "points": 0},
            {"cle": "vd/2026-10-06", "date": "2026-10-06", "points": 2},
            {"cle": "vd/2026-09-08", "date": "2026-09-08", "points": 2},
        ],
    }
    assert _lire(tmp_path, "conseils/5938/seances.json")["seances"] == [
        {"cle": "5938/2026-10-01", "date": "2026-10-01T20:00", "points": 1}
    ]


def test_les_objets_sont_listes_par_annee_de_depot_du_plus_recent_au_plus_ancien_en_lignes_legeres(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(
            id=341500,
            body_key="VD",
            number="26_MOT_7",
            title="Pour des trains le dimanche",
            type_name="Motion",
            begin_date="2026-03-03",
            contributeurs=[
                Contributeur("Anne Exemple", "VER"),
                Contributeur("Paul Témoin", "PS"),
                Contributeur("Léa Tiers"),
            ],
            etapes=[Etape("2026-03-03"), Etape("2026-05-12", harmonise_fr="Renvoyé")],
        ),
        Affaire(id=341501, body_key="VD", number="26_QUE_9", title="Sans aucune date", begin_date=None),
    ]

    _passer(tmp_path, monde, horloge)

    vd_2026 = _lire(tmp_path, "conseils/vd/objets-2026.json")
    assert (vd_2026["version"], vd_2026["conseil"], vd_2026["annee"]) == (1, "vd", 2026)
    assert vd_2026["objets"] == [
        {
            "cle": "vd/26_INT_140",
            "numero": "26_INT_140",
            "type": "Interpellation",
            "depose": "2026-10-06",
            "titre": "Covid 2020 six ans pour revenir en arrière",
            "auteurs": [{"nom": "Pierre-François Mottier", "parti": "PLR"}, {"nom": "DSAS", "parti": None}],
            "nombre_auteurs": 2,
            "statut": {"libelle": "A l'ordre du jour", "date": "2026-10-07"},
            "derniere_etape": "2026-10-07",
            "communes": [],
        },
        {
            "cle": "vd/26_MOT_7",
            "numero": "26_MOT_7",
            "type": "Motion",
            "depose": "2026-03-03",
            "titre": "Pour des trains le dimanche",
            "auteurs": [{"nom": "Anne Exemple", "parti": "VER"}, {"nom": "Paul Témoin", "parti": "PS"}],
            "nombre_auteurs": 3,
            "statut": {"libelle": "Renvoyé", "date": "2026-05-12"},
            "derniere_etape": "2026-05-12",
            "communes": [],
        },
    ]
    assert [o["cle"] for o in _lire(tmp_path, "conseils/vd/objets-2025.json")["objets"]] == ["vd/25_LEG_12"]
    assert sorted(p.name for p in (tmp_path / "conseils/vd").glob("objets-*.json")) == [
        "objets-2025.json",
        "objets-2026.json",
    ]


def test_un_objet_sans_depot_est_classe_a_l_annee_de_sa_premiere_etape_datee(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(
        Affaire(
            id=340100,
            body_key="5586",
            number="INT25/056",
            title="Sur les horaires de la piscine",
            begin_date=None,
            etapes=[Etape("2026-01-20", harmonise_fr="Répondu"), Etape("2025-12-02")],
        )
    )

    _passer(tmp_path, monde, horloge)

    assert [o["cle"] for o in _lire(tmp_path, "conseils/5586/objets-2026.json")["objets"]] == ["5586/POS25-115"]
    lausanne_2025 = _lire(tmp_path, "conseils/5586/objets-2025.json")["objets"]
    assert [(o["cle"], o["depose"], o["derniere_etape"]) for o in lausanne_2025] == [
        ("5586/INT25-056", None, "2026-01-20")
    ]
    assert not list((tmp_path / "conseils/5938").glob("objets-*.json"))


def test_l_index_resume_chaque_conseil_dans_l_ordre_des_sources(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(id=341700, body_key="VD", number="26_QUE_60", title="Il y a quinze jours", begin_date="2026-10-01"),
        Affaire(id=341701, body_key="VD", number="26_QUE_61", title="Il y a quatorze jours", begin_date="2026-10-02"),
        Affaire(id=341702, body_key="VD", number="26_QUE_62", title="Sans aucune date", begin_date=None),
    ]
    monde.reunions += [
        Reunion(id=1034500, body_key="VD", group_id=1965, name="Séance", begin_date="2026-12-01T09:30:00"),
        Reunion(id=1034400, body_key="VD", group_id=1965, name="Séance", begin_date="2026-10-16T00:00:00"),
        Reunion(id=1029000, body_key="VD", group_id=1965, name="Séance", begin_date="2026-09-22T00:00:00"),
    ]

    _passer(tmp_path, monde, horloge)

    index = _lire(tmp_path, "conseils/index.json")
    assert (index["version"], index["communes"]) == (1, {})
    vd, lausanne, yverdon = index["conseils"]
    assert {k: v for k, v in vd.items() if k != "recents"} == {
        "cle": "vd",
        "source": "openparldata-vd",
        "nom": "Conseil VD",
        "commune": None,
        "donne": ["objets", "seances"],
        "objets": 4,
        "objets_par_annee": {"2025": 1, "2026": 3},
        "seances": 4,
        "prochaine_seance": "vd/2026-10-16",
        "derniere_seance": "vd/2026-10-06",
    }
    assert [o["cle"] for o in vd["recents"]] == ["vd/26_INT_140", "vd/26_QUE_61"]
    assert vd["recents"][0]["titre"] == "Covid 2020 six ans pour revenir en arrière"
    assert (lausanne["cle"], lausanne["commune"], lausanne["objets"], lausanne["recents"]) == ("5586", 5586, 1, [])
    assert yverdon == {
        "cle": "5938",
        "source": "openparldata-5938",
        "nom": "Conseil 5938",
        "commune": 5938,
        "donne": ["seances"],
        "objets": 0,
        "objets_par_annee": {},
        "recents": [],
        "seances": 1,
        "prochaine_seance": None,
        "derniere_seance": "5938/2026-10-01",
    }


def test_sans_objet_rattache_aucun_fichier_au_grand_conseil_n_est_ecrit(tmp_path):
    # Le rattachement par le nom (ticket #67) remplira `communes` ; d'ici là, aucune commune n'a d'Objet.
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde(horloge), horloge)

    assert _lire(tmp_path, "conseils/index.json")["communes"] == {}
    assert not (tmp_path / "conseils/communes").exists()


def _entree(cle, sorte, date, titre, communes=(), type=None, points=None):
    return {
        "cle": cle,
        "conseil": cle.split("/")[0],
        "sorte": sorte,
        "type": type,
        "date": date,
        "titre": titre,
        "communes": list(communes),
        "points": points,
    }


def test_le_fil_tient_21_jours_et_toutes_les_seances_a_venir_a_la_forme_du_fil(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(id=341600, body_key="VD", number="26_QUE_50", title="Au bord de la fenêtre", begin_date="2026-09-25"),
        Affaire(id=341601, body_key="VD", number="26_QUE_49", title="Juste avant", begin_date="2026-09-24"),
        Affaire(id=340200, body_key="5586", number="INT26/101", title="Sur les quais", begin_date="2026-10-13"),
    ]
    monde.reunions += [
        Reunion(id=1034500, body_key="VD", group_id=1965, name="Séance", begin_date="2026-12-01T09:30:00"),
        Reunion(id=1029000, body_key="VD", group_id=1965, name="Séance", begin_date="2026-09-22T00:00:00"),
    ]

    _passer(tmp_path, monde, horloge)

    fil = _lire(tmp_path, "conseils/fil.json")
    assert fil["version"] == 1
    lausanne = "Séance - Mardi 06 octobre 2026 2026 à 18:00 & 20:30"
    assert fil["entrees"] == [
        _entree("vd/2026-12-01", "seance", "2026-12-01T09:30", "Séance", points=0),
        _entree("5586/INT26-101", "objet", "2026-10-13", "Sur les quais", [5586], type="Interpellation"),
        _entree("5586/2026-10-06", "seance", "2026-10-06", lausanne, [5586], points=1),
        _entree("vd/2026-10-06", "seance", "2026-10-06", "Séance du Grand Conseil du mardi 6 octobre 2026", points=2),
        _entree(
            "vd/26_INT_140", "objet", "2026-10-06", "Covid 2020 six ans pour revenir en arrière", type="Interpellation"
        ),
        _entree(
            "5938/2026-10-01", "seance", "2026-10-01T20:00", "Séance du Conseil communal du 1er octobre 2026", [5938],
            points=1,
        ),
        _entree("vd/26_QUE_50", "objet", "2026-09-25", "Au bord de la fenêtre", type="Interpellation"),
    ]
