"""L'archive des conseils prête pour les éléments scrapés (#146, spec de J3, « Schéma commun » et « Import des
sites ») : des Séances avec leurs documents, deux Séances d'un même jour, des enregistrements sans identifiant.

En attendant `lire_site` (#149), les enregistrements bruts passent par le passage de l'import de J1, servis par le
faux OpenParlData, qui ne filtre pas les champs : il sert les `docs` d'une Séance et un `id` nul comme le fera le
module de lecture d'une plateforme. Le conseil de test est celui d'une commune inventée pour ces cas (n° 5624).
"""

from faux_openparldata import Affaire, Document, HorlogeFactice, Monde, Point, Reunion
from schema import FichierSources
from test_import_conseils import T0, _lire, _passer, _source

SOURCES = FichierSources.model_validate({"sources": [_source("5624", donne=["objets", "seances"])]})


def _seance(id=1, begin_date="2026-10-06T20:00:00", **champs):
    return Reunion(id=id, body_key="5624", name="Séance du Conseil communal", begin_date=begin_date, **champs)


def test_les_documents_d_une_seance_sont_archives_titres_masques(tmp_path):
    horloge = HorlogeFactice(T0)
    monde = Monde(
        horloge=horloge,
        reunions=[
            _seance(
                documents=[
                    Document("Ordre du jour", "https://www.bussigny.ch/odj-2026-10-06.pdf", "2026-09-25"),
                    Document("Préavis 12/2026 - Succession de M. Paul Exemple", "https://www.bussigny.ch/p12.pdf"),
                ]
            )
        ],
    )

    _passer(tmp_path, monde, horloge, SOURCES)

    assert _lire(tmp_path, "conseils/5624/seances/2026-10-06.json")["documents"] == [
        {"titre": "Ordre du jour", "date": "2026-09-25", "lien": "https://www.bussigny.ch/odj-2026-10-06.pdf"},
        {"titre": "Préavis 12/2026 - Succession de [particulier]", "date": None, "lien": "https://www.bussigny.ch/p12.pdf"},
    ]


def test_deux_seances_du_meme_jour_n_en_font_qu_une_avec_tous_les_points_et_documents(tmp_path):
    horloge = HorlogeFactice(T0)
    odj = Document("Ordre du jour", "https://www.bussigny.ch/odj.pdf")
    monde = Monde(
        horloge=horloge,
        reunions=[
            # La Séance de 20 h 30 est lue avant celle de 18 h : c'est l'heure qui fait la première.
            _seance(
                id=1,
                begin_date="2026-10-06T20:30:00",
                points=[Point(1, "Préavis 13/2026 - Budget")],
                documents=[odj, Document("Procès-verbal", "https://www.bussigny.ch/pv-2.pdf")],
            ),
            Reunion(
                id=2,
                body_key="5624",
                name="Séance extraordinaire",
                begin_date="2026-10-06T18:00:00",
                points=[Point(1, "Assermentation"), Point(2, "Préavis 12/2026 - Crédit")],
                documents=[odj],
            ),
        ],
    )

    _passer(tmp_path, monde, horloge, SOURCES)

    seance = _lire(tmp_path, "conseils/5624/seances/2026-10-06.json")
    assert (seance["id"], seance["date"], seance["nom"]) == (2, "2026-10-06T18:00", "Séance extraordinaire")
    assert [p["titre"] for p in seance["ordre_du_jour"]] == [
        "Assermentation",
        "Préavis 12/2026 - Crédit",
        "Préavis 13/2026 - Budget",
    ]
    assert [d["lien"] for d in seance["documents"]] == [
        "https://www.bussigny.ch/odj.pdf",
        "https://www.bussigny.ch/pv-2.pdf",
    ]
    assert _lire(tmp_path, "conseils/5624/seances.json")["seances"] == [
        {"cle": "5624/2026-10-06", "date": "2026-10-06T18:00", "points": 3}
    ]
