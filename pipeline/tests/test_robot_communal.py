"""Le robot communal (ADR 0006), seul client HTTP des sites communaux, par sa seule opération : lire une URL pour
un rôle. Le réseau est un faux (`faux_sites.Reseau`) qui note chaque requête avec l'heure d'une horloge factice ;
l'attente du robot fait avancer cette horloge.

Ce que le passage du cron observe sur l'échantillon (5 s par /24 et réseaux qui ne s'attendent pas, redirections,
User-Agents de la sonde et de l'import, encodage, `content-encoding` en minuscules, erreurs vues par la sonde,
`robots.txt`, `Crawl-delay`, réseaux ralentis, blocage et `Retry-After`, plafond) est testé par lui
(`test_sites_communaux.py`, `test_sondes_sites.py`, `test_regles_du_robot.py`). Restent ici ce que le passage ne
montre pas : la forme de la réponse, les requêtes de plusieurs fils et un nom d'hôte inconnu.
"""

from datetime import UTC, datetime

import httpx
import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau
from robot_communal import Injoignable, Robot

T0 = datetime(2026, 10, 23, 7, 0, tzinfo=UTC)
IWEB = "195.65.10.20"


def _robot(reseau: Reseau, horloge: HorlogeFactice) -> Robot:
    return Robot(httpx.Client(transport=reseau.transport()), horloge, horloge.attendre, reseau.resoudre)


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_une_page_est_rendue_decodee_avec_son_statut_et_ses_en_tetes_utiles(horloge):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB})
    reseau.pages["https://www.commune.ch/seances"] = Page(
        "<table id='icmsTablePastSitzungen'>Séance</table>",
        entetes={"Content-Type": "text/html; charset=utf-8", "Set-Cookie": "x=1", "Content-Disposition": "inline"},
    )

    reponse = _robot(reseau, horloge).lire("https://www.commune.ch/seances", "import")

    assert reponse.statut == 200
    assert reponse.texte == "<table id='icmsTablePastSitzungen'>Séance</table>"
    assert reponse.url == "https://www.commune.ch/seances"
    assert reponse.entetes == {"content-type": "text/html; charset=utf-8", "content-disposition": "inline"}


def test_une_requete_a_la_fois_meme_appele_de_plusieurs_fils(horloge):
    import threading

    reseau = Reseau(horloge, adresses={f"c{i}.ch": f"10.0.{i}.1" for i in range(8)}, duree=0.02)
    for i in range(8):
        reseau.pages[f"https://c{i}.ch/"] = Page("")
    robot = _robot(reseau, horloge)

    fils = [threading.Thread(target=robot.lire, args=(f"https://c{i}.ch/", "import")) for i in range(8)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()

    assert len(reseau.journal) == 16  # robots.txt et la page, pour chaque site
    assert reseau.en_vol_max == 1


def test_un_nom_d_hote_inconnu_rend_la_page_injoignable_sans_requete(horloge):
    reseau = Reseau(horloge)

    with pytest.raises(Injoignable):
        _robot(reseau, horloge).lire("https://www.disparue.ch/", "sonde")

    assert reseau.journal == []

