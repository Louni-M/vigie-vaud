"""Les sites communaux dans le passage du cron (spec de J3, « Import des sites ») : une commune i-web en séances
seules, déclarée dans un `sources.json` de test, lue par le robot communal sur l'échantillon enregistré
(`echantillon-sites/i-web/`), archivée et listée comme un conseil d'OpenParlData.

C'est le seul seam du cron : le passage reçoit un seul transport, qui sert à la fois le faux OpenParlData de J1 et
les pages de l'échantillon (`faux_sites.Reseau`), une résolution d'adresse factice pour le /24 du robot, et une
horloge que l'attente fait avancer. On observe les fichiers écrits, le journal du passage et les requêtes reçues par
les sites (URL, User-Agent, heure). Les cas instables sont fabriqués par de petites retouches de l'échantillon.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from cron import passage
from faux_openparldata import Affaire, HorlogeFactice, Monde
from faux_sites import Page, Reseau, echantillon
from schema import FichierSources
from test_cron import IssuesFactices

# 07:17 à Lausanne, le jour où l'échantillon a été enregistré : la fenêtre du passage part du 23 avril 2026.
T0 = datetime(2026, 10, 23, 5, 17, tzinfo=UTC)
PREVERENGES = "https://www.preverenges.ch"
IP_PREVERENGES = "195.65.10.20"

PLATEFORMES = [
    {
        "id": "i-web",
        "nom": "i-web",
        "editeur": "Innovative Web AG",
        "variantes": [{"id": "seances", "marqueur": "icmsTablePastSitzungen", "niveaux": [["seances"]]}],
    }
]


def _site(ofs, commune, seances, lien_conseil):
    return {
        "id": f"site-{ofs}",
        "nom": f"Conseil communal de {commune} (site de la commune)",
        "nom_court": f"Site de {commune}",
        "attribution": {
            "texte": f"Commune de {commune}",
            "lien": lien_conseil,
            "licence": "Actes officiels (art. 5 LDA) : métadonnées et liens seulement",
        },
        "voie_acces": "cron",
        "fraicheur": "import",
        "couverture": {"communes": [ofs], "mode": "scrape"},
        "conseil": {"body_key": str(ofs), "donne": ["seances"]},
        "site": {"plateforme": "i-web", "variante": "seances", "seances": seances},
    }


def _opendata(body_key):
    return {
        "id": f"openparldata-{body_key.lower()}",
        "nom": f"Conseil {body_key} (OpenParlData)",
        "nom_court": f"Conseil {body_key}",
        "attribution": {"texte": "Source: OpenParlData.ch", "lien": "https://openparldata.ch", "licence": "CC BY 4.0"},
        "voie_acces": "cron",
        "fraicheur": "import",
        "conseil": {"body_key": body_key, "donne": ["objets"]},
    }


SITE_PREVERENGES = _site(5643, "Préverenges", f"{PREVERENGES}/sitzung", f"{PREVERENGES}/conseil")


def _sources(*sources):
    return FichierSources.model_validate({"plateformes": PLATEFORMES, "sources": list(sources)})


SOURCES = _sources(_opendata("5586"), SITE_PREVERENGES)


def _seance_fabriquee(doc, titre):
    """La page de Séance de l'échantillon, retouchée pour une autre Séance : un seul document, `doc`, sous `titre`."""
    page = echantillon("i-web", "seances")[f"{PREVERENGES}/sitzung/6987205"]
    texte = page.corps.decode("utf-8")
    debut, fin = texte.index("<tbody>") + len("<tbody>"), texte.index("</tbody>")
    ligne = texte[debut : texte.index("</tr>", debut) + len("</tr>")]
    ligne = ligne.replace("7223149", doc).replace("1. Ordre du jour", titre)
    return Page(texte[:debut] + ligne + texte[fin:], entetes=page.entetes, gzip=True)


def _preverenges(horloge):
    """Le site de Préverenges : l'échantillon, et les pages des deux autres Séances de la fenêtre, fabriquées."""
    reseau = Reseau(horloge, adresses={"www.preverenges.ch": IP_PREVERENGES})
    reseau.pages |= echantillon("i-web", "seances")
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987214"] = _seance_fabriquee("7300001", "Ordre du jour")
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"] = _seance_fabriquee("7100001", "Procès-verbal")
    return reseau


def _monde(horloge):
    return Monde(
        horloge=horloge,
        affaires=[Affaire(id=2, body_key="5586", number="POS25/115", title="Postulat", updated_at="2026-10-14")],
    )


def _passer(depot, horloge, reseau, monde, sources=SOURCES, heure=None):
    horloge.heure = heure or horloge.heure
    with httpx.Client(transport=reseau.transport(repli=monde.transport())) as client:
        passage(
            depot,
            sources,
            client,
            horloge=horloge,
            issues=IssuesFactices(),
            attendre=horloge.attendre,
            resoudre=reseau.resoudre,
        )


def _lire(depot, chemin):
    return json.loads((depot / chemin).read_text(encoding="utf-8"))


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_une_commune_i_web_en_seances_seules_est_archivee_avec_ses_documents_et_son_lien_stable(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge), _monde(horloge))

    seance = _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")
    del seance["genere"]
    assert seance == {
        "version": 1,
        "id": None,
        "date": "2026-09-10T20:00",
        "nom": "Séance du Conseil communal",
        "lien": f"{PREVERENGES}/_rte/anlass/6987205",
        "ordre_du_jour": [],
        "documents": [
            {"titre": "1. Ordre du jour", "date": None, "lien": f"{PREVERENGES}/_doc/7223149"},
            {
                "titre": "2. Préavis 6-26_Autorisations_generales 2026-2031",
                "date": None,
                "lien": f"{PREVERENGES}/_doc/7223152",
            },
            {"titre": "4. Décision CC 10.09.26", "date": None, "lien": f"{PREVERENGES}/_doc/7223158"},
            {
                "titre": "5. PV 25.6.26 installations des Autorités approuvé le 10.9.26",
                "date": None,
                "lien": f"{PREVERENGES}/_doc/7223161",
            },
        ],
    }
