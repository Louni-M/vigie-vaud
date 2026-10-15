"""JSON Schema tiré des modèles et versionné dans `schema/`."""

import json

from schema import DOSSIER_SCHEMA, ecrire_schemas


def test_le_json_schema_versionne_est_a_jour(tmp_path):
    for chemin in ecrire_schemas(tmp_path):
        versionne = DOSSIER_SCHEMA / chemin.name
        assert versionne.exists(), f"{versionne.name} manque : lancer `pnpm --dir web schema`"
        assert versionne.read_text() == chemin.read_text(), f"{versionne.name} périmé : lancer `pnpm --dir web schema`"


def test_les_enumerations_sont_nommees_et_les_champs_sans_titre(tmp_path):
    ecrire_schemas(tmp_path)
    sources = json.loads((tmp_path / "sources.schema.json").read_text())

    assert {"VoieAcces", "SorteFraicheur", "ModeCouverture", "Source"} <= set(sources["$defs"])
    assert "title" not in sources["$defs"]["Source"]["properties"]["nom"]
    assert sources["$defs"]["Source"]["additionalProperties"] is False
