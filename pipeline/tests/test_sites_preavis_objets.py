"""Les niveaux « objets et séances » et « séances et préavis » d'i-web dans le passage du cron (spec de J3, « Import
des sites », ADR 0010) : les variantes **Objets** (module Objets de Blonay - Saint-Légier) et **pages** (tableau des
préavis rédigé dans la page des Séances de Puidoux), lues sur leur échantillon par le seul seam du cron, le passage.

Les Objets dont l'échantillon n'a pas la page sont servis par une retouche de la page d'Objet enregistrée ; les cas
instables (Objet sans numéro, doublon de numéro) par une retouche de la liste.
"""

import html
import json
import re
from datetime import timedelta

import pytest

from faux_openparldata import HorlogeFactice
from faux_sites import Page, Reseau, echantillon
from schema import FichierSources
from passage_sites import T0, _lire, _opendata, _passer, _site

BLONAY = "https://www.blonay-saint-legier.ch"
PUIDOUX = "https://www.puidoux.ch"

PLATEFORMES = [
    {
        "id": "i-web",
        "nom": "i-web",
        "editeur": "Innovative Web AG",
        "variantes": [
            {"id": "seances", "marqueur": "icmsTablePastSitzungen", "niveaux": [["seances"]]},
            {"id": "objets", "marqueur": "icmsTablePastSitzungen", "niveaux": [["objets", "seances"], ["seances"]]},
            {"id": "pages", "marqueur": "icmsTablePastSitzungen", "niveaux": [["preavis", "seances"], ["seances"]]},
        ],
    }
]


def _commune(ofs, commune, variante, donne, seances, objets, lien_conseil):
    source = _site(ofs, commune, seances, lien_conseil)
    source["conseil"]["donne"] = donne
    source["site"] |= {"variante": variante, "objets": objets}
    return source


SITE_BLONAY = _commune(
    5892,
    "Blonay - Saint-Légier",
    "objets",
    ["objets", "seances"],
    f"{BLONAY}/seances",
    f"{BLONAY}/objets-politiques",
    f"{BLONAY}/conseil-communal",
)


def _sources(*sources):
    return FichierSources.model_validate({"plateformes": PLATEFORMES, "sources": [_opendata("5586"), *sources]})


def _blonay(horloge):
    reseau = Reseau(horloge, adresses={"www.blonay-saint-legier.ch": "195.65.10.22"})
    reseau.pages |= echantillon("i-web", "objets")
    return reseau


@pytest.fixture
def horloge():
    return HorlogeFactice(T0)


def test_un_objet_du_module_objets_est_archive_avec_son_numero_brut_son_type_sa_date_son_statut_et_ses_documents(
    tmp_path, horloge
):
    _passer(tmp_path, horloge, _blonay(horloge), sources=_sources(SITE_BLONAY))

    objet = _lire(tmp_path, "conseils/5892/objets/2026-PM-37.json")
    del objet["genere"]
    assert objet == {
        "version": 1,
        "id": None,
        "numero": "2026-PM-37",
        "type": "Préavis municipal",
        "statut": {"libelle": "Déposé", "date": None},
        "depose": "2026-09-29",
        "titre": "Préavis 37-2026 - Budget 2027 du Fonds culturel Riviera",
        "contributeurs": [],
        "etapes": [],
        "documents": [{"titre": "Préavis 37-2026", "date": None, "lien": f"{BLONAY}/_doc/7266349"}],
        "lien": f"{BLONAY}/_rte/information/3002200",
        "communes": [],
    }


def test_les_auteur_e_s_publie_e_s_par_la_fiche_d_un_objet_sont_archive_e_s_et_restent_nomme_e_s_dans_son_titre(
    tmp_path, horloge
):
    _passer(tmp_path, horloge, _blonay(horloge), sources=_sources(SITE_BLONAY))

    postulat = _lire(tmp_path, "conseils/5892/objets/2026-PO-02.json")
    assert (postulat["type"], postulat["depose"], postulat["statut"]) == (
        "Postulat",
        "2026-09-29",
        {"libelle": "Déposé", "date": None},
    )
    # i-web nomme la personne « Krebs Yann » : l'élu connu est « Yann Krebs », que le masquage reconnaît.
    assert postulat["contributeurs"] == [{"nom": "Yann Krebs", "parti": None, "role": None, "sorte": "personne"}]
    assert postulat["titre"].startswith('Postulat de M. Y. Krebs, PVL-LC - "Valorisation de l\'annexe')
    assert postulat["documents"] == [{"titre": "Postulat de Y. Krebs", "date": None, "lien": f"{BLONAY}/_doc/7263511"}]


def _fiche_fabriquee(doc, statut=True):
    """La fiche d'Objet de l'échantillon (préavis 37-2026), retouchée pour un autre Objet : son seul document est
    `doc`, et sans `statut` la fiche ne publie pas de statut."""
    page = echantillon("i-web", "objets")[f"{BLONAY}/objetspolitiques/3002200"]
    texte = page.corps.decode("utf-8").replace("7266349", doc)
    if not statut:
        texte = texte.replace("<dt>Statut</dt>\n<dd>Déposé</dd>\n", "")
    return Page(texte, entetes=page.entetes, gzip=True)


def test_un_point_d_ordre_du_jour_est_relie_a_son_objet_par_son_numero(tmp_path, horloge):
    # Le point 6 de la Séance du 29 septembre cite le préavis 23-2026 (`/_rte/information/2909893`), que la liste
    # des Objets numérote 2026-PM-23 ; sa fiche, fabriquée, ne publie pas de statut.
    reseau = _blonay(horloge)
    reseau.pages[f"{BLONAY}/_rte/information/2909893"] = _fiche_fabriquee("7100001", statut=False)

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_BLONAY))

    preavis = _lire(tmp_path, "conseils/5892/objets/2026-PM-23.json")
    assert (preavis["type"], preavis["depose"], preavis["statut"], preavis["contributeurs"]) == (
        "Préavis municipal",
        "2026-06-16",
        None,
        [],
    )
    points = _lire(tmp_path, "conseils/5892/seances/2026-09-29.json")["ordre_du_jour"]
    assert [(p["numero"], p["objet"]) for p in points] == [("01", None), ("05", None), ("06", "5892/2026-PM-23")]


def test_les_documents_d_un_point_sans_objet_vont_a_la_seance(tmp_path, horloge):
    # Retouche de la Séance du 29 septembre : une annexe au point 01 (sans Objet), et un rapport au point 06, relié au
    # préavis 23-2026, dont la fiche donne les documents.
    reseau = _blonay(horloge)
    url = f"{BLONAY}/seances/6895123"
    texte = reseau.pages[url].corps.decode("utf-8")
    texte = texte.replace(
        "<td>01</td>\n<td><div class=\"icms-wysiwyg\">Adoption de l'ordre du jour définitif</div></td>\n<td></td>",
        "<td>01</td>\n<td><div class=\"icms-wysiwyg\">Adoption de l'ordre du jour définitif</div></td>\n"
        '<td><a href="/_doc/7400001">Annexe au point 1</a></td>',
    )
    texte = texte.replace(
        '<td><a href="/_rte/information/2909893">Préavis 23-2026</a></td>',
        '<td><a href="/_rte/information/2909893">Préavis 23-2026</a>, '
        '<a href="/_doc/7400002">Rapport de la commission</a></td>',
    )
    assert texte.count("/_doc/74000") == 2
    reseau.pages[url] = Page(texte, entetes=reseau.pages[url].entetes, gzip=True)
    reseau.pages[f"{BLONAY}/_rte/information/2909893"] = _fiche_fabriquee("7100001")

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_BLONAY))

    seance = _lire(tmp_path, "conseils/5892/seances/2026-09-29.json")
    assert [(d["titre"], d["lien"].rsplit("/", 1)[1]) for d in seance["documents"]] == [
        ("Ordre du jour", "7246414"),
        ("Procès-verbal de la séance du 8 septembre 2026", "7262080"),
        ("Annexe au point 1", "7400001"),
    ]
    assert [(p["numero"], p["objet"]) for p in seance["ordre_du_jour"]] == [
        ("01", None),
        ("05", None),
        ("06", "5892/2026-PM-23"),
    ]


def _objets_retouches(reseau, retoucher):
    """La liste des Objets de Blonay - Saint-Légier, dont `retoucher(lignes)` rend les nouvelles lignes, réécrites
    dans `data-entities` comme le site les écrit (JSON échappé dans l'attribut)."""
    url = f"{BLONAY}/objets-politiques"
    page = reseau.pages[url]
    texte = page.corps.decode("utf-8")

    def remplacer(m):
        donnees = json.loads(html.unescape(m[2]))
        donnees["data"] = retoucher(donnees["data"])
        return m[1] + html.escape(json.dumps(donnees), quote=True) + m[3]

    texte = re.sub(r'(<table[^>]*data-entities=")([^"]*)(")', remplacer, texte)
    reseau.pages[url] = Page(texte, entetes=page.entetes, gzip=True)


def _numeroter(numeros):
    """Retouche qui donne à l'Objet de chaque lien stable (`/_rte/information/<id>`) un autre numéro."""

    def retoucher(lignes):
        for ligne in lignes:
            ident = re.search(r"/_rte/information/(\d+)", ligne["title"])[1]
            ligne["_nummer"] = numeros.get(ident, ligne["_nummer"])
        return lignes

    return retoucher


def test_un_objet_sans_numero_n_est_pas_importe_et_un_doublon_de_numero_garde_le_premier_du_site(
    tmp_path, horloge, capsys
):
    # Le postulat perd son numéro ; le préavis 23-2026, listé après le 37-2026, en prend le numéro.
    reseau = _blonay(horloge)
    _objets_retouches(reseau, _numeroter({"3000802": "", "2909893": "2026-PM-37"}))

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_BLONAY))

    assert _lire(tmp_path, "conseils/5892/objets/2026-PM-37.json")["lien"] == f"{BLONAY}/_rte/information/3002200"
    assert sorted(p.name for p in (tmp_path / "conseils/5892/objets").iterdir()) == ["2026-PM-37.json"]
    assert not any(r.url.endswith(("/3000802", "/2909893")) for r in reseau.journal)
    journal = capsys.readouterr().err
    assert "élément sauté, Objet sans numéro, non importé : Postulat de M. Y. Krebs" in journal
    assert "élément sauté, Objet 2026-PM-37 en double, le premier du site gardé : Préavis 23-2026" in journal


def test_un_objet_d_avant_la_fenetre_n_est_ni_ouvert_ni_importe_au_passage_ordinaire(tmp_path, horloge):
    # Le préavis 37-2026 daté du 22 avril 2026, la veille du premier jour de la fenêtre.
    reseau = _blonay(horloge)

    def dater(lignes):
        for ligne in lignes:
            if "/3002200" in ligne["title"]:
                ligne["_geschaeftsdatum"] = "22.04.2026"
        return lignes

    _objets_retouches(reseau, dater)

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_BLONAY))

    assert not any(r.url.endswith("/3002200") for r in reseau.journal)
    assert not (tmp_path / "conseils/5892/objets/2026-PM-37.json").exists()
    assert (tmp_path / "conseils/5892/objets/2026-PO-02.json").exists()


def test_un_objet_sans_identifiant_relu_le_lendemain_remplace_celui_de_l_archive(tmp_path, horloge):
    # Le site corrige le titre du préavis 37-2026 : sans identifiant, l'Objet relu remplace celui de l'archive, au
    # même fichier (la clé est son numéro).
    _passer(tmp_path, horloge, _blonay(horloge), sources=_sources(SITE_BLONAY))
    reseau = _blonay(horloge)

    def corriger(lignes):
        for ligne in lignes:
            ligne["title"] = ligne["title"].replace("Budget 2027 du Fonds culturel Riviera", "Budget 2027 du Fonds")
        return lignes

    _objets_retouches(reseau, corriger)

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_BLONAY), heure=T0 + timedelta(days=1))

    objet = _lire(tmp_path, "conseils/5892/objets/2026-PM-37.json")
    assert (objet["id"], objet["titre"]) == (None, "Préavis 37-2026 - Budget 2027 du Fonds")


# --- Variante pages : les préavis rédigés dans une page (Puidoux) ----------------------------------------------------

SITE_PUIDOUX = _commune(
    5607, "Puidoux", "pages", ["preavis", "seances"], f"{PUIDOUX}/seances", f"{PUIDOUX}/seances", f"{PUIDOUX}/conseil"
)


def _puidoux(horloge):
    reseau = Reseau(horloge, adresses={"www.puidoux.ch": "193.34.137.9"})
    reseau.pages |= echantillon("i-web", "pages")
    return reseau


def test_les_preavis_rediges_dans_une_page_sont_archives_avec_leur_numero_brut_leur_date_et_leur_document(
    tmp_path, horloge, capsys
):
    reseau = _puidoux(horloge)

    _passer(tmp_path, horloge, reseau, sources=_sources(SITE_PUIDOUX))

    preavis = _lire(tmp_path, "conseils/5607/objets/10-2023.json")
    del preavis["genere"]
    assert preavis == {
        "version": 1,
        "id": None,
        "numero": "10-2023",
        "type": "Préavis",
        "statut": {"libelle": "Retiré", "date": None},
        "depose": "2023-11-21",
        "titre": "Concernant la démolition et la reconstruction d’un chalet d’alpage au Mont-Chesau",
        "contributeurs": [],
        "etapes": [],
        "documents": [
            {
                "titre": "Préavis 10-2023 – 21.11.2023",
                "date": None,
                "lien": f"{PUIDOUX}/_docn/5549947/Pr%C3%A9avis_10-2023.pdf",
            }
        ],
        "lien": None,
        "communes": [],
    }
    # Toutes les lignes de la liste, même hors de la fenêtre ; la proposition du bureau, sans numéro, n'en est pas.
    assert sorted(p.name for p in (tmp_path / "conseils/5607/objets").iterdir()) == [
        "03-2026.json",
        "05-2026.json",
        "07-2026.json",
        "08-2024.json",
        "09-2021.json",
        "10-2023.json",
    ]
    sans_document = _lire(tmp_path, "conseils/5607/objets/09-2021.json")
    assert (sans_document["depose"], sans_document["titre"], sans_document["documents"]) == ("2021-11-09", "Budget 2022", [])
    assert _lire(tmp_path, "conseils/5607/objets/03-2026.json")["depose"] == "2026-05-19"  # « du 19 mai 2026 »
    assert "élément sauté, Objet sans numéro, non importé : Proposition du bureau du CC" in capsys.readouterr().err
    # La page des préavis est celle des Séances : l'import ne la lit qu'une fois (la sonde la lit avant lui).
    imports = [r.url for r in reseau.journal if r.user_agent.startswith("VigieVaud-import")]
    assert imports.count(f"{PUIDOUX}/seances") == 1
