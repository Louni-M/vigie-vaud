"""Outil d'initialisation des hôtels de ville : `hotels-de-ville.csv` et liste des cas à revoir (#25)."""

import pytest
from shapely.geometry import Point, box

from faux_services import Adresse, Commune, Fiche, Monde, Townhall, carre, ecrire_csv, executer

# Deux communes voisines qui partagent un NPA (comme Dompierre et Mauraz), chacune avec une « Rue du Village 1 ».
DOMPIERRE = Commune(5911, "Dompierre (VD)", carre(2540000, 1170000))
MAURAZ = Commune(5912, "Mauraz", carre(2542000, 1170000))


def test_le_siege_est_geocode_dans_sa_propre_commune_par_le_numero_ofs(tmp_path):
    monde = Monde(
        communes=[DOMPIERRE, MAURAZ],
        fiches=[
            Fiche("Dompierre (VD)", 5911, ["Administration communale", "Rue du Village 1", "1682 Dompierre VD"]),
            Fiche("Mauraz", 5912, ["Rue du Village 1", "1682 Dompierre VD"]),
        ],
        adresses=[
            Adresse(5912, "Rue du Village", "1", "1682 Dompierre VD", egid=222, e=2543000, n=1171000),
            Adresse(5911, "Rue du Village", "1", "1682 Dompierre VD", egid=111, e=2541000, n=1171000),
        ],
    )

    lignes, _ = executer(monde, tmp_path)

    assert lignes == [
        {"ofs": "5911", "nom": "Dompierre (VD)", "adresse": "Rue du Village 1, 1682 Dompierre VD",
         "E": "2541000", "N": "1171000", "origine": "adresse:111", "note": ""},
        {"ofs": "5912", "nom": "Mauraz", "adresse": "Rue du Village 1, 1682 Dompierre VD",
         "E": "2543000", "N": "1171000", "origine": "adresse:222", "note": ""},
    ]


def test_sans_rue_dans_l_annuaire_la_commune_passe_en_repli_sur_la_terre_ferme(tmp_path):
    # Une commune riveraine dont les limites couvrent surtout le lac : seule la bande nord est en terre ferme.
    riveraine = Commune(5590, "Pully", carre(2540000, 1150000))
    leman = box(2530000, 1140000, 2550000, 1151800)
    monde = Monde(
        communes=[riveraine],
        fiches=[Fiche("Pully", 5590, ["Hôtel de Ville", "Case postale", "1009 Pully"])],
        lacs=[leman],
    )

    lignes, revue = executer(monde, tmp_path)

    [ligne] = lignes
    assert (ligne["origine"], ligne["adresse"]) == ("repli", "")
    position = Point(float(ligne["E"]), float(ligne["N"]))
    assert riveraine.limites.contains(position) and not leman.intersects(position)
    assert [(r["ofs"], r["motif"]) for r in revue] == [("5590", "repli")]


def test_une_adresse_abregee_dans_l_annuaire_retrouve_son_libelle_officiel(tmp_path):
    assens = Commune(5511, "Assens", carre(2536000, 1162000))
    monde = Monde(
        communes=[assens],
        fiches=[Fiche("Assens", 5511, ["Rte St-Germain 3", "Case postale 12", "1042 Assens"])],
        adresses=[Adresse(5511, "Route de Saint-Germain", "3", "1042 Assens", egid=333, e=2537000, n=1163000)],
    )

    lignes, revue = executer(monde, tmp_path)

    assert [(l["adresse"], l["origine"]) for l in lignes] == [("Route de Saint-Germain 3, 1042 Assens", "adresse:333")]
    assert revue == []


def test_l_apostrophe_typographique_et_les_accents_de_l_annuaire_ne_genent_pas_l_appariement(tmp_path):
    bursins = Commune(5853, "Bursins", carre(2510000, 1144000))
    monde = Monde(
        communes=[bursins],
        fiches=[Fiche("Bursins", 5853, ["Greffe municipal", "Rue de l’Église 2", "1183 Bursins"])],
        adresses=[Adresse(5853, "Rue de l'Eglise", "2", "1183 Bursins", egid=827982, e=2511000, n=1145000)],
    )

    lignes, _ = executer(monde, tmp_path)

    assert [l["origine"] for l in lignes] == ["adresse:827982"]


@pytest.mark.parametrize(
    "lignes",
    [
        pytest.param(["Hôtel de Ville, Place Pestalozzi 2", "Case postale 355"], id="nom du bâtiment devant"),
        pytest.param(["Place Pestalozzi 2, Case postale 221"], id="case postale derrière"),
        pytest.param(["Commune de Yverdon - Place Pestalozzi 2"], id="tiret"),
        pytest.param(["Place Pestalozzi 2 / CP 14"], id="barre oblique"),
        pytest.param(["p.a. Place Pestalozzi 2 (2ème étage)"], id="par adresse et précision"),
    ],
)
def test_la_rue_du_siege_se_retrouve_parmi_les_mentions_de_l_annuaire(tmp_path, lignes):
    yverdon = Commune(5938, "Yverdon-les-Bains", carre(2538000, 1180000))
    monde = Monde(
        communes=[yverdon],
        fiches=[Fiche("Yverdon-les-Bains", 5938, [*lignes, "1401 Yverdon-les-Bains"])],
        adresses=[Adresse(5938, "Place Pestalozzi", "2", "1400 Yverdon-les-Bains", egid=444, e=2539000, n=1181000)],
    )

    lignes_csv, _ = executer(monde, tmp_path)

    assert [l["origine"] for l in lignes_csv] == ["adresse:444"]


def test_une_adresse_introuvable_ou_une_commune_absente_de_l_annuaire_passe_en_repli_a_revoir(tmp_path):
    monde = Monde(
        communes=[DOMPIERRE, MAURAZ],
        fiches=[Fiche("Dompierre (VD)", 5911, ["Rue du Vilage 1", "1682 Dompierre VD"])],
        adresses=[Adresse(5911, "Rue du Village", "1", "1682 Dompierre VD", egid=111, e=2541000, n=1171000)],
    )

    lignes, revue = executer(monde, tmp_path)

    assert [(l["ofs"], l["origine"], l["adresse"]) for l in lignes] == [("5911", "repli", ""), ("5912", "repli", "")]
    assert [(r["ofs"], r["motif"]) for r in revue] == [("5911", "adresse non appariée"), ("5912", "repli")]
    assert "Rue du Vilage 1" in revue[0]["detail"]


def _commune_geocodee(ofs: int, nom: str, e: float, n: float, coordonnees: str = "0 - 0"):
    """Une commune de 2 km de côté dont le siège, « Grand-Rue 1 », est au centre (e + 1000, n + 1000)."""
    return (
        Commune(ofs, nom, carre(e, n)),
        Fiche(nom, ofs, ["Grand-Rue 1", f"1000 {nom}"], coordonnees),
        Adresse(ofs, "Grand-Rue", "1", f"1000 {nom}", egid=ofs * 10, e=e + 1000, n=n + 1000),
    )


def test_la_revue_signale_les_ecarts_de_plus_de_150_m_avec_osm_bien_nomme_ou_les_coordonnees_ucv(tmp_path):
    loin_osm = _commune_geocodee(1, "Loin-OSM", 2500000, 1150000)
    salle = _commune_geocodee(2, "Salle", 2502000, 1150000)
    proche = _commune_geocodee(3, "Proche", 2504000, 1150000, coordonnees="505000 - 151000")
    loin_ucv = _commune_geocodee(4, "Loin-UCV", 2506000, 1150000, coordonnees="507600 - 151000")
    mondes = [loin_osm, salle, proche, loin_ucv]
    monde = Monde(
        communes=[c for c, _, _ in mondes],
        fiches=[f for _, f, _ in mondes],
        adresses=[a for _, _, a in mondes],
        townhalls=[
            Townhall("Administration communale", 2501400, 1151000),  # 400 m du siège de Loin-OSM
            Townhall("Grande Salle", 2503400, 1151000),  # 400 m, mais ce n'est pas une administration
            Townhall("Hôtel de Ville", 2505100, 1151000),  # 100 m du siège de Proche
        ],
    )

    _, revue = executer(monde, tmp_path)

    assert [(r["nom"], r["motif"]) for r in revue] == [("Loin-OSM", "écart"), ("Loin-UCV", "écart")]
    assert "400 m" in revue[0]["detail"] and "OSM" in revue[0]["detail"]
    assert revue[1]["detail"] == "à 600 m des coordonnées UCV ; aucun townhall OSM bien nommé dans la commune"


def test_un_ecart_avec_les_coordonnees_ucv_n_est_signale_que_si_osm_ne_confirme_pas_le_siege(tmp_path):
    # Les coordonnées UCV sont arrondies à 100 m : un townhall OSM bien nommé à moins de 80 m du siège l'emporte.
    confirmee = _commune_geocodee(1, "Confirmée", 2500000, 1150000, coordonnees="501600 - 151000")
    eloignee = _commune_geocodee(2, "Éloignée", 2502000, 1150000, coordonnees="503600 - 151000")
    mondes = [confirmee, eloignee]
    monde = Monde(
        communes=[c for c, _, _ in mondes],
        fiches=[f for _, f, _ in mondes],
        adresses=[a for _, _, a in mondes],
        townhalls=[
            Townhall("Administration communale", 2501050, 1151000),  # 50 m du siège de Confirmée
            Townhall("Maison de commune", 2503120, 1151000),  # 120 m du siège d'Éloignée : ne confirme pas
        ],
    )

    _, revue = executer(monde, tmp_path)

    assert [(r["nom"], r["motif"]) for r in revue] == [("Éloignée", "écart")]
    assert revue[0]["detail"] == "à 600 m des coordonnées UCV ; townhall OSM « Maison de commune » à 120 m"


def test_aucune_donnee_osm_n_est_ecrite_dans_le_csv(tmp_path):
    monde = Monde(
        communes=[DOMPIERRE],
        fiches=[Fiche("Dompierre (VD)", 5911, ["Rue Inconnue 9", "1682 Dompierre VD"])],
        townhalls=[Townhall("Administration communale de Dompierre", 2541234, 1171234)],
    )

    executer(monde, tmp_path)

    texte = (tmp_path / "hotels-de-ville.csv").read_text(encoding="utf-8")
    assert "Administration communale" not in texte
    assert "2541234" not in texte and "1171234" not in texte


def test_une_nouvelle_execution_ne_deplace_jamais_une_ligne_manuel_et_garde_les_notes(tmp_path):
    monde = Monde(
        communes=[DOMPIERRE, MAURAZ],
        fiches=[Fiche("Dompierre (VD)", 5911, ["Rue du Vilage 1", "1682 Dompierre VD"])],
        adresses=[Adresse(5911, "Rue du Village", "1", "1682 Dompierre VD", egid=111, e=2541000, n=1171000)],
    )
    lignes, _ = executer(monde, tmp_path)
    corrigee = {"ofs": "5911", "nom": "Dompierre (VD)", "adresse": "Rue du Village 1, 1682 Dompierre VD",
                "E": "2541010", "N": "1171020", "origine": "manuel", "note": "Faute de frappe dans l'annuaire"}
    lignes[0] = corrigee
    lignes[1]["note"] = "Repli assumé : pas de bâtiment administratif"
    ecrire_csv(tmp_path / "hotels-de-ville.csv", lignes)

    relancees, revue = executer(monde, tmp_path)

    assert relancees[0] == corrigee
    assert relancees[1]["note"] == "Repli assumé : pas de bâtiment administratif"
    assert [r["ofs"] for r in revue] == ["5912"]
