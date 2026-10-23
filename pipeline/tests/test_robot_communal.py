"""Le robot communal (ADR 0006), seul client HTTP des sites communaux, par sa seule opération : lire une URL pour
un rôle. Le réseau est un faux (`faux_sites.Reseau`) qui note chaque requête avec l'heure d'une horloge factice ;
l'attente du robot fait avancer cette horloge.

Ce que le passage du cron observe déjà sur l'échantillon (5 s par /24 et réseaux qui ne s'attendent pas,
redirections, User-Agent de l'import, encodage, `content-encoding` en minuscules) est testé par lui
(`test_sites_communaux.py`). Restent ici ce que le passage ne montre pas encore : requêtes de plusieurs fils, erreurs
typées et `Retry-After` (blocage, #151), User-Agent de la sonde (#150).
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import DELAI, REFUS, Page, Reseau
from robot_communal import DelaiDepasse, ErreurHttp, Injoignable, Robot

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

    assert len(reseau.journal) == 8
    assert reseau.en_vol_max == 1


@pytest.mark.parametrize(
    ("page", "erreur"),
    [
        (Page("introuvable", statut=404), ErreurHttp),
        (Page("", statut=503, entetes={"Retry-After": "3600"}), ErreurHttp),
        (REFUS, Injoignable),
        (DELAI, DelaiDepasse),
    ],
)
def test_une_page_non_lue_leve_une_erreur_typee_et_compte_dans_le_debit(horloge, page, erreur):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB})
    reseau.pages |= {"https://www.commune.ch/seances": page, "https://www.commune.ch/": Page("")}
    robot = _robot(reseau, horloge)

    with pytest.raises(erreur):
        robot.lire("https://www.commune.ch/seances", "sonde")
    robot.lire("https://www.commune.ch/", "sonde")

    assert reseau.heures() == [T0, T0 + timedelta(seconds=5)]


def test_une_erreur_http_dit_son_statut_et_son_retry_after(horloge):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB})
    reseau.pages["https://www.commune.ch/"] = Page("", statut=429, entetes={"Retry-After": "120"})

    with pytest.raises(ErreurHttp) as e:
        _robot(reseau, horloge).lire("https://www.commune.ch/", "import")

    assert (e.value.statut, e.value.retry_after) == (429, "120")


def test_un_nom_d_hote_inconnu_rend_la_page_injoignable_sans_requete(horloge):
    reseau = Reseau(horloge)

    with pytest.raises(Injoignable):
        _robot(reseau, horloge).lire("https://www.disparue.ch/", "sonde")

    assert reseau.journal == []


def test_le_user_agent_de_la_sonde_porte_son_role_le_courriel_et_le_lien_vers_l_a_propos(horloge):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB}, pages={"https://www.commune.ch/": Page("")})

    _robot(reseau, horloge).lire("https://www.commune.ch/", "sonde")

    assert reseau.journal[0].user_agent == (
        "VigieVaud-sonde (+https://louni-m.github.io/vigie-vaud/a-propos#robot; vigievaud.gentile263@passinbox.com)"
    )
