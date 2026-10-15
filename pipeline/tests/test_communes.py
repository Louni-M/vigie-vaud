"""Préparation des communes : communes.json et communes-limites.json (#27)."""

import pytest
from pyproj import Transformer
from shapely.geometry import Point, box

from communes import HotelsHorsTerre
from faux_services import Commune, Etat, Monde, Mutation, carre, hotel, preparer

VERS_LV95 = Transformer.from_crs(4326, 2056, always_xy=True)

ASSENS = Commune(5511, "Assens", carre(2536000, 1162000))


def en_lv95(position: list[float]) -> tuple[float, float]:
    return VERS_LV95.transform(*position)


@pytest.mark.parametrize(
    ("nom", "slug"),
    [("Dompierre (VD)", "dompierre"), ("Blonay - Saint-Légier", "blonay-saint-legier"),
     ("Château-d'Oex", "chateau-d-oex"), ("Goumoëns", "goumoens"), ("Arzier-Le Muids", "arzier-le-muids")],
)
def test_le_slug_d_une_commune_ne_change_pas_puisqu_il_sert_d_adresse(tmp_path, nom, slug):
    monde = Monde(communes=[Commune(5511, nom, carre(2536000, 1162000))])

    [commune] = preparer(monde, tmp_path, [hotel(5511, nom, 2537000, 1163000)])

    assert commune["slug"] == slug


def test_l_hotel_de_ville_est_place_et_decrit_d_apres_le_csv(tmp_path):
    monde = Monde(communes=[ASSENS])

    [commune] = preparer(monde, tmp_path, [
        hotel(5511, "Assens", 2537000, 1163000, "Route de Saint-Germain 3, 1042 Assens", "adresse:333"),
    ])

    e, n = en_lv95(commune["hotel"])
    assert abs(e - 2537000) < 1 and abs(n - 1163000) < 1
    assert commune["adresse"] == "Route de Saint-Germain 3, 1042 Assens"


def test_une_commune_absente_du_csv_passe_en_repli_sur_la_terre_ferme_avec_un_avertissement(tmp_path, capsys):
    # Une commune née d'une fusion au 1ᵉʳ janvier, riveraine : seule sa bande nord est en terre ferme.
    nouvelle = Commune(5999, "Nouvelle-Riveraine", carre(2540000, 1150000))
    leman = box(2530000, 1140000, 2550000, 1151800)
    monde = Monde(communes=[ASSENS, nouvelle], lacs=[leman])

    communes = preparer(monde, tmp_path, [hotel(5511, "Assens", 2537000, 1163000, "Grand-Rue 1, 1042 Assens", "manuel")])

    riveraine = next(c for c in communes if c["bfs"] == 5999)
    assert riveraine["adresse"] == ""
    position = Point(en_lv95(riveraine["hotel"]))
    assert nouvelle.limites.contains(position) and not leman.intersects(position)
    assert "Nouvelle-Riveraine (5999)" in capsys.readouterr().err


def test_un_hotel_de_ville_dans_le_lac_ou_hors_de_sa_commune_arrete_la_preparation(tmp_path):
    pully = Commune(5590, "Pully", carre(2540000, 1150000))
    leman = box(2530000, 1140000, 2550000, 1151800)
    monde = Monde(communes=[ASSENS, pully], lacs=[leman])

    with pytest.raises(HotelsHorsTerre) as erreur:
        preparer(monde, tmp_path, [
            hotel(5511, "Assens", 2540500, 1163000, "Grand-Rue 1, 1042 Assens", "manuel"),  # chez la voisine
            hotel(5590, "Pully", 2541000, 1151000, "Avenue du Lac 1, 1009 Pully", "adresse:1"),  # dans le Léman
        ])

    assert "Assens (5511)" in str(erreur.value) and "Pully (5590)" in str(erreur.value)
    assert not (tmp_path / "static" / "communes.json").exists()


def test_le_cadre_d_une_commune_riveraine_est_sa_partie_terrestre_et_la_bbox_garde_le_lac(tmp_path):
    # Pully s'étend sur 2 km, dont les 1800 m du sud dans le Léman.
    pully = Commune(5590, "Pully", carre(2540000, 1150000))
    leman = box(2530000, 1140000, 2550000, 1151800)
    monde = Monde(communes=[pully], lacs=[leman])

    [commune] = preparer(monde, tmp_path, [hotel(5590, "Pully", 2541000, 1151900, "Avenue 1, 1009 Pully", "adresse:1")])

    ouest, sud, est, nord = commune["bbox"]
    assert en_lv95([ouest, sud]) == pytest.approx((2540000, 1150000), abs=50)
    assert en_lv95([est, nord]) == pytest.approx((2542000, 1152000), abs=50)
    ouest, sud, est, nord = commune["cadre"]
    assert en_lv95([ouest, sud]) == pytest.approx((2540000, 1151800), abs=50)
    assert en_lv95([est, nord]) == pytest.approx((2542000, 1152000), abs=50)


def _historique_vaudois() -> Monde:
    """Quelques fusions et changements de nom tirés du répertoire historisé de l'OFS."""
    bel = Commune(5613, "Bourg-en-Lavaux", carre(2546000, 1148000))
    yverdon = Commune(5938, "Yverdon-les-Bains", carre(2538000, 1180000))
    hautemorges = Commune(5656, "Hautemorges", carre(2520000, 1158000))
    return Monde(
        communes=[bel, yverdon, hautemorges, ASSENS],
        mutations=[
            # Réforme des districts de 2006 : même commune, même nom, nouvel état.
            Mutation("01.01.2006", [Etat(1, 5604, "Cully")], Etat(11, 5604, "Cully"), 24, 24),
            Mutation("01.01.2006", [Etat(2, 5606, "Epesses")], Etat(12, 5606, "Epesses"), 24, 24),
            Mutation("01.07.2011", [Etat(11, 5604, "Cully"), Etat(12, 5606, "Epesses"),
                                    Etat(3, 5612, "Villette (Lavaux)")], Etat(13, 5613, "Bourg-en-Lavaux")),
            # Changement de nom, puis fusion qui garde le nom et le n° OFS.
            Mutation("01.01.1982", [Etat(20, 5938, "Yverdon")], Etat(21, 5938, "Yverdon-les-Bains"), 23, 23),
            Mutation("01.07.2011", [Etat(21, 5938, "Yverdon-les-Bains"), Etat(22, 5926, "Gressy")],
                     Etat(23, 5938, "Yverdon-les-Bains")),
            # Fusions en chaîne : Bussy-Chardonney disparaît à son tour dans Hautemorges.
            Mutation("01.04.1961", [Etat(30, 5625, "Bussy-sur-Morges"), Etat(31, 5626, "Chardonney-sur-Morges")],
                     Etat(32, 5625, "Bussy-Chardonney")),
            Mutation("01.07.2021", [Etat(32, 5625, "Bussy-Chardonney"), Etat(33, 5628, "Pampigny")],
                     Etat(34, 5656, "Hautemorges")),
            # Une fusion dans un autre canton.
            Mutation("01.01.2017", [Etat(40, 2001, "Ailleurs-Dessus"), Etat(41, 2002, "Ailleurs-Dessous")],
                     Etat(42, 2003, "Ailleurs")),
        ],
    )


def test_chaque_commune_porte_ses_anciennes_communes_et_ses_anciens_noms(tmp_path):
    communes = preparer(_historique_vaudois(), tmp_path, [
        hotel(5613, "Bourg-en-Lavaux", 2547000, 1149000),
        hotel(5938, "Yverdon-les-Bains", 2539000, 1181000),
        hotel(5656, "Hautemorges", 2521000, 1159000),
        hotel(5511, "Assens", 2537000, 1163000),
    ])

    anciens = {c["nom"]: c["anciens"] for c in communes}
    assert anciens["Bourg-en-Lavaux"] == [
        {"nom": "Cully", "slug": "cully", "type": "Ancienne commune", "annee": 2011},
        {"nom": "Epesses", "slug": "epesses", "type": "Ancienne commune", "annee": 2011},
        {"nom": "Villette (Lavaux)", "slug": "villette-lavaux", "type": "Ancienne commune", "annee": 2011},
    ]
    assert anciens["Yverdon-les-Bains"] == [
        {"nom": "Gressy", "slug": "gressy", "type": "Ancienne commune", "annee": 2011},
        {"nom": "Yverdon", "slug": "yverdon", "type": "Ancien nom", "annee": 1982},
    ]
    assert anciens["Hautemorges"] == [
        {"nom": "Bussy-Chardonney", "slug": "bussy-chardonney", "type": "Ancienne commune", "annee": 2021},
        {"nom": "Bussy-sur-Morges", "slug": "bussy-sur-morges", "type": "Ancienne commune", "annee": 1961},
        {"nom": "Chardonney-sur-Morges", "slug": "chardonney-sur-morges", "type": "Ancienne commune", "annee": 1961},
        {"nom": "Pampigny", "slug": "pampigny", "type": "Ancienne commune", "annee": 2021},
    ]
    assert anciens["Assens"] == []
