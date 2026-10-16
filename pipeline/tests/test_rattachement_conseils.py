"""Le rattachement par le nom dans le passage complet de l'import des conseils (ticket #67 ; ADR 0016) : les Objets
du Grand Conseil rattachés par leur titre masqué et le texte de leurs documents, `corrections.json`, les documents
tardifs, et les fichiers de lecture qui s'en remplissent. Contre un dossier temporaire qui tient lieu de clone du
dépôt de données, avec le faux OpenParlData et l'horloge factice de `test_import_conseils`.
"""

import json
from datetime import timedelta

import httpx
import jsonschema

from conseils import OpenParlData, importer_conseils
from faux_openparldata import Affaire, Contributeur, Document, HorlogeFactice, Point, Reunion
from schema import DOSSIER_SCHEMA, RACINE
from test_import_conseils import SOURCES, T0, _lire, _monde, _schema_du_fichier

COMMUNES = json.loads((RACINE / "web/static/communes.json").read_text(encoding="utf-8"))
OFS = {c["nom"]: c["bfs"] for c in COMMUNES}
BOURG_EN_LAVAUX, NYON, MORGES, LAUSANNE = (OFS[n] for n in ("Bourg-en-Lavaux", "Nyon", "Morges", "Lausanne"))
CAVES = "conseils/vd/objets/26_INT_150.json"


def _passer(depot, monde, horloge, communes=None):
    chemin = None
    if communes is not None:
        chemin = depot.parent / "communes.json"
        chemin.write_text(json.dumps(communes, ensure_ascii=False), encoding="utf-8")
    with httpx.Client(transport=monde.transport()) as http:
        opd = OpenParlData(http, horloge, attendre=horloge.attendre)
        if chemin is None:
            importer_conseils(depot, SOURCES, opd, horloge)
        else:
            importer_conseils(depot, SOURCES, opd, horloge, communes=chemin)


def _caves(**autres):
    """Une interpellation du Grand Conseil dont le titre nomme Cully (ancienne commune de Bourg-en-Lavaux) et dont
    les documents citent Nyon plus souvent que Morges."""
    return Affaire(
        id=341200,
        body_key="VD",
        number="26_INT_150",
        title="Les caves de Cully sont-elles menacées ?",
        begin_date="2026-10-08",
        documents=[
            Document(
                "Réponse du Conseil d'Etat",
                "https://sieldocs.vd.ch/reponse.pdf",
                texte="Les caves de Nyon et de Morges sont comparées à celles de Nyon. "
                "Ainsi adopté, en séance du Conseil d'Etat, à Lausanne, le 7 octobre 2026.",
            ),
            Document("Annexe", "https://sieldocs.vd.ch/annexe.pdf", texte="Carte des vignobles de Nyon et de Cully."),
            Document(None, "https://www.vd.ch/video", categorie="Vidéo"),
        ],
        **autres,
    )


def _communes(depot, chemin=CAVES):
    return [(c["ofs"], c["origine"]) for c in _lire(depot, chemin)["communes"]]


def test_un_objet_du_grand_conseil_est_rattache_par_son_titre_puis_par_ses_documents(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(_caves())

    _passer(tmp_path, monde, horloge)

    assert _communes(tmp_path) == [(BOURG_EN_LAVAUX, "titre"), (NYON, "document"), (MORGES, "document")]
    assert "comparées" not in (tmp_path / CAVES).read_text(encoding="utf-8")  # le texte n'est pas conservé
    assert _communes(tmp_path, "conseils/vd/objets/26_INT_140.json") == []


def test_les_fichiers_de_lecture_portent_les_communes_rattachees(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(_caves())

    _passer(tmp_path, monde, horloge)

    rattachees = [
        {"ofs": BOURG_EN_LAVAUX, "origine": "titre"},
        {"ofs": NYON, "origine": "document"},
        {"ofs": MORGES, "origine": "document"},
    ]
    index = _lire(tmp_path, "conseils/index.json")
    assert index["communes"] == {str(BOURG_EN_LAVAUX): 1, str(MORGES): 1, str(NYON): 1}
    au_grand_conseil = _lire(tmp_path, f"conseils/communes/{NYON}.json")
    assert (au_grand_conseil["commune"], [o["cle"] for o in au_grand_conseil["objets"]]) == (NYON, ["vd/26_INT_150"])
    assert au_grand_conseil["objets"][0]["communes"] == rattachees
    assert sorted(p.name for p in (tmp_path / "conseils/communes").iterdir()) == sorted(
        f"{ofs}.json" for ofs in (BOURG_EN_LAVAUX, NYON, MORGES)
    )
    (entree,) = [e for e in _lire(tmp_path, "conseils/fil.json")["entrees"] if e["cle"] == "vd/26_INT_150"]
    assert entree["communes"] == [BOURG_EN_LAVAUX, NYON, MORGES]
    (ligne,) = [o for o in _lire(tmp_path, "conseils/vd/objets-2026.json")["objets"] if o["cle"] == "vd/26_INT_150"]
    assert ligne["communes"] == rattachees
    assert [o["communes"] for o in index["conseils"][0]["recents"] if o["cle"] == "vd/26_INT_150"] == [rattachees]
    for fichier in sorted(tmp_path.rglob("*.json")):
        nom = _schema_du_fichier(fichier.relative_to(tmp_path))
        schema = json.loads((DOSSIER_SCHEMA / f"{nom}.schema.json").read_text())
        jsonschema.validate(json.loads(fichier.read_text()), schema)


def test_le_titre_est_lu_apres_masquage(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(
        Affaire(
            id=341300,
            body_key="VD",
            number="26_PET_9",
            title="Pétition de Mme Anne Morges : « Un banc à Nyon »",
            type_name="Pétition",
            contributeurs=[Contributeur("Anne Morges")],
        )
    )

    _passer(tmp_path, monde, horloge)

    assert _communes(tmp_path, "conseils/vd/objets/26_PET_9.json") == [(NYON, "titre")]


def test_au_dela_de_10_communes_dans_les_documents_seul_le_titre_compte(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    liste = "Liste des communes : " +", ".join(c["nom"] for c in COMMUNES[:11]) + "."
    monde.affaires.append(
        Affaire(
            id=341400,
            body_key="VD",
            number="26_LEG_30",
            title="Fusion des communes de Nyon et Morges",
            type_name="Décret/Loi",
            documents=[Document("EMPD", "https://sieldocs.vd.ch/empd.pdf", texte=liste)],
        )
    )

    _passer(tmp_path, monde, horloge)

    assert _communes(tmp_path, "conseils/vd/objets/26_LEG_30.json") == [(NYON, "titre"), (MORGES, "titre")]


def test_les_conseils_communaux_et_les_seances_ne_sont_jamais_rattaches_par_le_nom(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(
        Affaire(
            id=340300,
            body_key="5586",
            number="INT26/102",
            title="Le tram jusqu'à Renens et Morges",
            begin_date="2026-10-13",
            documents=[Document("Texte", "https://lausanne.ch/int.pdf", texte="Renens, Morges, Nyon.")],
        )
    )
    monde.reunions.append(
        Reunion(
            id=1034600,
            body_key="VD",
            group_id=1965,
            name="Séance du Grand Conseil à Morges",
            begin_date="2026-10-13T00:00:00",
            points=[Point(1, "Le tram jusqu'à Renens")],
        )
    )

    _passer(tmp_path, monde, horloge)

    assert _communes(tmp_path, "conseils/5586/objets/INT26-102.json") == []
    fil = {e["cle"]: e["communes"] for e in _lire(tmp_path, "conseils/fil.json")["entrees"]}
    assert (fil["5586/INT26-102"], fil["vd/2026-10-13"]) == ([LAUSANNE], [])
    assert _lire(tmp_path, "conseils/index.json")["communes"] == {}
    assert "communes" not in _lire(tmp_path, "conseils/vd/seances/2026-10-13.json")


def test_un_ancien_nom_rattache_a_la_commune_actuelle_et_le_rattrapage_suit_une_fusion(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(Affaire(id=341500, body_key="VD", number="26_QUE_70", title="Le château de Curtilles"))
    _passer(tmp_path, monde, horloge, communes=COMMUNES)
    avant = _communes(tmp_path, "conseils/vd/objets/26_QUE_70.json")

    # Curtilles fusionne dans Lucens : `communes.json` est mis à jour, puis on relance le rattrapage (aucun import
    # réussi : tout l'historique est relu).
    lucens = next(c for c in COMMUNES if c["nom"] == "Lucens")
    apres_fusion = [c for c in COMMUNES if c["nom"] not in ("Curtilles", "Lucens")] + [
        {**lucens, "anciens": [*lucens["anciens"], {"nom": "Curtilles", "type": "Ancienne commune", "annee": 2027}]}
    ]
    (tmp_path / "conseils/import.json").unlink()
    horloge.heure = T0 + timedelta(days=80)
    _passer(tmp_path, monde, horloge, communes=apres_fusion)

    assert avant == [(OFS["Curtilles"], "titre")]
    assert _communes(tmp_path, "conseils/vd/objets/26_QUE_70.json") == [(OFS["Lucens"], "titre")]
    assert _lire(tmp_path, "conseils/index.json")["communes"] == {str(OFS["Lucens"]): 1}


def _corriger(depot, *corrections):
    (depot / "corrections.json").write_text(json.dumps(list(corrections), ensure_ascii=False), encoding="utf-8")


def test_corrections_json_l_emporte_sur_la_regle(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(_caves())
    _corriger(
        tmp_path,
        {"objet": "vd/26_INT_150", "retirer": [NYON], "ajouter": [LAUSANNE, MORGES], "note": "Nyon par erreur"},
    )

    _passer(tmp_path, monde, horloge)

    assert _communes(tmp_path) == [(BOURG_EN_LAVAUX, "titre"), (MORGES, "document"), (LAUSANNE, "correction")]
    assert str(NYON) not in _lire(tmp_path, "conseils/index.json")["communes"]


def test_une_correction_s_applique_a_l_import_suivant_sans_que_l_objet_change(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(_caves())
    _passer(tmp_path, monde, horloge)

    _corriger(tmp_path, {"objet": "vd/26_INT_150", "retirer": [MORGES], "ajouter": [LAUSANNE], "note": "À Lausanne"})
    horloge.heure = T0 + timedelta(days=1)
    _passer(tmp_path, monde, horloge)
    corrige = _communes(tmp_path)

    _corriger(tmp_path)
    horloge.heure = T0 + timedelta(days=2)
    _passer(tmp_path, monde, horloge)

    assert corrige == [(BOURG_EN_LAVAUX, "titre"), (NYON, "document"), (LAUSANNE, "correction")]
    # La correction retirée, son ajout disparaît ; la commune qu'elle retirait revient au prochain rattrapage.
    assert _communes(tmp_path) == [(BOURG_EN_LAVAUX, "titre"), (NYON, "document")]


def test_un_document_arrive_plus_tard_rattache_a_nouveau_son_objet(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(Affaire(id=341600, body_key="VD", number="26_INT_160", title="Les caves vaudoises"))
    _passer(tmp_path, monde, horloge)
    avant = _communes(tmp_path, "conseils/vd/objets/26_INT_160.json")

    horloge.heure = T0 + timedelta(days=1)
    monde.affaires[-1].documents.append(
        Document("Réponse", "https://sieldocs.vd.ch/r.pdf", texte="Les caves de Morges.", mis_a_jour="2026-10-17")
    )
    _passer(tmp_path, monde, horloge)

    assert avant == []
    objet = _lire(tmp_path, "conseils/vd/objets/26_INT_160.json")
    assert ([(c["ofs"], c["origine"]) for c in objet["communes"]], len(objet["documents"])) == (
        [(MORGES, "document")],
        1,
    )
    docs = monde.requetes_vers("docs")
    assert [r.url.params.get("from_updated_at") for r in docs] == ["2026-10-15"]
    assert {r.url.params["body_key"] for r in docs} == {"VD"}
