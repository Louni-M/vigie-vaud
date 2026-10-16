"""Le rattachement par le nom mesuré sur un jeu annoté réel (`jeu-annote-rattachement.json`, voir sa
description) : la précision par origine doit rester d'au moins 95 % pour les titres comme pour les documents. Le
rappel est affiché sans faire échouer. `corrections.json` n'entre pas dans la mesure : seule la règle est mesurée.

Si une modification des contextes exclus fait passer la précision des documents sous le seuil, on revient sur le
seuil plutôt que d'empiler les exclusions (spec de J1, « Décisions de test »).
"""

import json
from pathlib import Path

import pytest

from rattachement import rattacher

JEU = json.loads((Path(__file__).parent / "jeu-annote-rattachement.json").read_text(encoding="utf-8"))
SEUIL = 0.95


def _mesure(origine):
    justes = trouvees = attendues = 0
    fausses, manquees = [], []
    for cas in JEU["cas"]:
        if cas["origine"] != origine:
            continue
        trouve = {c.ofs for c in rattacher(cas["texte"], origine)}
        attendu = set(cas["attendu"])
        justes += len(trouve & attendu)
        trouvees += len(trouve)
        attendues += len(attendu)
        fausses += [(cas["numero"], ofs) for ofs in sorted(trouve - attendu)]
        manquees += [(cas["numero"], ofs) for ofs in sorted(attendu - trouve)]
    return justes / trouvees, justes / attendues, fausses, manquees


@pytest.mark.parametrize("origine", ["titre", "document"])
def test_la_precision_du_rattachement_reste_d_au_moins_95_pour_cent_par_origine(origine, capsys):
    precision, rappel, fausses, manquees = _mesure(origine)

    with capsys.disabled():
        print(
            f"\nRattachement ({origine}) : précision {precision:.1%}, rappel {rappel:.1%} ; "
            f"{len(fausses)} fausse(s) {fausses}, {len(manquees)} manquée(s) {manquees}"
        )
    assert precision >= SEUIL, f"précision {precision:.1%} sous {SEUIL:.0%} : {fausses}"


def test_le_jeu_annote_a_la_taille_prevue_par_la_spec():
    origines = [cas["origine"] for cas in JEU["cas"]]
    assert (origines.count("titre"), origines.count("document")) == (133, 100)
    assert sum(1 for cas in JEU["cas"] if cas["origine"] == "titre" and not cas["attendu"]) >= 50
