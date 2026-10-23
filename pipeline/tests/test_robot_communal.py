"""Le robot communal (ADR 0006), seul client HTTP des sites communaux, par sa seule opération : lire une URL pour
un rôle. Le réseau est un faux (`faux_sites.Reseau`) qui note chaque requête avec l'heure d'une horloge factice ;
l'attente du robot fait avancer cette horloge.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import DELAI, REFUS, Page, Reseau, redirection
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


def test_cinq_secondes_au_moins_entre_deux_requetes_vers_un_meme_24_sans_attendre_les_autres_reseaux(horloge):
    # Deux communes i-web sur deux adresses du même /24, une commune Quicksite sur un autre réseau.
    reseau = Reseau(horloge, adresses={"a.ch": "195.65.10.20", "b.ch": "195.65.10.25", "q.ch": "193.34.137.9"})
    for hote in ("a.ch", "b.ch", "q.ch"):
        for chemin in ("/1", "/2"):
            reseau.pages[f"https://{hote}{chemin}"] = Page("")
    robot = _robot(reseau, horloge)

    for url in ("https://a.ch/1", "https://q.ch/1", "https://b.ch/1", "https://q.ch/2", "https://a.ch/2"):
        robot.lire(url, "import")

    s = timedelta(seconds=1)
    assert [(r.url, r.heure - T0) for r in reseau.journal] == [
        ("https://a.ch/1", 0 * s),
        ("https://q.ch/1", 0 * s),  # autre réseau : pas d'attente
        ("https://b.ch/1", 5 * s),  # même /24 que a.ch, autre hôte
        ("https://q.ch/2", 5 * s),  # q.ch attendait depuis 0 s : 5 s sont déjà passées
        ("https://a.ch/2", 10 * s),
    ]


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


def test_les_redirections_sont_suivies_une_a_une_au_meme_debit(horloge):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB})
    reseau.pages |= {
        "https://www.commune.ch/_rte/anlass/7702069": redirection("/seances/7702069"),
        "https://www.commune.ch/seances/7702069": Page("<h1>Séance</h1>"),
    }

    reponse = _robot(reseau, horloge).lire("https://www.commune.ch/_rte/anlass/7702069", "import")

    assert (reponse.url, reponse.texte) == ("https://www.commune.ch/seances/7702069", "<h1>Séance</h1>")
    assert [(r.url, r.heure) for r in reseau.journal] == [
        ("https://www.commune.ch/_rte/anlass/7702069", T0),
        ("https://www.commune.ch/seances/7702069", T0 + timedelta(seconds=5)),
    ]


def test_une_page_en_iso_8859_1_est_decodee_selon_son_content_type(horloge):
    reseau = Reseau(horloge, adresses={"conseil.commune.ch": "185.54.6.10"})
    reseau.pages["https://conseil.commune.ch/seances.asp"] = Page(
        "Séance du conseil, procès-verbal".encode("iso-8859-1"),
        entetes={"Content-Type": "text/html; charset=ISO-8859-1"},
    )

    reponse = _robot(reseau, horloge).lire("https://conseil.commune.ch/seances.asp", "import")

    assert reponse.texte == "Séance du conseil, procès-verbal"


def test_un_corps_compresse_annonce_par_un_content_encoding_en_minuscules_est_decompresse(horloge):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB})
    reseau.pages["https://www.commune.ch/"] = Page("<p>Préavis</p>", gzip=True)

    reponse = _robot(reseau, horloge).lire("https://www.commune.ch/", "import")

    assert (reponse.texte, reponse.entetes["content-encoding"]) == ("<p>Préavis</p>", "gzip")


@pytest.mark.parametrize("role", ["sonde", "import"])
def test_le_user_agent_porte_le_role_le_courriel_et_le_lien_vers_l_a_propos(horloge, role):
    reseau = Reseau(horloge, adresses={"www.commune.ch": IWEB}, pages={"https://www.commune.ch/": Page("")})

    _robot(reseau, horloge).lire("https://www.commune.ch/", role)

    assert reseau.journal[0].user_agent == (
        f"VigieVaud-{role} (+https://louni-m.github.io/vigie-vaud/a-propos#robot; vigievaud.gentile263@passinbox.com)"
    )
