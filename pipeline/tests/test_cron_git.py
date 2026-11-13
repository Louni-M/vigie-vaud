"""La couche git du cron : `committer` et `pousser` contre un dépôt nu local qui tient lieu de GitHub
(`faux_depot`), le commit et le push de chaque phase du passage (`publier`), et le point d'entrée `main`. Ni réseau
ni DNS : le dépôt nu est un chemin."""

import json
from datetime import timedelta
from functools import partial

import httpx
import pytest
from faux_depot import crochet, git
from faux_openparldata import HorlogeFactice
from passage_sites import SOURCES as SOURCES_SITES
from passage_sites import T0 as T0_SITES
from passage_sites import _passer as _passer_avec_les_sites
from passage_sites import _preverenges
from test_cron import CONSEILS, JOUR, IssuesFactices, _monde_conseils

import cron
from cron import committer, main, passage, pousser, publier

MESSAGE = "Passage du cron du 2026-11-13 06:30Z : sondes"


def _passage_ecrit(clone, contenu="{}\n"):
    """Ce qu'un passage laisse dans le clone avant le commit : `etat-sources.json` et `schema/`. Rend le message de
    son commit."""
    (clone / "etat-sources.json").write_text(contenu, encoding="utf-8")
    (clone / "schema").mkdir(exist_ok=True)
    (clone / "schema" / "etat-sources.schema.json").write_text("{}\n", encoding="utf-8")
    return MESSAGE


def test_le_passage_committe_l_etat_et_le_schema_puis_pousse(depot_nu):
    clone = depot_nu.cloner("cron")
    message = _passage_ecrit(clone, '{"version": 1}\n')

    assert committer(clone, message)
    pousser(clone)

    assert depot_nu.journal() == ["Passage du cron du 2026-11-13 06:30Z : sondes", "Amorce"]
    assert depot_nu.fichier("etat-sources.json") == '{"version": 1}\n'
    assert depot_nu.fichier("schema/etat-sources.schema.json") == "{}\n"


def test_un_push_refuse_est_rattrape_par_pull_rebase(depot_nu, capsys):
    clone = depot_nu.cloner("cron")
    committer(clone, _passage_ecrit(clone))
    depot_nu.pousser_depuis(depot_nu.cloner("autre"), "conseils/import.json", "{}\n", "Rattrapage lancé à la main")

    pousser(clone)

    assert depot_nu.journal() == [MESSAGE, "Rattrapage lancé à la main", "Amorce"]
    assert depot_nu.fichier("conseils/import.json") == "{}\n"
    assert "Push refusé : pull --rebase puis nouvel essai (1/2)" in capsys.readouterr().err


def test_un_conflit_au_rebase_fait_echouer_le_passage_sans_laisser_de_rebase_en_cours(depot_nu):
    clone = depot_nu.cloner("cron")
    committer(clone, _passage_ecrit(clone, '{"passage": "cron"}\n'))
    depot_nu.pousser_depuis(depot_nu.cloner("autre"), "etat-sources.json", '{"passage": "autre"}\n', "Autre passage")

    with pytest.raises(SystemExit, match="Push refusé : le passage échoue"):
        pousser(clone)

    assert depot_nu.journal() == ["Autre passage", "Amorce"]
    assert not (clone / ".git" / "rebase-merge").exists()
    assert not (clone / ".git" / "rebase-apply").exists()


def test_un_depot_qui_refuse_tout_push_fait_echouer_le_passage_apres_deux_nouveaux_essais(depot_nu, capsys):
    clone = depot_nu.cloner("cron")
    committer(clone, _passage_ecrit(clone))
    depot_nu.refuser_les_push()

    with pytest.raises(SystemExit, match="Push refusé : le passage échoue"):
        pousser(clone)

    assert depot_nu.journal() == ["Amorce"]
    journal = capsys.readouterr().err
    assert "nouvel essai (1/2)" in journal
    assert "nouvel essai (2/2)" in journal


def _sources_vides(dossier):
    """Un `sources.json` sans source : le passage n'envoie aucune requête et n'écrit que l'état et le schéma."""
    chemin = dossier / "sources.json"
    chemin.write_text('{"sources": []}\n', encoding="utf-8")
    return chemin


def test_sans_push_le_point_d_entree_committe_le_passage_sans_le_pousser(depot_nu, tmp_path, capsys):
    clone = depot_nu.cloner("cron")

    main(["--depot", str(clone), "--sources", str(_sources_vides(tmp_path)), "--sans-push"])

    assert git(clone, "log", "--format=%s", "-1").startswith("Passage du cron du ")
    assert git(clone, "status", "--porcelain") == ""
    assert depot_nu.journal() == ["Amorce"]
    assert "Commit fait, sans push (--sans-push)." in capsys.readouterr().out


def test_le_point_d_entree_refuse_un_dossier_qui_n_est_pas_un_clone(tmp_path):
    with pytest.raises(SystemExit, match="n'est pas un clone git du dépôt de données"):
        main(["--depot", str(tmp_path), "--sources", str(_sources_vides(tmp_path)), "--sans-push"])


def test_un_appel_a_git_qui_depasse_son_delai_fait_echouer_le_passage_avec_un_message_clair(
    depot_nu, tmp_path, monkeypatch
):
    clone = depot_nu.cloner("cron")
    crochet(clone / ".git", "pre-commit", "sleep 10")
    monkeypatch.setattr(cron, "DELAI_GIT", 2)  # assez pour le `git add` qui précède, même sur une machine chargée

    with pytest.raises(SystemExit, match=r"^git commit : sans réponse après 2 s, le passage échoue"):
        main(["--depot", str(clone), "--sources", str(_sources_vides(tmp_path)), "--sans-push"])

    assert git(clone, "rev-list", "--count", "HEAD") == "1\n"


# --- Un commit et un push par phase (ticket #203) ------------------------------------------------------------------
# Le passage publie après chaque phase : les sondes, puis l'import des conseils d'OpenParlData, puis celui des sites
# des communes. Un dépassement du délai du job ne perd que la phase en cours.


def _passer_les_conseils(clone, monde, heure, interrompre_l_import=False):
    """Un passage du cron sur les deux conseils d'OpenParlData de `test_cron`, qui publie chaque phase dans le dépôt
    nu. Avec `interrompre_l_import`, la première requête de l'import lève `KeyboardInterrupt`, comme le job que
    GitHub arrête à son délai : rien après elle ne s'exécute."""
    monde.horloge.heure = heure

    def traiter(requete):
        if interrompre_l_import and "expand" in requete.url.params:
            raise KeyboardInterrupt
        return monde.transport().handle_request(requete)

    with httpx.Client(transport=httpx.MockTransport(traiter)) as client:
        passage(
            clone,
            CONSEILS,
            client,
            horloge=monde.horloge,
            issues=IssuesFactices(),
            attendre=monde.horloge.attendre,
            fin_de_phase=partial(publier, clone),
        )


def test_un_passage_interrompu_pendant_l_import_garde_ses_sondes_poussees(depot_nu):
    clone = depot_nu.cloner("cron")

    with pytest.raises(KeyboardInterrupt):
        _passer_les_conseils(clone, _monde_conseils(), JOUR, interrompre_l_import=True)

    assert depot_nu.journal() == ["Passage du cron du 2026-10-16 05:17Z : sondes", "Amorce"]
    etat = json.loads(depot_nu.fichier("etat-sources.json"))
    assert {i: e["etat"] for i, e in etat["sources"].items()} == {
        "openparldata-vd": "disponible",
        "openparldata-5586": "disponible",
    }
    assert depot_nu.fichier("schema/etat-sources.schema.json")


def test_un_second_passage_du_jour_sans_import_ne_committe_que_ses_sondes(depot_nu):
    clone = depot_nu.cloner("cron")
    monde = _monde_conseils()
    _passer_les_conseils(clone, monde, JOUR)
    import_du_jour = depot_nu.fichier("conseils/import.json")

    _passer_les_conseils(clone, monde, JOUR + timedelta(minutes=30))

    assert depot_nu.journal() == [
        "Passage du cron du 2026-10-16 05:47Z : sondes",
        "Passage du cron du 2026-10-16 05:17Z : conseils d'OpenParlData",
        "Passage du cron du 2026-10-16 05:17Z : sondes",
        "Amorce",
    ]
    assert depot_nu.fichier("conseils/import.json") == import_du_jour


def test_une_phase_sans_changement_ne_committe_rien(depot_nu):
    clone = depot_nu.cloner("cron")
    committer(clone, _passage_ecrit(clone))

    assert not committer(clone, "Passage du cron du 2026-11-13 06:30Z : conseils d'OpenParlData")

    assert git(clone, "log", "--format=%s") == f"{MESSAGE}\nAmorce\n"


def test_l_import_des_sites_des_communes_est_publie_apres_celui_d_openparldata(depot_nu):
    clone = depot_nu.cloner("cron")
    horloge = HorlogeFactice(T0_SITES)

    _passer_avec_les_sites(clone, horloge, _preverenges(horloge), SOURCES_SITES, fin_de_phase=partial(publier, clone))

    assert depot_nu.journal() == [
        "Passage du cron du 2026-10-23 05:17Z : sites des communes",
        "Passage du cron du 2026-10-23 05:17Z : conseils d'OpenParlData",
        "Passage du cron du 2026-10-23 05:17Z : sondes",
        "Amorce",
    ]
    assert git(clone, "status", "--porcelain") == ""
    assert "5643" in json.loads(depot_nu.fichier("conseils/import.json"))["conseils"]
