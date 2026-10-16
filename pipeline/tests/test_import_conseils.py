"""Le passage complet de l'import des conseils (`importer` → `vers_archive` → `lecture` → `ecrire`), lancé contre un
dossier temporaire qui tient lieu de clone du dépôt de données (spec de J1, « Décisions de test »).

Le faux OpenParlData est écrit à la main (`faux_openparldata.Monde`) et l'horloge est factice : on observe les
requêtes envoyées à l'API et les fichiers que le passage écrit. Le commit et le push restent en dehors.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx
import jsonschema
import pytest

from conseils import OpenParlData, cle_objet, importer_conseils
from schema import DOSSIER_SCHEMA, FichierSources
from faux_openparldata import (
    Affaire,
    Contributeur,
    Document,
    Etape,
    HorlogeFactice,
    Monde,
    Point,
    Reunion,
)

T0 = datetime(2026, 10, 16, 7, 5, tzinfo=UTC)


def _source(body_key, donne=("objets", "seances"), groupe=None):
    conseil = {"body_key": body_key, "donne": list(donne)} | ({"groupe": groupe} if groupe else {})
    return {
        "id": f"openparldata-{body_key.lower()}",
        "nom": f"Conseil {body_key} (OpenParlData)",
        "nom_court": f"Conseil {body_key}",
        "attribution": {"texte": "Source: OpenParlData.ch", "lien": "https://openparldata.ch", "licence": "CC BY 4.0"},
        "voie_acces": "cron",
        "fraicheur": "import",
        "conseil": conseil,
    }


SOURCES = FichierSources.model_validate(
    {
        "sources": [
            _source("VD", groupe=1965),
            _source("5586"),
            _source("5938", donne=["seances"]),
        ]
    }
)


def _monde(horloge):
    return Monde(
        horloge=horloge,
        affaires=[
            Affaire(
                id=341083,
                body_key="VD",
                number="26_INT_140",
                title="Covid 2020 six ans pour revenir en arrière",
                type_name="Interpellation",
                begin_date="2026-10-06",
                url="https://www.vd.ch/gc/point/4291d7bb",
                contributeurs=[
                    Contributeur("Pierre-François Mottier", "PLR", "Auteur"),
                    Contributeur("DSAS", None, "Federführung", type="group"),
                ],
                etapes=[
                    Etape("2026-10-06", harmonise_fr="Déposé"),
                    Etape(None, harmonise_fr="Transférer"),
                    Etape("2026-10-07", harmonise_fr="A l'ordre du jour"),
                ],
                documents=[
                    Document("Objet", "https://www.vd.ch/fileadmin/26_INT_140.pdf", "2026-10-06", "Objet"),
                    Document(None, "https://www.vd.ch/fileadmin/annexe.pdf", None, "Annexe"),
                ],
            ),
            Affaire(
                id=339001,
                body_key="VD",
                number="25_LEG_12",
                title="Exposé des motifs et projet de décret sur les routes cantonales",
                type_name="Décret/Loi",
                state_name="Adopté",
                begin_date="2025-11-04",
                etapes=[Etape("2025-11-04"), Etape("2026-03-10", harmonise_fr="Adopté")],
            ),
            Affaire(id=339002, body_key="VD", number="26_GRA_1", title="Demande de grâce", type_name="Grâce"),
            Affaire(
                id=340899,
                body_key="5586",
                number="POS25/115",
                title="Pour des préaux ouverts le week-end",
                type_name="Postulat",
                begin_date=None,
                etapes=[Etape("2026-09-01", titre_fr="Décision : Renvoi en Municipalité")],
            ),
        ],
        reunions=[
            Reunion(
                id=1033712,
                body_key="VD",
                group_id=1965,
                name="Séance du Grand Conseil du mardi 6 octobre 2026",
                begin_date="2026-10-06T00:00:00",
                url="https://www.vd.ch/gc/seance/1033712",
                points=[
                    Point(
                        3, "Interpellation Pierre-François Mottier - Covid 2020", "26_INT_140", resultat="Transmise au CE"
                    ),
                    Point(2, "Simple question - Galère La Liberté", "26_QUE_88"),
                ],
            ),
            Reunion(
                id=1033800,
                body_key="VD",
                group_id=3726,
                name="Séance du Conseil d'Etat du 7 octobre 2026",
                begin_date="2026-10-07T00:00:00",
            ),
            Reunion(
                id=33001,
                body_key="5586",
                name="Séance - Mardi 06 octobre 2026 2026 à 18:00 & 20:30",
                begin_date="2026-10-06T00:00:00",
                points=[Point(1, "Postulat - Préaux ouverts", "POS25/115", affaire_id=340899, categorie="RAPPORTS")],
            ),
            Reunion(
                id=33831,
                body_key="5938",
                group_id=8921,
                name="Séance du Conseil communal du 1er octobre 2026",
                begin_date="2026-10-01T20:00:00",
                points=[Point(1, "Appel")],
            ),
        ],
    )


def _passer(depot, monde, horloge, sources=SOURCES):
    with httpx.Client(transport=monde.transport()) as http:
        opd = OpenParlData(http, horloge, attendre=horloge.attendre)
        importer_conseils(depot, sources, opd, horloge)


def _lire(depot, chemin):
    return json.loads((depot / chemin).read_text(encoding="utf-8"))


def test_le_premier_import_ecrit_chaque_objet_dans_l_archive_normalise(tmp_path):
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde(horloge), horloge)

    assert _lire(tmp_path, "conseils/vd/objets/26_INT_140.json") == {
        "version": 1,
        "genere": "2026-10-16T07:05:00Z",
        "id": 341083,
        "numero": "26_INT_140",
        "type": "Interpellation",
        "statut": {"libelle": "A l'ordre du jour", "date": "2026-10-07"},
        "depose": "2026-10-06",
        "titre": "Covid 2020 six ans pour revenir en arrière",
        "contributeurs": [
            {"nom": "Pierre-François Mottier", "parti": "PLR", "role": "Auteur", "sorte": "personne"},
            {"nom": "DSAS", "parti": None, "role": "Federführung", "sorte": "groupe"},
        ],
        "etapes": [
            {"date": "2026-10-06", "libelle": "Déposé"},
            {"date": "2026-10-07", "libelle": "A l'ordre du jour"},
        ],
        "documents": [
            {"titre": "Objet", "date": "2026-10-06", "lien": "https://www.vd.ch/fileadmin/26_INT_140.pdf"},
            {"titre": "Annexe", "date": None, "lien": "https://www.vd.ch/fileadmin/annexe.pdf"},
        ],
        "lien": "https://www.vd.ch/gc/point/4291d7bb",
        "communes": [],
    }


def test_les_seances_sont_archivees_par_jour_avec_leur_ordre_du_jour_et_sans_le_conseil_d_etat(tmp_path):
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde(horloge), horloge)

    assert _lire(tmp_path, "conseils/vd/seances/2026-10-06.json") == {
        "version": 1,
        "genere": "2026-10-16T07:05:00Z",
        "id": 1033712,
        "date": "2026-10-06",
        "nom": "Séance du Grand Conseil du mardi 6 octobre 2026",
        "lien": "https://www.vd.ch/gc/seance/1033712",
        "ordre_du_jour": [
            {
                "numero": "2",
                "titre": "Simple question - Galère La Liberté",
                "categorie": None,
                "resultat": None,
                "objet": None,
            },
            {
                "numero": "3",
                "titre": "Interpellation Pierre-François Mottier - Covid 2020",
                "categorie": None,
                "resultat": "Transmise au CE",
                "objet": "vd/26_INT_140",
            },
        ],
    }
    assert _lire(tmp_path, "conseils/5586/seances/2026-10-06.json")["ordre_du_jour"][0]["objet"] == "5586/POS25-115"
    assert _lire(tmp_path, "conseils/5938/seances/2026-10-01.json")["date"] == "2026-10-01T20:00"
    assert sorted(p.name for p in (tmp_path / "conseils/vd/seances").iterdir()) == ["2026-10-06.json"]


def test_les_demandes_de_grace_ne_sont_pas_des_objets_et_la_barre_oblique_du_numero_devient_un_tiret(tmp_path):
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde(horloge), horloge)

    assert sorted(p.name for p in (tmp_path / "conseils/vd/objets").iterdir()) == ["25_LEG_12.json", "26_INT_140.json"]
    lausanne = _lire(tmp_path, "conseils/5586/objets/POS25-115.json")
    assert (lausanne["numero"], lausanne["depose"], lausanne["statut"]) == (
        "POS25/115",
        None,
        {"libelle": "Décision : Renvoi en Municipalité", "date": "2026-09-01"},
    )
    assert _lire(tmp_path, "conseils/vd/objets/25_LEG_12.json")["statut"] == {"libelle": "Adopté", "date": "2026-03-10"}
    assert not (tmp_path / "conseils/5938/objets").exists()


def test_un_numero_a_espaces_donne_une_cle_sans_espace(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(Affaire(id=342200, body_key="VD", number="V 1.9.2026", title="Divers", type_name="Divers"))
    monde.reunions[0].points.append(Point(4, "Divers", "V 1.9.2026"))

    _passer(tmp_path, monde, horloge)

    assert _lire(tmp_path, "conseils/vd/objets/V_1.9.2026.json")["numero"] == "V 1.9.2026"
    assert _lire(tmp_path, "conseils/vd/seances/2026-10-06.json")["ordre_du_jour"][-1]["objet"] == "vd/V_1.9.2026"


# Les mêmes cas que `cleObjet` du site (`web/src/lib/couches/conseils/numeros.test.ts`), qui ouvre un Objet par la
# clé que le cron a donnée à son fichier : un cas ajouté d'un côté s'ajoute de l'autre.
@pytest.mark.parametrize(
    ("conseil", "numero", "cle"),
    [
        ("vd", "26_INT_140", "vd/26_INT_140"),
        ("vd", "8_LEG_124", "vd/8_LEG_124"),
        ("vd", "V 1.9.2026", "vd/V_1.9.2026"),
        ("vd", "  21_POS_3 ", "vd/21_POS_3"),
        ("5586", "POS25/115", "5586/POS25-115"),
        ("5586", "INT26/056", "5586/INT26-056"),
        ("5586", "PR 25/3/bis", "5586/PR_25-3-bis"),
        ("5586", "INT \t 26/056", "5586/INT_26-056"),
        ("5586", "INT 26/056", "5586/INT_26-056"),
    ],
)
def test_la_cle_d_un_objet_est_celle_que_le_site_calcule(conseil, numero, cle):
    assert cle_objet(conseil, numero) == cle


def test_a_numero_egal_l_objet_au_plus_petit_identifiant_l_emporte_d_un_import_a_l_autre(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(id=29001, body_key="5586", number="Q22/014", title="Première question", type_name="Question écrite"),
        Affaire(id=29500, body_key="5586", number="Q22/014", title="Doublon", type_name="Question écrite"),
    ]
    _passer(tmp_path, monde, horloge)
    premier = _lire(tmp_path, "conseils/5586/objets/Q22-014.json")

    horloge.heure = T0 + timedelta(days=1)
    monde.affaires[-1].updated_at = "2026-10-17"  # seul le doublon revient à l'import suivant
    _passer(tmp_path, monde, horloge)

    assert premier["titre"] == "Première question"
    assert _lire(tmp_path, "conseils/5586/objets/Q22-014.json") == premier


def test_la_pagination_est_suivie_jusqu_au_bout_sans_parametre_repete(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(id=342000 + i, body_key="VD", number=f"26_QUE_{i}", title=f"Question {i}", type_name="Simple question")
        for i in range(5)
    ]

    _passer(tmp_path, monde, horloge)

    assert len(list((tmp_path / "conseils/vd/objets").iterdir())) == 7
    pages = [r for r in monde.requetes_vers("affairs") if r.url.params["body_key"] == "VD"]
    assert [r.url.params["offset"] for r in pages] == ["0", "2", "4", "6"]
    for _, requete in monde.requetes:
        cles = [cle for cle, _ in requete.url.params.multi_items()]
        assert len(cles) == len(set(cles)), requete.url


def test_au_moins_une_seconde_separe_deux_requetes_et_chacune_s_identifie(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)

    _passer(tmp_path, monde, horloge)

    heures = [h for h, _ in monde.requetes]
    assert len(heures) > 5
    assert all(b - a >= timedelta(seconds=1) for a, b in zip(heures, heures[1:]))
    assert all("VigieVaud" in r.headers["User-Agent"] and "@" in r.headers["User-Agent"] for _, r in monde.requetes)


def _genere_de_chaque_fichier(depot):
    return {str(p.relative_to(depot)): json.loads(p.read_text())["genere"] for p in depot.rglob("*.json")}


def test_le_premier_import_demande_tout_l_historique_et_note_la_date_de_chaque_conseil(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)

    _passer(tmp_path, monde, horloge)

    assert all("from_updated_at" not in r.url.params for _, r in monde.requetes)
    assert _lire(tmp_path, "conseils/import.json") == {
        "version": 1,
        "genere": "2026-10-16T07:05:00Z",
        "conseils": {"vd": "2026-10-16T07:05:00Z", "5586": "2026-10-16T07:05:00Z", "5938": "2026-10-16T07:05:00Z"},
    }


def test_l_import_suivant_ne_demande_que_les_changements_depuis_la_veille_du_dernier_import(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)
    monde.requetes.clear()

    horloge.heure = T0 + timedelta(days=1)
    _passer(tmp_path, monde, horloge)

    assert {r.url.params.get("from_updated_at") for _, r in monde.requetes} == {"2026-10-15"}
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["vd"] == "2026-10-17T07:05:00Z"


def test_sans_changement_seul_import_json_est_reecrit(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)
    avant = _genere_de_chaque_fichier(tmp_path)

    horloge.heure = T0 + timedelta(days=1)
    for e in monde.affaires + monde.reunions:
        e.updated_at = "2026-10-17"  # réimportation par OpenParlData, sans vrai changement
    _passer(tmp_path, monde, horloge)

    apres = _genere_de_chaque_fichier(tmp_path)
    assert {c for c in apres if apres[c] != avant[c]} == {"conseils/import.json"}


def test_un_objet_modifie_seul_son_fichier_est_reecrit_et_rien_n_est_supprime(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)
    avant = _genere_de_chaque_fichier(tmp_path)

    horloge.heure = T0 + timedelta(days=1)
    modifie = next(a for a in monde.affaires if a.number == "25_LEG_12")
    modifie.state_name, modifie.updated_at = "Retiré", "2026-10-17"
    monde.affaires = [a for a in monde.affaires if a.number != "26_INT_140"]  # disparu d'OpenParlData
    _passer(tmp_path, monde, horloge)

    apres = _genere_de_chaque_fichier(tmp_path)
    assert set(apres) == set(avant)
    assert {c for c in apres if apres[c] != avant[c]} == {
        "conseils/import.json",
        "conseils/vd/objets/25_LEG_12.json",
        "conseils/vd/objets-2025.json",  # sa ligne légère, qui porte son statut
    }
    assert _lire(tmp_path, "conseils/vd/objets/25_LEG_12.json")["statut"]["libelle"] == "Retiré"
    assert _lire(tmp_path, "conseils/vd/objets/26_INT_140.json")["numero"] == "26_INT_140"


def test_un_conseil_en_echec_garde_sa_date_et_n_empeche_pas_les_autres(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)

    horloge.heure = T0 + timedelta(days=1)
    monde.en_panne = {"VD"}
    monde.reunions.append(
        Reunion(id=33002, body_key="5586", name="Séance", begin_date="2026-10-13T00:00:00", updated_at="2026-10-17")
    )
    monde.affaires.append(
        Affaire(id=342100, body_key="VD", number="26_MOT_20", title="Motion", updated_at="2026-10-17")
    )
    _passer(tmp_path, monde, horloge)

    assert _lire(tmp_path, "conseils/import.json")["conseils"] == {
        "vd": "2026-10-16T07:05:00Z",
        "5586": "2026-10-17T07:05:00Z",
        "5938": "2026-10-17T07:05:00Z",
    }
    assert (tmp_path / "conseils/5586/seances/2026-10-13.json").exists()
    assert not (tmp_path / "conseils/vd/objets/26_MOT_20.json").exists()


def test_une_erreur_imprevue_d_un_conseil_n_empeche_pas_d_ecrire_les_autres(tmp_path, capsys):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)

    horloge.heure = T0 + timedelta(days=1)
    monde.reunions.append(
        Reunion(id=33002, body_key="5586", name="Séance", begin_date="2026-10-13T00:00:00", updated_at="2026-10-17")
    )

    def repondre(requete):
        # Une réponse d'une forme inattendue pour le Grand Conseil : ni erreur HTTP, ni `ValueError`.
        if requete.url.params.get("body_key") == "VD":
            return httpx.Response(200, json={"meta": {"has_more": False}, "data": [42]})
        return monde.transport().handle_request(requete)

    with httpx.Client(transport=httpx.MockTransport(repondre)) as http:
        importer_conseils(tmp_path, SOURCES, OpenParlData(http, horloge, attendre=horloge.attendre), horloge)

    assert _lire(tmp_path, "conseils/import.json")["conseils"] == {
        "vd": "2026-10-16T07:05:00Z",
        "5586": "2026-10-17T07:05:00Z",
        "5938": "2026-10-17T07:05:00Z",
    }
    assert (tmp_path / "conseils/5586/seances/2026-10-13.json").exists()
    assert "Import en échec : Conseil VD (OpenParlData)" in capsys.readouterr().err


def _schema_du_fichier(chemin):
    """Le document du schéma commun que doit suivre un fichier du dossier `conseils/`."""
    if chemin.parent.name in ("objets", "seances"):
        return {"objets": "objet", "seances": "seance"}[chemin.parent.name]
    if chemin.parent.name == "communes":
        return "rattachements-commune"
    if chemin.name.startswith("objets-"):
        return "liste-objets"
    noms = {"import.json": "import-conseils", "index.json": "index-conseils", "fil.json": "fil-conseils"}
    return noms.get(chemin.name, "liste-seances" if chemin.name == "seances.json" else None)


def test_chaque_fichier_ecrit_est_valide_au_json_schema(tmp_path):
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde(horloge), horloge)

    fichiers = sorted(tmp_path.rglob("*.json"))
    assert len(fichiers) == 15  # 7 d'archive et d'import, 8 de lecture
    for fichier in fichiers:
        nom = _schema_du_fichier(fichier.relative_to(tmp_path))
        schema = json.loads((DOSSIER_SCHEMA / f"{nom}.schema.json").read_text())
        jsonschema.validate(json.loads(fichier.read_text()), schema)


def _monde_avec_petition(horloge):
    """Le monde de base, plus une pétition de Lausanne qui nomme son pétitionnaire, une interpellation d'une élue, et
    un point de grâce au Grand Conseil. « Exemple » ne nomme que des particuliers."""
    monde = _monde(horloge)
    monde.affaires += [
        Affaire(
            id=340950,
            body_key="5586",
            number="PET25/003",
            title="Pétition de M. Paul Exemple et consorts (312 signatures) : « Pour un parc à chiens »",
            type_name="Pétition",
            # OpenParlData nomme parfois un·e pétitionnaire du nom complet d'un·e élu·e : le prénom et le nom de
            # famille de la source l'emportent.
            contributeurs=[Contributeur("Léa Conseillère", None, "Auteur", prenom="Paul", nom_de_famille="Exemple")],
            documents=[
                Document(
                    "Pétition de Exemple Paul - chemin des Lilas 2 - 1000 Lausanne - Pour un parc à chiens",
                    "https://www.lausanne.ch/pet25-003.pdf",
                ),
                Document("PET25-003 Plan du parc à chiens.pdf", "https://www.lausanne.ch/pet25-003-annexe.pdf"),
                Document("2025_08_rp_petition_paul_exemple_parc_a_chiens.pdf v1.0", "https://www.lausanne.ch/rp.pdf"),
            ],
        ),
        Affaire(
            id=340951,
            body_key="5586",
            number="INT25/020",
            title="Interpellation de Mme Léa Conseillère : « Des bancs »",
            contributeurs=[Contributeur("Léa Conseillère", "PS", "Auteur")],
            documents=[
                Document("Interpellation de Mme Léa Conseillère - Des bancs", "https://www.lausanne.ch/int25-020.pdf"),
                Document(None, "https://www.lausanne.ch/int25-020-annexe.pdf", categorie="Annexe"),
                # Le rapport-préavis qui répond à la pétition et à l'interpellation, joint aux deux Objets.
                Document("2025_08_rp_petition_paul_exemple_parc_a_chiens.pdf v1.0", "https://www.lausanne.ch/rp-2.pdf"),
            ],
        ),
    ]
    monde.reunions[2].points += [
        Point(2, "Pétition de M. Paul Exemple et consorts : « Pour un parc à chiens »", "PET25/003", affaire_id=340950),
        Point(3, "Interpellation de Mme Léa CONSEILLÈRE : « Des bancs »", "INT25/020", affaire_id=340951),
        Point(4, "Communication - Pétition du Comité des Lilas (Paul Exemple) : « Un parc »", "PET25/003", affaire_id=340950),
    ]
    monde.reunions[0].points += [
        Point(5, "Demande de grâce de M. Marc Exemple", "26_GRA_1"),
        Point(6, "Recours en grâce Zoé Exemple"),  # sans numéro d'Objet : reconnu à son titre
        Point(7, "Grâce aux vélos, des rues apaisées"),
    ]
    return monde


def test_aucun_nom_masque_n_atteint_l_archive_et_une_petition_n_a_pas_d_auteur(tmp_path):
    horloge = HorlogeFactice(T0)

    _passer(tmp_path, _monde_avec_petition(horloge), horloge)

    for fichier in tmp_path.rglob("*.json"):
        assert "Exemple" not in fichier.read_text(encoding="utf-8"), fichier
    petition = _lire(tmp_path, "conseils/5586/objets/PET25-003.json")
    assert (petition["titre"], petition["contributeurs"]) == (
        "Pétition de [particulier] et consorts (312 signatures) : « Pour un parc à chiens »",
        [],
    )
    # Les titres de documents sont masqués comme celui de l'Objet ; le ou la pétitionnaire que la source connaît l'est
    # aussi dans un nom de fichier, et dans le même document joint à un autre Objet (ADR 0007).
    assert [d["titre"] for d in petition["documents"]] == [
        "Pétition de [particulier] - [coordonnées] - Pour un parc à chiens",
        "PET25-003 Plan du parc à chiens.pdf",
        "2025_08_rp_petition_[particulier]_parc_a_chiens.pdf v1.0",
    ]
    interpellation = _lire(tmp_path, "conseils/5586/objets/INT25-020.json")
    assert [d["titre"] for d in interpellation["documents"]] == [
        "Interpellation de Mme Léa Conseillère - Des bancs",
        "Annexe",
        "2025_08_rp_petition_[particulier]_parc_a_chiens.pdf v1.0",
    ]
    lausanne = _lire(tmp_path, "conseils/5586/seances/2026-10-06.json")["ordre_du_jour"]
    assert [p["titre"] for p in lausanne] == [
        "Postulat - Préaux ouverts",
        "Pétition de [particulier] et consorts : « Pour un parc à chiens »",
        "Interpellation de Mme Léa CONSEILLÈRE : « Des bancs »",
        "Communication - Pétition du Comité des Lilas ([particulier]) : « Un parc »",
    ]
    grand_conseil = _lire(tmp_path, "conseils/vd/seances/2026-10-06.json")["ordre_du_jour"]
    assert [p["numero"] for p in grand_conseil] == ["2", "3", "7"]


def test_les_elus_connus_viennent_aussi_de_l_archive(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde_avec_petition(horloge)
    _passer(tmp_path, monde, horloge)

    horloge.heure = T0 + timedelta(days=1)
    monde.reunions.append(
        Reunion(
            id=33002,
            body_key="5586",
            name="Séance",
            begin_date="2026-10-13T00:00:00",
            updated_at="2026-10-17",
            points=[
                Point(1, "Interpellation de Mme Léa Conseillère : « Des tables »"),
                Point(2, "Pétition de M. Paul Exemple : « Des chaises »"),
            ],
        )
    )
    _passer(tmp_path, monde, horloge)

    points = _lire(tmp_path, "conseils/5586/seances/2026-10-13.json")["ordre_du_jour"]
    assert [p["titre"] for p in points] == [
        "Interpellation de Mme Léa Conseillère : « Des tables »",
        "Pétition de [particulier] : « Des chaises »",
    ]
