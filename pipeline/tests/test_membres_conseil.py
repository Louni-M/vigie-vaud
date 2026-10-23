"""Les élu·e·s connu·e·s d'une commune scrapée (spec de J3, « Dépôt de données », « Import des sites », « Masquage ») :
la page des membres du conseil, lue par le robot au passage, remplit `conseils/<ofs>/membres.json`, une liste qui ne
fait que s'allonger, et le masquage épargne ces élu·e·s dans les titres de la commune.

Par le seul seam du cron, le passage, comme `test_sites_communaux` dont ce fichier reprend le site de Préverenges :
l'échantillon i-web (variante Séances) porte sa page des membres, le bureau du Conseil (`personList`, « Nom Prénom »).
"""

import html
import json
import re
from datetime import timedelta

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page
from passage_sites import (
    PREVERENGES,
    SITE_PREVERENGES,
    T0,
    _lire,
    _passer,
    _preverenges,
    _seance_fabriquee,
    _sources,
)

MEMBRES = f"{PREVERENGES}/conseil"
AVEC_MEMBRES = _sources({**SITE_PREVERENGES, "site": {**SITE_PREVERENGES["site"], "membres": MEMBRES}})


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_la_page_des_membres_remplit_la_liste_des_elus_connus_du_conseil(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge), sources=AVEC_MEMBRES)

    membres = _lire(tmp_path, "conseils/5643/membres.json")
    del membres["genere"]
    # La page donne « Nom Prénom » : la liste les remet dans l'ordre « Prénom Nom » du masquage, triés.
    assert membres == {"version": 1, "conseil": "5643", "membres": ["Béatrice Moser", "Steen Boschetti"]}


def _membres_retouches(reseau, noms):
    """La page des membres de Préverenges, dont les lignes deviennent celles des `noms` (« Nom Prénom », inventés
    sauf ceux de l'échantillon), réécrites dans `data-entities` comme le site les écrit."""
    url = f"{PREVERENGES}/conseil/29471"
    page = reseau.pages[url]
    texte = page.corps.decode("utf-8")

    def remplacer(m):
        donnees = json.loads(html.unescape(m[2]))
        modele = donnees["data"][0]
        donnees["data"] = [
            {**modele, "_nameVorname": f'<a href="/_rte/person/{900000 + i}">{nom}</a>'} for i, nom in enumerate(noms)
        ]
        return m[1] + html.escape(json.dumps(donnees), quote=True) + m[3]

    texte = re.sub(r'(<table[^>]*id="icmsTable-personList"[^>]*data-entities=")([^"]*)(")', remplacer, texte)
    reseau.pages[url] = Page(texte, entetes=page.entetes, gzip=True)


def test_un_nom_qui_disparait_de_la_page_des_membres_reste_dans_la_liste(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge), sources=AVEC_MEMBRES)

    # Au nouveau bureau, Béatrice Moser n'y est plus et une nouvelle élue y entre.
    reseau = _preverenges(horloge)
    _membres_retouches(reseau, ["Boschetti Steen", "Exemple-Modèle Anne-Laure"])
    _passer(tmp_path, horloge, reseau, sources=AVEC_MEMBRES, heure=T0 + timedelta(days=1))

    assert _lire(tmp_path, "conseils/5643/membres.json")["membres"] == [
        "Anne-Laure Exemple-Modèle",
        "Béatrice Moser",
        "Steen Boschetti",
    ]


def _seance_du_18_juin(reseau):
    """La Séance du 18 juin, dont un document et deux points nomment des membres du bureau et une personne
    inventée, chacun·e après une civilité ; « Rapp. Mme Moser » : un nom partiel en contexte d'élue."""
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"] = _seance_fabriquee(
        "7100001",
        "Postulat de M. Steen Boschetti pour un parc",
        points=[("1", "Préavis 4-26 - Budget (Rapp. Mme Moser)"), ("2", "Lettre de M. Paul Exemple, Rue du Lac 2")],
    )


def test_un_membre_nomme_apres_une_civilite_reste_lisible_et_une_personne_inconnue_est_masquee(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _seance_du_18_juin(reseau)

    _passer(tmp_path, horloge, reseau, sources=AVEC_MEMBRES)

    seance = _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")
    assert [d["titre"] for d in seance["documents"]] == ["Postulat de M. Steen Boschetti pour un parc"]
    assert [p["titre"] for p in seance["ordre_du_jour"]] == [
        "Préavis 4-26 - Budget (Rapp. Mme Moser)",
        "Lettre de [particulier], [coordonnées]",
    ]


def test_un_conseil_sans_page_des_membres_est_importe_ses_elus_masques(tmp_path, horloge):
    reseau = _preverenges(horloge)
    _seance_du_18_juin(reseau)

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_PREVERENGES))

    assert not any(r.url.startswith(MEMBRES) for r in reseau.journal)
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"
    seance = _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")
    assert [d["titre"] for d in seance["documents"]] == ["Postulat de [particulier] pour un parc"]
    assert [p["titre"] for p in seance["ordre_du_jour"]] == [
        "Préavis 4-26 - Budget (Rapp. [particulier])",
        "Lettre de [particulier], [coordonnées]",
    ]
    assert _lire(tmp_path, "conseils/5643/membres.json")["membres"] == []


def test_une_page_des_membres_qui_ne_se_lit_plus_n_empeche_pas_l_import_et_la_liste_reste(tmp_path, horloge, capsys):
    _passer(tmp_path, horloge, _preverenges(horloge), sources=AVEC_MEMBRES)
    reseau = _preverenges(horloge)
    del reseau.pages[f"{PREVERENGES}/conseil/29471"]
    _seance_du_18_juin(reseau)

    _passer(tmp_path, horloge, reseau, sources=AVEC_MEMBRES, heure=T0 + timedelta(days=1))

    assert f"page des membres {MEMBRES} non lue" in capsys.readouterr().err
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-24T05:17:05Z"
    assert _lire(tmp_path, "conseils/5643/membres.json")["membres"] == ["Béatrice Moser", "Steen Boschetti"]
    seance = _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")
    assert seance["ordre_du_jour"][0]["titre"] == "Préavis 4-26 - Budget (Rapp. Mme Moser)"
