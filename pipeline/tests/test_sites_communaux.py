"""Les sites communaux dans le passage du cron (spec de J3, « Import des sites ») : une commune i-web en séances
seules, déclarée dans un `sources.json` de test, lue par le robot communal sur l'échantillon enregistré
(`echantillon-sites/i-web/`), archivée et listée comme un conseil d'OpenParlData.

C'est le seul seam du cron : le passage reçoit un seul transport, qui sert à la fois le faux OpenParlData de J1 et
les pages de l'échantillon (`faux_sites.Reseau`), une résolution d'adresse factice pour le /24 du robot, et une
horloge que l'attente fait avancer. On observe les fichiers écrits, le journal du passage et les requêtes reçues par
les sites (URL, User-Agent, heure). Les cas instables sont fabriqués par de petites retouches de l'échantillon.
"""

import html
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from cron import passage
from faux_openparldata import Affaire, HorlogeFactice, Monde
from faux_sites import Page, Reseau, echantillon
from schema import FichierSources
from test_cron import IssuesFactices

# 07:17 à Lausanne, le jour où l'échantillon a été enregistré : la fenêtre du passage part du 23 avril 2026.
T0 = datetime(2026, 10, 23, 5, 17, tzinfo=UTC)
S = timedelta(seconds=1)
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


def _seance_fabriquee(doc, titre, points=()):
    """La page de Séance de l'échantillon, retouchée pour une autre Séance : un seul document, `doc`, sous `titre`,
    et les `points` (numéro, titre) d'un ordre du jour en HTML, à la forme de celui de Blonay - Saint-Légier."""
    page = echantillon("i-web", "seances")[f"{PREVERENGES}/sitzung/6987205"]
    texte = page.corps.decode("utf-8")
    debut, fin = texte.index("<tbody>") + len("<tbody>"), texte.index("</tbody>")
    ligne = texte[debut : texte.index("</tr>", debut) + len("</tr>")]
    ligne = ligne.replace("7223149", doc).replace("1. Ordre du jour", titre)
    lignes = "".join(
        f'<tr id="traktanden_{i}"><td>{n}</td><td><div class="icms-wysiwyg">{t}</div></td><td></td></tr>\n'
        for i, (n, t) in enumerate(points, start=1)
    )
    ordre_du_jour = f"<h2>Points de l'ordre du jour</h2><table><tbody>\n{lignes}</tbody></table>\n" if points else ""
    texte = texte[:debut] + ligne + texte[fin:]
    fin_du_bloc = texte.index("</table>") + len("</table>")
    return Page(texte[:fin_du_bloc] + ordre_du_jour + texte[fin_du_bloc:], entetes=page.entetes, gzip=True)


def _preverenges(horloge):
    """Le site de Préverenges : l'échantillon, et les pages des deux autres Séances de la fenêtre, fabriquées."""
    reseau = Reseau(horloge, adresses={"www.preverenges.ch": IP_PREVERENGES})
    reseau.pages |= echantillon("i-web", "seances")
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987214"] = _seance_fabriquee("7300001", "Ordre du jour")
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"] = _seance_fabriquee("7100001", "Procès-verbal")
    return reseau


def _ligne(anlass, jour, heure="20h00 - 22h00", nom="Séance du Conseil communal"):
    """Une ligne de liste de Séances, à la forme de celles de l'échantillon (« 10.09.2026, 20h00 - 22h00 »)."""
    return {
        "name": f'<a href="/_rte/anlass/{anlass}">{nom}</a>',
        "_datum": f'<span class="d-none d-md-block"><span class="text-nowrap">{jour}, <br>{heure} </span></span>',
    }


def _liste_retouchee(reseau, retoucher):
    """La page de liste de Préverenges, dont `retoucher(id_du_tableau, lignes)` rend les nouvelles lignes, réécrites
    dans `data-entities` comme le site les écrit (JSON échappé dans l'attribut)."""
    url = f"{PREVERENGES}/sitzung"
    page = reseau.pages[url]
    texte = page.corps.decode("utf-8")

    def remplacer(m):
        donnees = json.loads(html.unescape(m[3]))
        donnees["data"] = retoucher(m[2], donnees["data"])
        return m[1] + html.escape(json.dumps(donnees), quote=True) + m[4]

    texte = re.sub(r'(<table[^>]*id="(\w+)"[^>]*data-entities=")([^"]*)(")', remplacer, texte)
    reseau.pages[url] = Page(texte, entetes=page.entetes, gzip=True)


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


def test_les_seances_de_la_fenetre_sont_listees_dans_l_ordre_des_dates_malgre_le_desordre_du_site(tmp_path, horloge):
    # La liste passée du site donne le 18 juin, le 10 septembre, puis le 5 février : hors de la fenêtre (avant le
    # 23 avril), la Séance de février n'est ni ouverte ni importée.
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert _lire(tmp_path, "conseils/5643/seances.json")["seances"] == [
        {
            "cle": "5643/2026-10-29",
            "date": "2026-10-29T20:00",
            "points": 0,
            "documents": [{"titre": "Ordre du jour", "date": None, "lien": f"{PREVERENGES}/_doc/7300001"}],
        },
        {
            "cle": "5643/2026-09-10",
            "date": "2026-09-10T20:00",
            "points": 0,
            "documents": _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")["documents"],
        },
        {
            "cle": "5643/2026-06-18",
            "date": "2026-06-18T19:00",
            "points": 0,
            "documents": [{"titre": "Procès-verbal", "date": None, "lien": f"{PREVERENGES}/_doc/7100001"}],
        },
    ]
    assert not any("7273262" in r.url for r in reseau.journal)
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert (conseil["source"], conseil["nom"], conseil["commune"], conseil["donne"]) == (
        "site-5643",
        "Conseil communal de Préverenges",
        5643,
        ["seances"],
    )
    assert (conseil["prochaine_seance"], conseil["derniere_seance"]) == ("5643/2026-10-29", "5643/2026-09-10")
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"


def test_le_meme_passage_importe_les_conseils_d_openparldata_comme_sans_site(tmp_path, horloge):
    seul, avec_site = tmp_path / "seul", tmp_path / "avec-site"
    seul.mkdir()
    avec_site.mkdir()

    # La sonde du site (robots.txt, puis la page de liste 5 s plus tard) précède l'import : sans site, le passage
    # part 5 s plus tard pour importer à la même heure.
    _passer(seul, horloge, _preverenges(horloge), _monde(horloge), sources=_sources(_opendata("5586")), heure=T0 + 5 * S)
    horloge.heure = T0
    _passer(avec_site, horloge, _preverenges(horloge), _monde(horloge))

    lausanne = sorted(p.relative_to(seul) for p in (seul / "conseils/5586").rglob("*.json"))
    assert lausanne == [
        Path("conseils/5586/objets/POS25-115.json"),
        Path("conseils/5586/objets-2026.json"),
        Path("conseils/5586/seances.json"),
    ]
    for chemin in lausanne:
        assert _lire(avec_site, chemin) == _lire(seul, chemin)
    # Le premier import d'un conseil scrapé est noté à part, pour l'issue `a-verifier` (#155) ; Lausanne n'en a pas.
    assert _lire(avec_site, "conseils/import.json") == _lire(seul, "conseils/import.json") | {
        "conseils": {"5586": "2026-10-23T05:17:05Z", "5643": "2026-10-23T05:17:05Z"},
        "premiers": {"5643": "2026-10-23T05:17:05Z"},
    }


def test_un_second_passage_ne_reecrit_rien(tmp_path, horloge):
    _passer(tmp_path, horloge, _preverenges(horloge), _monde(horloge))
    avant = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}

    reseau = _preverenges(horloge)
    _passer(tmp_path, horloge, reseau, _monde(horloge), heure=T0 + timedelta(days=1))

    assert any("/_rte/anlass/" in r.url for r in reseau.journal)  # les pages ont bien été relues
    apres = {p: p.read_bytes() for p in (tmp_path / "conseils").rglob("*.json") if p.name != "import.json"}
    assert apres == avant
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-24T05:17:05Z"


def test_une_commune_non_couverte_n_est_ni_sondee_ni_importee(tmp_path, horloge):
    # Une commune i-web qui ne publie que des préavis : déclarée avec sa plateforme, sa page de liste et sa raison,
    # mais sans conseil ni sonde. Son site n'est jamais lu, même s'il répond.
    sainte_croix = "https://www.sainte-croix.ch"
    reseau = _preverenges(horloge)
    reseau.adresses["www.sainte-croix.ch"] = "193.34.137.9"
    reseau.pages[f"{sainte_croix}/seances"] = reseau.pages[f"{PREVERENGES}/sitzung"]
    non_couverte = {
        k: v for k, v in _site(5568, "Sainte-Croix", f"{sainte_croix}/seances", f"{sainte_croix}/conseil").items()
        if k != "conseil"
    } | {"couverture": {"communes": [5568], "mode": "non_couvert", "raison": "preavis_seuls"}}

    sources = _sources(_opendata("5586"), SITE_PREVERENGES, non_couverte)

    _passer(tmp_path, horloge, reseau, _monde(horloge), sources=sources)

    assert not any(r.url.startswith(sainte_croix) for r in reseau.journal)
    assert any(r.url.startswith(PREVERENGES) for r in reseau.journal)
    assert "site-5568" not in _lire(tmp_path, "etat-sources.json")["sources"]
    assert [c["cle"] for c in _lire(tmp_path, "conseils/index.json")["conseils"]] == ["5586", "5643"]
    assert set(_lire(tmp_path, "conseils/import.json")["conseils"]) == {"5586", "5643"}
    assert not (tmp_path / "conseils/5568").exists()


# --- Cas instables, fabriqués par retouche de l'échantillon ---------------------------------------------------------


def test_une_date_fictive_est_importee_telle_quelle(tmp_path, horloge):
    # « Séance du 1er janvier » : une date que le site n'a pas corrigée, annoncée à venir.
    reseau = _preverenges(horloge)
    _liste_retouchee(
        reseau, lambda tableau, lignes: lignes + [_ligne(7400001, "01.01.2030", "00h00")] if "Future" in tableau else lignes
    )
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = _seance_fabriquee("7400002", "Ordre du jour")

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert _lire(tmp_path, "conseils/5643/seances/2030-01-01.json")["date"] == "2030-01-01"
    (conseil,) = [c for c in _lire(tmp_path, "conseils/index.json")["conseils"] if c["cle"] == "5643"]
    assert conseil["prochaine_seance"] == "5643/2026-10-29"


def test_un_element_illisible_est_saute_et_note_dans_le_journal(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    # Une ligne sans date, et la page du 18 juin qui ne répond plus.
    _liste_retouchee(
        reseau, lambda tableau, lignes: lignes + [_ligne(7400001, "", "")] if "Past" in tableau else lignes
    )
    del reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"]

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert [s["cle"] for s in _lire(tmp_path, "conseils/5643/seances.json")["seances"]] == [
        "5643/2026-10-29",
        "5643/2026-09-10",
    ]
    journal = capsys.readouterr().err
    assert "Conseil communal de Préverenges (site de la commune) : élément sauté" in journal
    assert "/_rte/anlass/7400001" in journal
    assert f"{PREVERENGES}/_rte/anlass/6987193 non lue" in journal
    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"


def test_une_liste_dont_aucune_ligne_ne_se_lit_met_l_import_de_la_commune_en_echec(tmp_path, horloge, capsys):
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [{"name": "Séance", "_datum": ligne["_datum"]} for ligne in lignes])

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert "Import en échec : Conseil communal de Préverenges (site de la commune)" in capsys.readouterr().err
    assert _lire(tmp_path, "conseils/import.json")["conseils"] == {"5586": "2026-10-23T05:17:05Z"}
    assert not (tmp_path / "conseils/5643/seances").exists()


def test_une_liste_vide_est_un_import_reussi_sans_seance(tmp_path, horloge):
    # Un conseil général entre deux séances : le site ne liste rien, ce n'est pas un échec.
    reseau = _preverenges(horloge)
    _liste_retouchee(reseau, lambda tableau, lignes: [])

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert _lire(tmp_path, "conseils/import.json")["conseils"]["5643"] == "2026-10-23T05:17:05Z"
    assert _lire(tmp_path, "conseils/5643/seances.json")["seances"] == []


def test_deux_seances_d_un_meme_jour_n_en_font_qu_une_avec_tous_leurs_points_et_documents(tmp_path, horloge):
    # Une Séance extraordinaire à 18 h, listée après celle de 20 h du même 10 septembre : l'heure fait la première.
    reseau = _preverenges(horloge)
    extraordinaire = _ligne(7400001, "10.09.2026", "18h00 - 19h00", "Séance extraordinaire")
    _liste_retouchee(reseau, lambda tableau, lignes: lignes + [extraordinaire] if "Past" in tableau else lignes)
    reseau.pages[f"{PREVERENGES}/_rte/anlass/7400001"] = _seance_fabriquee(
        "7400002", "Ordre du jour extraordinaire", points=[("1", "Assermentation"), ("2", "Préavis 7-26")]
    )

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    seance = _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")
    assert (seance["id"], seance["date"], seance["nom"], seance["lien"]) == (
        None,
        "2026-09-10T18:00",
        "Séance extraordinaire",
        f"{PREVERENGES}/_rte/anlass/7400001",
    )
    assert [p["titre"] for p in seance["ordre_du_jour"]] == ["Assermentation", "Préavis 7-26"]
    assert [d["lien"].rsplit("/", 1)[1] for d in seance["documents"]] == [
        "7400002",
        "7223149",
        "7223152",
        "7223158",
        "7223161",
    ]
    lignes = _lire(tmp_path, "conseils/5643/seances.json")["seances"]
    assert {"cle": "5643/2026-09-10", "date": "2026-09-10T18:00", "points": 2} in lignes


def test_les_titres_des_documents_d_une_seance_sont_masques(tmp_path, horloge):
    reseau = _preverenges(horloge)
    reseau.pages[f"{PREVERENGES}/_rte/anlass/6987193"] = _seance_fabriquee(
        "7100001", "Préavis 4-26 - Succession de M. Paul Exemple, vente de la parcelle 12"
    )

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    assert _lire(tmp_path, "conseils/5643/seances/2026-06-18.json")["documents"] == [
        {
            "titre": "Préavis 4-26 - Succession de [particulier], vente de la parcelle 12",
            "date": None,
            "lien": f"{PREVERENGES}/_doc/7100001",
        }
    ]


# --- Le robot communal, vu depuis le site ---------------------------------------------------------------------------


def test_le_robot_lit_le_site_une_page_toutes_les_5_s_sous_le_nom_vigievaud_import(tmp_path, horloge):
    reseau = _preverenges(horloge)

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    s = timedelta(seconds=1)
    assert [(r.url.removeprefix(PREVERENGES), r.heure - T0, r.user_agent.split(" ")[0]) for r in reseau.journal] == [
        ("/robots.txt", 0 * s, "VigieVaud-sonde"),  # lu une fois, avant la sonde (test_regles_du_robot.py)
        ("/sitzung", 5 * s, "VigieVaud-sonde"),  # la sonde, juste avant l'import (test_sondes_sites.py)
        ("/sitzung", 10 * s, "VigieVaud-import"),
        ("/_rte/anlass/6987214", 15 * s, "VigieVaud-import"),  # à venir, puis les passées dans l'ordre du site
        ("/_rte/anlass/6987193", 20 * s, "VigieVaud-import"),
        ("/_rte/anlass/6987205", 25 * s, "VigieVaud-import"),
        ("/sitzung/6987205", 30 * s, "VigieVaud-import"),  # la redirection du lien stable, au même débit
    ]
    assert reseau.journal[-1].user_agent == (
        "VigieVaud-import (+https://louni-m.github.io/vigie-vaud/a-propos#robot; vigievaud.gentile263@passinbox.com)"
    )


BLONAY = "https://www.blonay-saint-legier.ch"


@pytest.mark.parametrize(
    ("adresse", "attente"),
    [("195.65.10.22", 5), ("193.34.137.9", 0)],
    ids=["meme-24", "autre-reseau"],
)
def test_deux_communes_d_un_meme_24_s_attendent_et_celles_d_un_autre_reseau_non(tmp_path, horloge, adresse, attente):
    reseau = _preverenges(horloge)
    reseau.adresses["www.blonay-saint-legier.ch"] = adresse
    reseau.pages |= echantillon("i-web", "objets")
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")

    _passer(tmp_path, horloge, reseau, _monde(horloge), sources=_sources(SITE_PREVERENGES, blonay))

    heures = {r.url: r.heure for r in reseau.journal}
    assert heures[f"{BLONAY}/seances"] - heures[f"{PREVERENGES}/sitzung/6987205"] == timedelta(seconds=attente)


def test_une_page_en_iso_8859_1_est_lue_selon_son_content_type(tmp_path, horloge):
    # Les pages de l'échantillon sont servies compressées, avec `content-encoding: gzip` en minuscules ; celle-ci
    # l'est aussi, mais encodée en ISO-8859-1.
    reseau = _preverenges(horloge)
    url = f"{PREVERENGES}/sitzung/6987205"
    texte = reseau.pages[url].corps.decode("utf-8")
    reseau.pages[url] = Page(
        texte.encode("iso-8859-1"), entetes={"Content-Type": "text/html; charset=ISO-8859-1"}, gzip=True
    )

    _passer(tmp_path, horloge, reseau, _monde(horloge))

    titres = [d["titre"] for d in _lire(tmp_path, "conseils/5643/seances/2026-09-10.json")["documents"]]
    assert titres[1:] == [
        "2. Préavis 6-26_Autorisations_generales 2026-2031",
        "4. Décision CC 10.09.26",
        "5. PV 25.6.26 installations des Autorités approuvé le 10.9.26",
    ]


def test_les_points_d_une_seance_publies_en_html_sont_archives(tmp_path, horloge):
    # Blonay - Saint-Légier publie l'ordre du jour de ses Séances en HTML ; lue en séances seules, sans ses Objets.
    reseau = Reseau(horloge, adresses={"www.blonay-saint-legier.ch": "195.65.10.22"})
    reseau.pages |= echantillon("i-web", "objets")
    blonay = _site(5892, "Blonay - Saint-Légier", f"{BLONAY}/seances", f"{BLONAY}/conseil-communal")

    _passer(tmp_path, horloge, reseau, _monde(horloge), sources=_sources(blonay))

    seance = _lire(tmp_path, "conseils/5892/seances/2026-09-29.json")
    assert seance["ordre_du_jour"] == [
        {
            "numero": "01",
            "titre": "Adoption de l'ordre du jour définitif",
            "categorie": None,
            "resultat": None,
            "objet": None,
        },
        {"numero": "05", "titre": "Communications de la Municipalité", "categorie": None, "resultat": None, "objet": None},
        {
            "numero": "06",
            "titre": "Préavis 23-2026 concernant un crédit d'étude pour le renouvellement des infrastructures routières "
            "et souterraines communales ainsi que la réfection du Pont de Brent, pour un montant de CF 1'387'000.-",
            "categorie": None,
            "resultat": None,
            "objet": None,
        },
    ]
    assert [d["titre"] for d in seance["documents"]] == ["Ordre du jour", "Procès-verbal de la séance du 8 septembre 2026"]
    assert _lire(tmp_path, "conseils/5892/seances.json")["seances"][0] == {
        "cle": "5892/2026-09-29",
        "date": "2026-09-29T20:00",
        "points": 3,
    }
