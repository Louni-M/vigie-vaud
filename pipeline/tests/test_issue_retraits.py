"""L'issue `retrait-sans-effet` du dépôt de données (#199 ; ADR 0007) : un retrait qui ne trouve plus sa cible est
signalé dans une issue qui ne donne que la clé de l'élément et la cible, jamais un texte. Contre le GitHub factice
et les passages de `test_cron`.
"""

import copy
import json
from datetime import timedelta

from test_cron import (
    JOUR,
    VEILLE,
    GitHubFactice,
    IssuesFactices,
    _monde_conseils,
    _passer_conseils,
    _passer_conseils_avec_github,
)

from cron import IssuesAffichees

CLE = "cle-de-test-des-retraits-0123456789abcdef0123456789abcdef"
LIEN = "https://www.lausanne.ch/pos25-115-jeanne-rochat.pdf"
TEXTE = "Postulat de [particulier]"


def _retirer(depot, *retraits):
    (depot / "retraits.json").write_text(json.dumps(list(retraits), ensure_ascii=False), encoding="utf-8")


def _retrait(element, cible, **autres):
    return {"element": element, "cible": cible, "texte": TEXTE, "date": "2026-10-15"} | autres


def test_un_retrait_sans_effet_ouvre_une_issue_completee_puis_fermee_sans_aucun_texte(tmp_path, monkeypatch):
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    monde, github = _monde_conseils(), GitHubFactice()
    _passer_conseils_avec_github(tmp_path, monde, github, [VEILLE])
    assert github.issues == []  # sans `retraits.json`, aucune issue

    # L'Objet n'a aucun document : le retrait est sans effet. Un élément pas encore importé attend son import.
    _retirer(tmp_path, _retrait("5586/POS25-115", f"document:{LIEN}"), _retrait("vd/99_INT_1", "titre"))
    _passer_conseils_avec_github(tmp_path, monde, github, [VEILLE + timedelta(minutes=30)])
    (ouverte,) = copy.deepcopy(github.issues)

    # Un second retrait sans effet complète l'issue ; un passage sans changement n'y ajoute rien.
    _retirer(
        tmp_path,
        _retrait("5586/POS25-115", f"document:{LIEN}"),
        _retrait("vd/26_INT_140", "document:https://www.vd.ch/26_INT_140.pdf"),
    )
    _passer_conseils_avec_github(tmp_path, monde, github, [VEILLE + timedelta(minutes=60), JOUR])
    (completee,) = copy.deepcopy(github.issues)

    # Les deux retraits corrigés : l'issue se ferme.
    _retirer(tmp_path, _retrait("5586/POS25-115", "titre"), _retrait("vd/26_INT_140", "titre"))
    _passer_conseils_avec_github(tmp_path, monde, github, [JOUR + timedelta(minutes=30)])

    assert ouverte["title"] == "Retraits sans effet"
    assert [e["name"] for e in ouverte["labels"]] == ["retrait-sans-effet"]
    assert "`5586/POS25-115` : `document`" in ouverte["body"]
    assert "99_INT_1" not in ouverte["body"]
    assert "`vd/26_INT_140` : `document`" in completee["body"]
    assert completee["commentaires"] == [
        "Retraits sans effet : `5586/POS25-115` : `document`, `vd/26_INT_140` : `document`."
    ]
    (issue,) = github.issues
    assert issue["state"] == "closed"
    assert issue["commentaires"][1:] == ["Chaque retrait de `retraits.json` a de nouveau effet."]
    # Ni le texte corrigé, ni le lien (qui peut porter le nom), ni le nom.
    tout = json.dumps(github.issues, ensure_ascii=False)
    assert TEXTE not in tout
    assert "lausanne.ch" not in tout
    assert "Rochat" not in tout


def test_sans_la_cle_l_issue_dit_que_les_retraits_a_empreinte_ne_sont_pas_verifies(tmp_path, monkeypatch):
    monkeypatch.setenv("RETRAITS_CLE", "")  # un secret non défini arrive vide dans le workflow
    monde, github = _monde_conseils(), GitHubFactice()
    _retirer(tmp_path, _retrait("5586/2026-10-06", "point:2", empreinte="0" * 64))

    _passer_conseils_avec_github(tmp_path, monde, github, [VEILLE])

    (issue,) = github.issues
    assert issue["title"] == "Retraits sans effet"
    assert "`RETRAITS_CLE` absente : 1 retrait à empreinte" in issue["body"]


def test_sans_push_le_passage_affiche_les_retraits_sans_effet(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    _retirer(tmp_path, _retrait("5586/POS25-115", f"document:{LIEN}"))

    _passer_conseils(tmp_path, _monde_conseils(), VEILLE, IssuesAffichees())

    assert "Retraits sans effet : `5586/POS25-115` : `document`." in capsys.readouterr().out


def test_un_passage_avec_retraits_les_signale_au_client_d_issues(tmp_path, monkeypatch):
    monkeypatch.setenv("RETRAITS_CLE", CLE)
    _retirer(tmp_path, _retrait("5586/POS25-115", f"document:{LIEN}"))
    issues = IssuesFactices()

    _passer_conseils(tmp_path, _monde_conseils(), VEILLE, issues)

    assert ("retraits_sans_effet", ["5586/POS25-115"], 0) in issues.signalements
