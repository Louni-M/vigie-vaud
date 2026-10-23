"""Les retraits (#141 ; ADR 0007) : les corrections par élément de `retraits.json`, réappliquées après le masquage à
chaque import et à chaque rattrapage, pour tous les conseils. Contre un dossier temporaire qui tient lieu de clone du
dépôt de données, avec le faux OpenParlData et l'horloge factice de `test_import_conseils`.
"""

import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from faux_openparldata import HorlogeFactice
from retraits import appliquer_retraits, lire_retraits
from test_import_conseils import T0, _lire, _monde, _passer

COVID = "conseils/vd/objets/26_INT_140.json"
SEANCE_LAUSANNE = "conseils/5586/seances/2026-10-06.json"


def _retirer(depot, *retraits):
    (depot / "retraits.json").write_text(json.dumps(list(retraits), ensure_ascii=False), encoding="utf-8")


def test_un_objet_relu_avec_son_titre_d_origine_garde_le_texte_corrige(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _passer(tmp_path, monde, horloge)
    _retirer(tmp_path, {"element": "vd/26_INT_140", "cible": "titre", "texte": "Covid 2020", "date": "2026-10-16"})

    horloge.heure = T0 + timedelta(days=1)
    _passer(tmp_path, monde, horloge)  # le retrait vaut dès le passage suivant, sans que l'Objet change
    assert _lire(tmp_path, COVID)["titre"] == "Covid 2020"

    horloge.heure = T0 + timedelta(days=2)
    relu = next(a for a in monde.affaires if a.number == "26_INT_140")
    relu.state_name, relu.updated_at = "Répondu", "2026-10-18"  # relu avec son titre d'origine
    _passer(tmp_path, monde, horloge)

    objet = _lire(tmp_path, COVID)
    assert objet["titre"] == "Covid 2020"
    assert objet["statut"]["libelle"] == "Répondu"
    assert "six ans" not in (tmp_path / "conseils/vd/objets-2026.json").read_text(encoding="utf-8")


def test_le_point_d_une_seance_et_le_titre_d_un_document_se_corrigent(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _retirer(
        tmp_path,
        {"element": "5586/2026-10-06", "cible": "point:1", "texte": "Postulat", "date": "2026-10-16"},
        {
            "element": "vd/26_INT_140",
            "cible": "document:https://www.vd.ch/fileadmin/26_INT_140.pdf",
            "texte": "Texte déposé",
            "date": "2026-10-16",
        },
    )

    _passer(tmp_path, monde, horloge)

    assert _lire(tmp_path, SEANCE_LAUSANNE)["ordre_du_jour"][0]["titre"] == "Postulat"
    assert _lire(tmp_path, COVID)["documents"][0]["titre"] == "Texte déposé"


def test_un_retrait_sans_cible_est_signale_sans_faire_echouer_l_import(tmp_path, capsys):
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    _retirer(
        tmp_path,
        {"element": "5586/2026-10-06", "cible": "point:9", "texte": "Point", "date": "2026-10-16"},
        {"element": "vd/99_INT_1", "cible": "titre", "texte": "Pas encore importé", "date": "2026-10-16"},
    )

    _passer(tmp_path, monde, horloge)

    assert "Retrait sans effet : 5586/2026-10-06" in capsys.readouterr().err
    assert _lire(tmp_path, COVID)["titre"].startswith("Covid 2020 six ans")


def test_un_retraits_json_invalide_fait_echouer_avant_tout_import(tmp_path):
    _retirer(tmp_path, {"element": "vd/26_INT_140", "cible": "contributeurs", "texte": "x", "date": "2026-10-16"})
    with pytest.raises(ValidationError):
        lire_retraits(tmp_path)


def test_sans_retraits_json_rien_ne_change(tmp_path):
    assert lire_retraits(tmp_path) == {}
    assert appliquer_retraits({}, {}) == {}
