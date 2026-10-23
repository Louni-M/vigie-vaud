"""L'archive des conseils prête pour les Objets scrapés (#146, spec de J3, « Schéma commun » et « Import des
sites ») : des Objets sans identifiant.

Les Séances scrapées (`id` nul, documents, deux Séances d'un même jour) passent par le passage du cron sur
l'échantillon i-web (`test_sites_communaux.py`), comme les Objets scrapés (`test_sites_preavis_objets.py`). Ici,
les Objets sans identifiant passent par le passage de l'import de J1, servis par le faux OpenParlData, qui sert un
`id` nul comme le module de lecture d'une plateforme : un Objet relu remplace celui de l'archive, ce que l'échantillon
ne montre pas en un passage. Le conseil de test est celui d'une commune inventée (n° 5624).
"""

from datetime import timedelta

from faux_openparldata import Affaire, HorlogeFactice, Monde, Point, Reunion
from schema import FichierSources
from test_import_conseils import T0, _lire, _passer, _source

SOURCES = FichierSources.model_validate({"sources": [_source("5624", donne=["objets", "seances"])]})


def _seance(id=1, begin_date="2026-10-06T20:00:00", **champs):
    return Reunion(id=id, body_key="5624", name="Séance du Conseil communal", begin_date=begin_date, **champs)


def _preavis(titre="Préavis 12/2026 - Crédit pour la piscine", updated_at="2026-10-07"):
    return Affaire(
        id=None, body_key="5624", number="12/2026", title=titre, type_name="Préavis", updated_at=updated_at
    )


def test_un_objet_brut_sans_identifiant_est_archive_avec_un_identifiant_nul(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = Monde(
        horloge=horloge,
        affaires=[_preavis()],
        reunions=[_seance(id=None, points=[Point(1, "Préavis 12/2026 - Crédit", "12/2026")])],
    )

    _passer(tmp_path, monde, horloge, SOURCES)

    objet = _lire(tmp_path, "conseils/5624/objets/12-2026.json")
    assert (objet["id"], objet["numero"], objet["titre"]) == (None, "12/2026", "Préavis 12/2026 - Crédit pour la piscine")
    seance = _lire(tmp_path, "conseils/5624/seances/2026-10-06.json")
    assert seance["id"] is None
    assert seance["ordre_du_jour"][0]["objet"] == "5624/12-2026"


def test_un_objet_sans_identifiant_relu_remplace_celui_de_l_archive(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = Monde(horloge=horloge, affaires=[_preavis()])
    _passer(tmp_path, monde, horloge, SOURCES)

    horloge.heure = T0 + timedelta(days=1)
    monde.affaires = [_preavis("Préavis 12/2026 - Crédit pour la piscine couverte", updated_at="2026-10-17")]
    _passer(tmp_path, monde, horloge, SOURCES)

    assert _lire(tmp_path, "conseils/5624/objets/12-2026.json")["titre"] == (
        "Préavis 12/2026 - Crédit pour la piscine couverte"
    )
