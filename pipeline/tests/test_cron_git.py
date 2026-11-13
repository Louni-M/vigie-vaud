"""La couche git du cron : `committer` et `pousser` contre un dépôt nu local qui tient lieu de GitHub
(`faux_depot`), et le point d'entrée `main`. Ni réseau ni DNS : le dépôt nu est un chemin."""

from datetime import UTC, datetime

import pytest

import cron
from cron import committer, main, pousser
from faux_depot import crochet, git
from schema import EtatSources

T0 = datetime(2026, 11, 13, 6, 30, tzinfo=UTC)


def _passage_ecrit(clone, contenu="{}\n"):
    """Ce qu'un passage laisse dans le clone avant le commit : `etat-sources.json` et `schema/`."""
    (clone / "etat-sources.json").write_text(contenu, encoding="utf-8")
    (clone / "schema").mkdir(exist_ok=True)
    (clone / "schema" / "etat-sources.schema.json").write_text("{}\n", encoding="utf-8")
    return EtatSources(version=1, genere=T0, sources={})


def test_le_passage_committe_l_etat_et_le_schema_puis_pousse(depot_nu):
    clone = depot_nu.cloner("cron")
    etat = _passage_ecrit(clone, '{"version": 1}\n')

    committer(clone, etat)
    pousser(clone)

    assert depot_nu.journal() == ["Passage du cron du 2026-11-13 06:30Z", "Amorce"]
    assert depot_nu.fichier("etat-sources.json") == '{"version": 1}\n'
    assert depot_nu.fichier("schema/etat-sources.schema.json") == "{}\n"


def test_un_push_refuse_est_rattrape_par_pull_rebase(depot_nu, capsys):
    clone = depot_nu.cloner("cron")
    committer(clone, _passage_ecrit(clone))
    depot_nu.pousser_depuis(depot_nu.cloner("autre"), "conseils/import.json", "{}\n", "Rattrapage lancé à la main")

    pousser(clone)

    assert depot_nu.journal() == ["Passage du cron du 2026-11-13 06:30Z", "Rattrapage lancé à la main", "Amorce"]
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
