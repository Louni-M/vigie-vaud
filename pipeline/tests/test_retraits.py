"""Les retraits (#141 ; ADR 0007) : les corrections par élément de `retraits.json`, réappliquées après le masquage à
chaque import et à chaque rattrapage, pour tous les conseils. Contre un dossier temporaire qui tient lieu de clone du
dépôt de données, avec le faux OpenParlData et l'horloge factice de `test_import_conseils`.
"""

import hashlib
import hmac
import io
import json
from dataclasses import replace
from datetime import timedelta

import pytest
from pydantic import ValidationError

from faux_openparldata import Affaire, Contributeur, HorlogeFactice, Point
from retraits import appliquer_retraits, constat_des_retraits, lire_retraits
from retraits import main as retraits_main
from test_import_conseils import T0, _lire, _monde, _passer

COVID = "conseils/vd/objets/26_INT_140.json"
SEANCE_LAUSANNE = "conseils/5586/seances/2026-10-06.json"

# La clé des empreintes du dépôt de données (`RETRAITS_CLE`), une clé de test.
CLE = "cle-de-test-des-retraits-0123456789abcdef0123456789abcdef"
# Un nom que le masquage ne voit pas (ni civilité ni mot déclencheur) : il faut un retrait.
TITRE_NOMME = "Préavis 7/2026 - Vente de la parcelle 412 à Jeanne Rochat"
TEXTE_CORRIGE = "Préavis 7/2026 - Vente de la parcelle 412 à [particulier]"


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


def _monde_avec_vente(horloge):
    """Le monde de base, où la Séance de Lausanne du 6 octobre a un deuxième point qui nomme un particulier."""
    monde = _monde(horloge)
    lausanne = next(r for r in monde.reunions if r.id == 33001)
    lausanne.points.append(Point(2, TITRE_NOMME))
    return monde, lausanne


def _titres(depot):
    return [p["titre"] for p in _lire(depot, SEANCE_LAUSANNE)["ordre_du_jour"]]


def _empreinte(depot, element, cible, capsys):
    """L'empreinte que donne la commande de la procédure de retrait, lue dans le clone du dépôt de données."""
    capsys.readouterr()
    retraits_main(["--depot", str(depot), element, cible])
    return capsys.readouterr().out.strip()


def test_un_point_insere_avant_le_point_vise_ne_deplace_pas_la_correction(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde, lausanne = _monde_avec_vente(horloge)
    _passer(tmp_path, monde, horloge)
    assert _titres(tmp_path) == ["Postulat - Préaux ouverts", TITRE_NOMME]

    empreinte = _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys)
    _retirer(
        tmp_path,
        {
            "element": "5586/2026-10-06",
            "cible": "point:2",
            "empreinte": empreinte,
            "texte": TEXTE_CORRIGE,
            "date": "2026-10-16",
        },
    )
    horloge.heure = T0 + timedelta(days=1)
    _passer(tmp_path, monde, horloge)  # la Séance n'est pas relue : le retrait vaut sur l'archive
    assert _titres(tmp_path) == ["Postulat - Préaux ouverts", TEXTE_CORRIGE]

    # La source insère un point en tête : le point nommé passe au rang 3, et la Séance est relue.
    postulat, vente = lausanne.points
    lausanne.points = [Point(1, "Appel"), replace(postulat, numero=2), replace(vente, numero=3)]
    lausanne.updated_at = "2026-10-17"
    horloge.heure = T0 + timedelta(days=2)
    _passer(tmp_path, monde, horloge)
    assert _titres(tmp_path) == ["Appel", "Postulat - Préaux ouverts", TEXTE_CORRIGE]

    # Les passages suivants, Séance relue ou non, gardent la correction, sans la dire sans effet.
    capsys.readouterr()
    for jours in (3, 4):
        horloge.heure = T0 + timedelta(days=jours)
        _passer(tmp_path, monde, horloge)
        assert _titres(tmp_path) == ["Appel", "Postulat - Préaux ouverts", TEXTE_CORRIGE]
    assert "sans effet" not in capsys.readouterr().err
    assert not [f for f in tmp_path.rglob("*.json") if "Rochat" in f.read_text(encoding="utf-8")]

    # Sans la clé, la Séance non relue garde sa correction déplacée : le rang n'écrase pas le point 2.
    monkeypatch.delenv("RETRAITS_CLE")
    horloge.heure = T0 + timedelta(days=5)
    _passer(tmp_path, monde, horloge)
    assert _titres(tmp_path) == ["Appel", "Postulat - Préaux ouverts", TEXTE_CORRIGE]


def test_un_titre_change_par_la_source_rend_le_retrait_sans_effet(tmp_path, monkeypatch, capsys):
    """L'empreinte ne correspond plus à aucun point : le nom revient, et le retrait est signalé (issue du cron)."""
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde, lausanne = _monde_avec_vente(horloge)
    _passer(tmp_path, monde, horloge)
    retrait = {
        "element": "5586/2026-10-06",
        "cible": "point:2",
        "empreinte": _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys),
        "texte": TEXTE_CORRIGE,
        "date": "2026-10-16",
    }
    _retirer(tmp_path, retrait)
    horloge.heure = T0 + timedelta(days=1)
    _passer(tmp_path, monde, horloge)

    lausanne.points[1].titre = f"{TITRE_NOMME} (rectifié)"
    lausanne.updated_at = "2026-10-17"
    horloge.heure = T0 + timedelta(days=2)
    capsys.readouterr()
    _passer(tmp_path, monde, horloge)

    assert _titres(tmp_path) == ["Postulat - Préaux ouverts", f"{TITRE_NOMME} (rectifié)"]
    assert "Retrait sans effet : 5586/2026-10-06, cible « point:2 » introuvable" in capsys.readouterr().err
    constat = constat_des_retraits(tmp_path, CLE.encode())
    assert [(r.element, r.cible) for r in constat.sans_effet] == [("5586/2026-10-06", "point:2")]
    assert constat.non_verifies == []


def test_on_ne_retrouve_pas_le_nom_retire_en_essayant_des_noms_sans_la_cle(tmp_path, monkeypatch, capsys):
    """Ce que voit le public : `retraits.json` (le texte corrigé, l'empreinte) et le site. Il remet chaque nom d'un
    dictionnaire à la place de « [particulier] » et compare l'empreinte : sans la clé, rien ne correspond."""
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde, _ = _monde_avec_vente(horloge)
    _passer(tmp_path, monde, horloge)
    publique = _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys)

    noms = ["Jean Dupont", "Marie Martin", "Jeanne Rochat", "Pierre Favre", "Anne Rochat", "Jeanne"]
    candidats = [TEXTE_CORRIGE.replace("[particulier]", nom) for nom in noms]
    cles_essayees = [b"", b"vigie-vaud", b"retraits", b"RETRAITS_CLE", b"vigie-vaud-donnees"]

    def condensats(titre):
        octets = titre.encode("utf-8")
        yield hashlib.sha256(octets).hexdigest()
        yield hashlib.sha3_256(octets).hexdigest()
        yield from (hmac.new(c, octets, hashlib.sha256).hexdigest() for c in cles_essayees)

    assert not [t for t in candidats for c in condensats(t) if c == publique]
    # Avec la clé, le même essai trouve le nom : tout repose sur le secret.
    vrais = [t for t in candidats if hmac.new(CLE.encode(), t.encode(), hashlib.sha256).hexdigest() == publique]
    assert vrais == [TITRE_NOMME]


def test_l_empreinte_se_calcule_aussi_d_un_titre_colle_et_jamais_sans_la_cle(tmp_path, monkeypatch, capsys):
    """Pour un retrait dont le point est déjà corrigé dans l'archive : le titre d'origine vient de la source."""
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde, _ = _monde_avec_vente(horloge)
    _passer(tmp_path, monde, horloge)
    du_depot = _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys)

    assert _empreinte_collee(tmp_path, "5586/2026-10-06", f"  {TITRE_NOMME}\n", monkeypatch, capsys) == du_depot

    monkeypatch.delenv("RETRAITS_CLE")
    with pytest.raises(SystemExit, match="RETRAITS_CLE absente"):
        retraits_main(["--depot", str(tmp_path), "5586/2026-10-06", "point:2"])


def _empreinte_collee(depot, element, titre, monkeypatch, capsys):
    """L'empreinte que donne la commande de la procédure de retrait pour un titre de la source collé."""
    capsys.readouterr()
    monkeypatch.setattr("sys.stdin", io.StringIO(titre))
    retraits_main(["--depot", str(depot), "--stdin", element])
    return capsys.readouterr().out.strip()


def test_un_titre_colle_est_masque_comme_l_import_avant_son_empreinte(tmp_path, monkeypatch, capsys):
    """L'archive garde le titre masqué, et l'empreinte du retrait porte sur lui (ADR 0007) : le titre de la source,
    collé tel quel, est masqué comme à l'import avant d'être haché."""
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    lausanne = next(r for r in monde.reunions if r.id == 33001)
    source = "Préavis 7/2026 - Succession de Paul Exemple, parcelle 412 à Jeanne Rochat"
    lausanne.points.append(Point(2, source))
    _passer(tmp_path, monde, horloge)
    assert _titres(tmp_path)[1] == "Préavis 7/2026 - Succession de [particulier], parcelle 412 à Jeanne Rochat"

    archivee = _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys)
    assert _empreinte_collee(tmp_path, "5586/2026-10-06", source, monkeypatch, capsys) == archivee


def test_un_titre_colle_epargne_les_elus_connus_du_conseil_comme_l_import(tmp_path, monkeypatch, capsys):
    """Le masquage de l'import épargne les élu·e·s connu·e·s du conseil : celui du titre collé aussi, lu·e·s dans le
    clone (contributeur·rice·s de ses Objets, `membres.json`)."""
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    horloge = HorlogeFactice(T0)
    monde = _monde(horloge)
    monde.affaires.append(
        Affaire(
            id=340950,
            body_key="5586",
            number="INT25/020",
            title="Interpellation sur les préaux",
            type_name="Interpellation",
            contributeurs=[Contributeur("Léa Conseillère", "PS", "Auteur")],
        )
    )
    lausanne = next(r for r in monde.reunions if r.id == 33001)
    source = "Préavis 7/2026 - Vente à M. Paul Exemple, rapport de Mme Léa Conseillère"
    lausanne.points.append(Point(2, source))
    _passer(tmp_path, monde, horloge)
    assert _titres(tmp_path)[1] == "Préavis 7/2026 - Vente à [particulier], rapport de Mme Léa Conseillère"

    archivee = _empreinte(tmp_path, "5586/2026-10-06", "point:2", capsys)
    assert _empreinte_collee(tmp_path, "5586/2026-10-06", source, monkeypatch, capsys) == archivee


def test_un_titre_colle_sans_le_clone_ni_la_seance_est_refuse(tmp_path, monkeypatch):
    # Sans le conseil, le titre ne se masque pas comme l'import : une empreinte fausse, que rien ne signalerait.
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    monkeypatch.setattr("sys.stdin", io.StringIO(TITRE_NOMME))
    with pytest.raises(SystemExit):
        retraits_main(["--stdin"])
    with pytest.raises(SystemExit, match="Aucune Séance 5586/2026-10-06"):
        retraits_main(["--depot", str(tmp_path), "--stdin", "5586/2026-10-06"])


def test_sans_la_cle_un_retrait_a_empreinte_corrige_le_point_de_son_rang_et_le_dit(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("RETRAITS_CLE", raising=False)
    horloge = HorlogeFactice(T0)
    monde, _ = _monde_avec_vente(horloge)
    _retirer(
        tmp_path,
        {
            "element": "5586/2026-10-06",
            "cible": "point:2",
            "empreinte": "0" * 64,
            "texte": TEXTE_CORRIGE,
            "date": "2026-10-16",
        },
    )

    _passer(tmp_path, monde, horloge)

    assert _titres(tmp_path) == ["Postulat - Préaux ouverts", TEXTE_CORRIGE]
    attendu = "Retrait non vérifié : 5586/2026-10-06, « point:2 » corrigé au rang, RETRAITS_CLE absente"
    assert attendu in capsys.readouterr().err


def test_une_cle_trop_courte_fait_echouer_l_import_avant_tout_import(tmp_path, monkeypatch):
    monkeypatch.setenv("RETRAITS_CLE", "secret")
    horloge = HorlogeFactice(T0)
    with pytest.raises(ValueError, match="RETRAITS_CLE trop courte"):
        _passer(tmp_path, _monde(horloge), horloge)
    assert not (tmp_path / "conseils").exists()


def test_une_empreinte_ne_vise_qu_un_point(tmp_path):
    _retirer(
        tmp_path,
        {"element": "vd/26_INT_140", "cible": "titre", "empreinte": "0" * 64, "texte": "x", "date": "2026-10-16"},
    )
    with pytest.raises(ValidationError, match="empreinte"):
        lire_retraits(tmp_path)
