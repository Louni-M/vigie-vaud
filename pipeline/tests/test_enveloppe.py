"""Enveloppe `version` + `genere` des fichiers du dépôt de données."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from schema import Enveloppe


def test_genere_s_ecrit_en_iso_8601_utc_avec_z():
    enveloppe = Enveloppe(version=1, genere=datetime(2026, 10, 14, 12, 17, tzinfo=UTC))

    assert json.loads(enveloppe.model_dump_json()) == {"version": 1, "genere": "2026-10-14T12:17:00Z"}


def test_un_fichier_ecrit_se_relit_a_l_identique():
    texte = '{"version":1,"genere":"2026-10-14T12:17:00Z"}'

    assert Enveloppe.model_validate_json(texte).model_dump_json() == texte


@pytest.mark.parametrize(
    "donnees",
    [
        pytest.param({"version": 1, "genere": "2026-10-14T12:17:00"}, id="heure sans fuseau"),
        pytest.param(
            {"version": 1, "genere": datetime(2026, 10, 14, 14, 17, tzinfo=timezone(timedelta(hours=2)))},
            id="heure hors UTC",
        ),
        pytest.param({"version": 0, "genere": "2026-10-14T12:17:00Z"}, id="version nulle"),
        pytest.param({"version": "v1", "genere": "2026-10-14T12:17:00Z"}, id="version préfixée"),
        pytest.param({"genere": "2026-10-14T12:17:00Z"}, id="sans version"),
    ],
)
def test_une_enveloppe_invalide_est_refusee(donnees):
    with pytest.raises(ValidationError):
        Enveloppe.model_validate(donnees)
