"""Un passage du cron, lancé contre un dossier temporaire qui tient lieu de clone du dépôt de données.

C'est le seul point de test du cron (spec de J0, « Décisions de test ») : le transport HTTP et l'horloge sont
factices, et on observe ce que le passage écrit dans le clone. Le commit et le push restent en dehors.
"""

import json
import ssl
from datetime import UTC, datetime, timedelta

import httpx
import jsonschema
import pytest

from cron import IssuesGitHub, client_issues, passage
from schema import RACINE, FichierSources, lire_sources

T0 = datetime(2026, 10, 14, 12, 17, tzinfo=UTC)
URL_SONDE = "https://sonde.exemple.ch/query?f=json"


def _source(id="camac-permis", sonde=None):
    source = {
        "id": id,
        "nom": "Permis CAMAC (MapServer/537)",
        "nom_court": "CAMAC",
        "attribution": {"texte": "© Exemple", "lien": "https://exemple.ch", "licence": "Exemple"},
        "voie_acces": "direct",
        "fraicheur": "requete",
        "couverture": {"communes": "canton", "mode": "api"},
    }
    if sonde is not None:
        source["sonde"] = {"url": URL_SONDE, "delai": 20} | sonde
    return source


def _sources(*sources):
    return FichierSources.model_validate({"sources": list(sources)})


SONDEE = _source(sonde={"champs": ["NO_CAMAC", "ETAT"], "jamais_vide": True})


def _dossiers(*enregistrements):
    return {"features": [{"attributes": e} for e in enregistrements]}


DOSSIER = {"NO_CAMAC": 123456, "ETAT": "En cours"}


def _repondre(reponse):
    """Transport factice : `reponse` est une `httpx.Response`, un dict renvoyé en JSON, ou une exception levée."""
    requetes = []

    def traiter(requete):
        requetes.append(requete)
        if isinstance(reponse, Exception):
            raise reponse
        if isinstance(reponse, httpx.Response):
            return reponse
        return httpx.Response(200, json=reponse)

    return httpx.MockTransport(traiter), requetes


class IssuesFactices:
    """Client d'issues factice : note les pannes et les retours que le passage lui signale."""

    def __init__(self):
        self.signalements = []

    def signalees(self, sources):
        return None

    def panne(self, source, etat):
        self.signalements.append(("panne", source.id, etat.depuis.isoformat()))

    def retour(self, source, panne, etat):
        self.signalements.append(("retour", source.id, panne.depuis.isoformat(), etat.depuis.isoformat()))


def _passer(depot, sources, reponse, heure=T0, issues=None):
    transport, requetes = _repondre(reponse)
    with httpx.Client(transport=transport) as client:
        passage(depot, sources, client, horloge=lambda: heure, issues=issues or IssuesFactices())
    return json.loads((depot / "etat-sources.json").read_text()), requetes


def test_une_source_neuve_qui_repond_est_ecrite_disponible_avec_l_enveloppe(tmp_path):
    etat, _ = _passer(tmp_path, _sources(SONDEE), _dossiers(DOSSIER))

    assert etat == {
        "version": 1,
        "genere": "2026-10-14T12:17:00Z",
        "sources": {
            "camac-permis": {
                "etat": "disponible",
                "depuis": "2026-10-14T12:17:00Z",
                "derniere_sonde": "2026-10-14T12:17:00Z",
                "dernier_succes": "2026-10-14T12:17:00Z",
                "echecs_consecutifs": 0,
                "motif": None,
            }
        },
    }
    schema = json.loads((tmp_path / "schema" / "etat-sources.schema.json").read_text())
    jsonschema.validate(etat, schema)


def test_un_echec_laisse_la_source_disponible_et_deux_la_passent_en_panne_depuis_le_premier(tmp_path):
    sources = _sources(SONDEE)
    T1, T2 = T0 + timedelta(minutes=30), T0 + timedelta(minutes=60)
    _passer(tmp_path, sources, _dossiers(DOSSIER), T0)

    apres_un, _ = _passer(tmp_path, sources, httpx.Response(503), T1)
    apres_deux, _ = _passer(tmp_path, sources, httpx.Response(503), T2)

    assert apres_un["sources"]["camac-permis"] == {
        "etat": "disponible",
        "depuis": "2026-10-14T12:17:00Z",
        "derniere_sonde": "2026-10-14T12:47:00Z",
        "dernier_succes": "2026-10-14T12:17:00Z",
        "echecs_consecutifs": 1,
        "motif": "HTTP 503",
    }
    assert apres_deux["sources"]["camac-permis"] == {
        "etat": "en_panne",
        "depuis": "2026-10-14T12:47:00Z",
        "derniere_sonde": "2026-10-14T13:17:00Z",
        "dernier_succes": "2026-10-14T12:17:00Z",
        "echecs_consecutifs": 2,
        "motif": "HTTP 503",
    }


def test_un_succes_fait_revenir_la_source_et_remet_le_compteur_a_zero(tmp_path):
    sources = _sources(SONDEE)
    for minutes in (0, 30, 60):
        _passer(tmp_path, sources, httpx.Response(503), T0 + timedelta(minutes=minutes))

    etat, _ = _passer(tmp_path, sources, _dossiers(DOSSIER), T0 + timedelta(minutes=90))

    assert etat["sources"]["camac-permis"] == {
        "etat": "disponible",
        "depuis": "2026-10-14T13:47:00Z",
        "derniere_sonde": "2026-10-14T13:47:00Z",
        "dernier_succes": "2026-10-14T13:47:00Z",
        "echecs_consecutifs": 0,
        "motif": None,
    }


def test_un_succes_apres_un_seul_echec_garde_le_depuis_de_la_source_disponible(tmp_path):
    sources = _sources(SONDEE)
    _passer(tmp_path, sources, _dossiers(DOSSIER), T0)
    _passer(tmp_path, sources, httpx.Response(503), T0 + timedelta(minutes=30))

    etat, _ = _passer(tmp_path, sources, _dossiers(DOSSIER), T0 + timedelta(minutes=60))

    assert etat["sources"]["camac-permis"]["depuis"] == "2026-10-14T12:17:00Z"
    assert etat["sources"]["camac-permis"]["echecs_consecutifs"] == 0


def test_le_client_d_issues_apprend_le_passage_en_panne_puis_le_retour_une_seule_fois(tmp_path):
    sources, issues = _sources(SONDEE), IssuesFactices()
    reponses = [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503), httpx.Response(503), _dossiers(DOSSIER)]
    for i, reponse in enumerate(reponses):
        _passer(tmp_path, sources, reponse, T0 + timedelta(minutes=30 * i), issues)

    assert issues.signalements == [
        ("panne", "camac-permis", "2026-10-14T12:47:00+00:00"),
        ("retour", "camac-permis", "2026-10-14T12:47:00+00:00", "2026-10-14T14:17:00+00:00"),
    ]


NEUVE_EN_ECHEC = {
    "etat": "disponible",
    "depuis": None,
    "derniere_sonde": "2026-10-14T12:17:00Z",
    "dernier_succes": None,
    "echecs_consecutifs": 1,
    "motif": "HTTP 500",
}


def test_une_source_neuve_qui_echoue_reste_disponible_sans_depuis_ni_dernier_succes(tmp_path):
    etat, _ = _passer(tmp_path, _sources(SONDEE), httpx.Response(500))

    assert etat["sources"]["camac-permis"] == NEUVE_EN_ECHEC


def _etat_precedent(depot, version):
    panne = {
        "etat": "en_panne",
        "depuis": "2026-10-13T08:17:00Z",
        "derniere_sonde": "2026-10-14T11:47:00Z",
        "dernier_succes": "2026-10-13T07:47:00Z",
        "echecs_consecutifs": 9,
        "motif": "HTTP 500",
    }
    contenu = {"version": version, "genere": "2026-10-14T11:47:00Z", "sources": {"camac-permis": panne}}
    (depot / "etat-sources.json").write_text(json.dumps(contenu))


def test_un_etat_d_une_autre_version_fait_repartir_de_zero(tmp_path):
    _etat_precedent(tmp_path, version=2)

    etat, _ = _passer(tmp_path, _sources(SONDEE), httpx.Response(500))

    assert etat["version"] == 1
    assert etat["sources"]["camac-permis"] == NEUVE_EN_ECHEC


def test_un_etat_illisible_fait_repartir_de_zero(tmp_path):
    (tmp_path / "etat-sources.json").write_text("{pas du json")

    etat, _ = _passer(tmp_path, _sources(SONDEE), httpx.Response(500))

    assert etat["sources"]["camac-permis"] == NEUVE_EN_ECHEC


def test_l_etat_precedent_est_repris_quand_il_est_de_la_meme_version(tmp_path):
    _etat_precedent(tmp_path, version=1)

    etat, _ = _passer(tmp_path, _sources(SONDEE), httpx.Response(500))

    assert etat["sources"]["camac-permis"]["etat"] == "en_panne"
    assert etat["sources"]["camac-permis"]["depuis"] == "2026-10-13T08:17:00Z"
    assert etat["sources"]["camac-permis"]["echecs_consecutifs"] == 10


def test_une_source_sans_bloc_sonde_n_est_ni_sondee_ni_ecrite(tmp_path):
    sans_sonde = _source(id="swisstopo-fond")
    autre = _source(id="autre-source", sonde={"url": "https://autre.exemple.ch/q", "jamais_vide": False})
    _etat_precedent(tmp_path, version=1)

    etat, requetes = _passer(tmp_path, _sources(sans_sonde, autre), _dossiers(DOSSIER))

    assert [str(r.url) for r in requetes] == ["https://autre.exemple.ch/q"]
    assert list(etat["sources"]) == ["autre-source"]


def _erreur_tls():
    try:
        raise ssl.SSLCertVerificationError("certificate verify failed")
    except ssl.SSLError as e:
        try:
            raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED]") from e
        except httpx.ConnectError as erreur:
            return erreur


@pytest.mark.parametrize(
    ("reponse", "motif"),
    [
        pytest.param(httpx.Response(503), "HTTP 503", id="erreur HTTP"),
        pytest.param(httpx.Response(404), "HTTP 404", id="introuvable"),
        pytest.param(httpx.ReadTimeout("lent"), "délai dépassé", id="délai dépassé"),
        pytest.param(httpx.ConnectTimeout("lent"), "délai dépassé", id="délai de connexion dépassé"),
        pytest.param(httpx.ConnectError("refusée"), "erreur réseau", id="erreur réseau"),
        pytest.param(_erreur_tls(), "erreur TLS", id="erreur TLS"),
        pytest.param(httpx.Response(200, text="<html>maintenance</html>"), "JSON illisible", id="JSON illisible"),
        pytest.param(
            {"error": {"code": 400, "message": "Invalid query", "details": []}},
            "erreur du service (400)",
            id="erreur ArcGIS dans une réponse 200",
        ),
        pytest.param({"count": 3}, "réponse sans enregistrements", id="sans liste d'enregistrements"),
        pytest.param(_dossiers({"NO_CAMAC": 1}), "champs absents : ETAT", id="un champ absent"),
        pytest.param(_dossiers({"AUTRE": 1}), "champs absents : NO_CAMAC, ETAT", id="deux champs absents"),
        pytest.param(_dossiers(), "réponse vide", id="vide alors que jamais_vide"),
    ],
)
def test_chaque_cause_d_echec_donne_son_motif(tmp_path, reponse, motif):
    etat, _ = _passer(tmp_path, _sources(SONDEE), reponse)

    assert etat["sources"]["camac-permis"]["motif"] == motif
    assert etat["sources"]["camac-permis"]["echecs_consecutifs"] == 1


def test_une_reponse_vide_reussit_si_la_source_n_est_pas_jamais_vide(tmp_path):
    peut_etre_vide = _source(sonde={"champs": ["NO_CAMAC"], "jamais_vide": False})

    etat, _ = _passer(tmp_path, _sources(peut_etre_vide), _dossiers())

    assert etat["sources"]["camac-permis"]["echecs_consecutifs"] == 0
    assert etat["sources"]["camac-permis"]["motif"] is None


def test_les_champs_se_lisent_aussi_dans_les_proprietes_geojson(tmp_path):
    geojson = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": DOSSIER}]}

    etat, _ = _passer(tmp_path, _sources(SONDEE), geojson)

    assert etat["sources"]["camac-permis"]["motif"] is None


def _conseil(id, sonde):
    """Un conseil d'OpenParlData : voie Cron, fraîcheur `import`, sans Couverture."""
    source = {k: v for k, v in _source(id=id).items() if k != "couverture"}
    return source | {
        "nom": f"Conseil {id}",
        "voie_acces": "cron",
        "fraicheur": "import",
        "conseil": {"body_key": "VD", "donne": ["objets", "seances"]},
        "sonde": {"url": "https://api.openparldata.ch/v1/affairs/?body_key=VD", "delai": 20} | sonde,
    }


SONDE_OPENPARLDATA = {"champs": ["id", "number", "title"], "enregistrements": "data", "jamais_vide": True}


def _objets(*enregistrements):
    """Réponse d'OpenParlData : les enregistrements à plat dans `data`, avec l'enveloppe de pagination."""
    return {"meta": {"total_records": len(enregistrements), "has_more": False}, "data": list(enregistrements)}


OBJET = {"id": 1, "number": "26_INT_140", "title": "Interpellation"}


def test_la_sonde_d_un_conseil_lit_les_champs_a_plat_dans_data(tmp_path):
    etat, _ = _passer(tmp_path, _sources(_conseil("openparldata-vd", SONDE_OPENPARLDATA)), _objets(OBJET))

    assert etat["sources"]["openparldata-vd"]["etat"] == "disponible"
    assert etat["sources"]["openparldata-vd"]["motif"] is None


@pytest.mark.parametrize(
    ("reponse", "motif"),
    [
        pytest.param(_objets({"id": 1, "number": "26_INT_140"}), "champs absents : title", id="un champ absent"),
        pytest.param(_objets(), "réponse vide", id="vide"),
        pytest.param(_dossiers(DOSSIER), "réponse sans enregistrements", id="features au lieu de data"),
    ],
)
def test_la_sonde_d_un_conseil_echoue_sans_ses_champs_ou_sans_enregistrement(tmp_path, reponse, motif):
    etat, _ = _passer(tmp_path, _sources(_conseil("openparldata-vd", SONDE_OPENPARLDATA)), reponse)

    assert etat["sources"]["openparldata-vd"]["motif"] == motif


def test_un_passage_sonde_les_trois_conseils_de_sources_json_et_les_donne_disponibles(tmp_path):
    sources = lire_sources(RACINE / "sources.json")
    reponses = {"affairs": _objets(OBJET), "meetings": _objets({"id": 7, "begin_date": "2026-10-06T18:00:00"})}

    def traiter(requete):
        if requete.url.host != "api.openparldata.ch":
            return httpx.Response(200, json=_dossiers(DOSSIER))
        assert requete.url.params["client"] == "vigie-vaud"
        return httpx.Response(200, json=reponses[requete.url.path.split("/")[2]])

    with httpx.Client(transport=httpx.MockTransport(traiter)) as client:
        passage(tmp_path, sources, client, horloge=lambda: T0, issues=IssuesFactices())

    etat = json.loads((tmp_path / "etat-sources.json").read_text())
    conseils = {id: e for id, e in etat["sources"].items() if id.startswith("openparldata-")}
    assert {id: (e["etat"], e["motif"]) for id, e in conseils.items()} == {
        "openparldata-vd": ("disponible", None),
        "openparldata-5586": ("disponible", None),
        "openparldata-5938": ("disponible", None),
    }


def test_la_sonde_est_une_seule_requete_avec_son_delai_et_le_user_agent_du_depot(tmp_path):
    lente = _source(sonde={"delai": 7})

    _, requetes = _passer(tmp_path, _sources(lente), _dossiers(DOSSIER))

    (requete,) = requetes
    assert requete.headers["User-Agent"] == "VigieVaud-sonde (+https://github.com/Louni-M/vigie-vaud)"
    assert requete.extensions["timeout"] == {"connect": 7, "read": 7, "write": 7, "pool": 7}


def test_un_passage_ne_conserve_aucune_donnee_de_la_source(tmp_path):
    _passer(tmp_path, _sources(SONDEE), _dossiers({"NO_CAMAC": 987654, "ETAT": "Dossier secret"}))

    ecrits = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*") if p.is_file())
    assert ecrits == [
        "etat-sources.json",
        "schema/corrections.schema.json",
        "schema/enveloppe.schema.json",
        "schema/etat-sources.schema.json",
        "schema/fil-conseils.schema.json",
        "schema/import-conseils.schema.json",
        "schema/index-conseils.schema.json",
        "schema/liste-objets.schema.json",
        "schema/liste-seances.schema.json",
        "schema/objet.schema.json",
        "schema/rattachements-commune.schema.json",
        "schema/seance.schema.json",
        "schema/sources.schema.json",
    ]
    assert "987654" not in (tmp_path / "etat-sources.json").read_text()


# --- Issues `panne-source` dans le dépôt de données (ticket #32), contre un GitHub factice ----------------------

DEPOT_DONNEES = "Louni-M/vigie-vaud-donnees"
API = f"https://api.github.com/repos/{DEPOT_DONNEES}/issues"
JETON = "jeton-du-depot"


class GitHubFactice:
    """Transport factice de l'API REST des issues : il tient en mémoire les issues du dépôt de données."""

    def __init__(self, *ouvertes):
        self.issues = []
        self.requetes = []
        self.hors_service = False
        for titre, etiquettes in ouvertes:
            self._creer({"title": titre, "body": "", "labels": etiquettes})

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self._traiter))

    def _creer(self, corps):
        issue = {
            "number": len(self.issues) + 1,
            "title": corps["title"],
            "body": corps.get("body"),
            "labels": [{"name": n} for n in corps.get("labels", [])],
            "state": "open",
            "commentaires": [],
        }
        self.issues.append(issue)
        return issue

    def _traiter(self, requete):
        self.requetes.append(requete)
        if self.hors_service:
            return httpx.Response(503, json={"message": "Service Unavailable"})
        if requete.headers.get("Authorization") != f"Bearer {JETON}":
            return httpx.Response(401, json={"message": "Bad credentials"})
        url = str(requete.url.copy_with(query=None))
        corps = json.loads(requete.content) if requete.content else None
        if url == API and requete.method == "GET":
            etiquette, etat = requete.url.params["labels"], requete.url.params["state"]
            return httpx.Response(
                200,
                json=[i for i in self.issues if i["state"] == etat and etiquette in [e["name"] for e in i["labels"]]],
            )
        if url == API and requete.method == "POST":
            return httpx.Response(201, json=self._creer(corps))
        for issue in self.issues:
            if url == f"{API}/{issue['number']}/comments" and requete.method == "POST":
                issue["commentaires"].append(corps["body"])
                return httpx.Response(201, json={"body": corps["body"]})
            if url == f"{API}/{issue['number']}" and requete.method == "PATCH":
                issue["state"] = corps["state"]
                return httpx.Response(200, json=issue)
        return httpx.Response(404, json={"message": "Not Found"})


def _passer_avec_github(depot, github, reponses, minutes=None):
    """Des passages, toutes les 30 minutes depuis T0 ou aux `minutes` données, avec le client d'issues GitHub
    branché sur le GitHub factice."""
    with github.client() as client:
        issues = IssuesGitHub(client, DEPOT_DONNEES, JETON)
        for i, reponse in enumerate(reponses):
            heure = T0 + timedelta(minutes=30 * i if minutes is None else minutes[i])
            _passer(depot, _sources(SONDEE), reponse, heure, issues)


def test_le_passage_en_panne_ouvre_une_seule_issue_panne_source_titree_d_apres_la_source(tmp_path):
    github = GitHubFactice()

    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER)] + [httpx.Response(503)] * 4)

    (issue,) = github.issues
    assert issue["title"] == "Panne : Permis CAMAC (MapServer/537)"
    assert [e["name"] for e in issue["labels"]] == ["panne-source"]
    assert issue["state"] == "open"


def test_aucune_issue_n_est_ouverte_si_une_issue_panne_source_est_deja_ouverte_pour_cette_source(tmp_path):
    github = GitHubFactice(
        ("Panne : Permis CAMAC (MapServer/537)", ["panne-source"]),
        ("Panne : Autre source", ["panne-source"]),
    )

    _passer_avec_github(tmp_path, github, [httpx.Response(503)] * 3)

    assert [(i["title"], i["state"]) for i in github.issues] == [
        ("Panne : Permis CAMAC (MapServer/537)", "open"),
        ("Panne : Autre source", "open"),
    ]


def test_une_issue_du_meme_titre_sans_l_etiquette_panne_source_n_empeche_pas_d_ouvrir_la_sienne(tmp_path):
    github = GitHubFactice(("Panne : Permis CAMAC (MapServer/537)", []))

    _passer_avec_github(tmp_path, github, [httpx.Response(503)] * 2)

    assert [[e["name"] for e in i["labels"]] for i in github.issues] == [[], ["panne-source"]]


def test_au_retour_l_issue_est_commentee_avec_la_duree_de_la_panne_puis_fermee(tmp_path):
    github = GitHubFactice()
    # Première sonde en échec à 12:47, retour à 15:57.
    reponses = [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503), _dossiers(DOSSIER)]

    _passer_avec_github(tmp_path, github, reponses, minutes=[0, 30, 60, 220])

    (issue,) = github.issues
    assert issue["commentaires"] == ["Permis CAMAC (MapServer/537) est de nouveau disponible après 3 h 10."]
    assert issue["state"] == "closed"
    assert [(r.method, r.url.path) for r in github.requetes[-2:]] == [
        ("POST", f"/repos/{DEPOT_DONNEES}/issues/1/comments"),
        ("PATCH", f"/repos/{DEPOT_DONNEES}/issues/1"),
    ]


@pytest.mark.parametrize(
    ("minutes", "texte"),
    [(40, "40 min"), (120, "2 h"), (125, "2 h 05"), (26 * 60 + 30, "26 h 30")],
)
def test_la_duree_de_la_panne_se_lit_en_heures_et_minutes(tmp_path, minutes, texte):
    github = GitHubFactice()
    reponses = [httpx.Response(503), httpx.Response(503), _dossiers(DOSSIER)]

    _passer_avec_github(tmp_path, github, reponses, minutes=[0, 30, minutes])

    assert github.issues[0]["commentaires"] == [
        f"Permis CAMAC (MapServer/537) est de nouveau disponible après {texte}."
    ]


def test_l_issue_ouverte_dit_depuis_quand_et_pourquoi_la_sonde_echoue(tmp_path):
    github = GitHubFactice()

    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503)])

    assert github.issues[0]["body"] == (
        "La sonde de Permis CAMAC (MapServer/537) échoue depuis le 2026-10-14 à 12:47 UTC (HTTP 503).\n\n"
        "Le cron commentera puis fermera cette issue au retour de la source."
    )


def test_un_retour_sans_issue_ouverte_ne_modifie_rien(tmp_path):
    _etat_precedent(tmp_path, version=1)
    github = GitHubFactice(("Panne : Autre source", ["panne-source"]))

    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER)])

    assert [r.method for r in github.requetes] == ["GET"]
    assert github.issues[0]["state"] == "open"


def test_une_panne_de_l_api_github_n_empeche_pas_d_ecrire_l_etat(tmp_path, capsys):
    github = GitHubFactice()
    github.hors_service = True

    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503)])

    etat = json.loads((tmp_path / "etat-sources.json").read_text())
    assert etat["sources"]["camac-permis"]["etat"] == "en_panne"
    assert "503" in capsys.readouterr().err


def test_une_issue_que_l_api_n_a_pas_laisse_ouvrir_est_ouverte_au_passage_suivant(tmp_path):
    github = GitHubFactice()
    github.hors_service = True
    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503)])

    github.hors_service = False
    _passer_avec_github(tmp_path, github, [httpx.Response(503)], minutes=[90])

    (issue,) = github.issues
    assert issue["state"] == "open"
    assert "échoue depuis le 2026-10-14 à 12:47 UTC" in issue["body"]


def test_une_issue_que_l_api_n_a_pas_laisse_fermer_est_fermee_au_passage_suivant(tmp_path):
    github = GitHubFactice()
    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER), httpx.Response(503), httpx.Response(503)])
    github.hors_service = True
    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER)], minutes=[90])

    github.hors_service = False
    _passer_avec_github(tmp_path, github, [_dossiers(DOSSIER)], minutes=[120])

    (issue,) = github.issues
    assert issue["state"] == "closed"
    assert issue["commentaires"] == [
        "Permis CAMAC (MapServer/537) est de nouveau disponible depuis le 2026-10-14 à 13:47 UTC."
    ]


def test_un_seul_echec_ne_ferme_pas_l_issue_d_une_source_en_panne(tmp_path):
    github = GitHubFactice(("Panne : Permis CAMAC (MapServer/537)", ["panne-source"]))

    _passer_avec_github(tmp_path, github, [httpx.Response(503)])

    assert github.issues[0]["state"] == "open"


ENV_DU_WORKFLOW = {"GITHUB_TOKEN": JETON, "GITHUB_REPOSITORY": DEPOT_DONNEES}


def _passer_en_panne(depot, issues):
    for i in range(2):
        _passer(depot, _sources(SONDEE), httpx.Response(503), T0 + timedelta(minutes=30 * i), issues)


def test_en_mode_local_sans_push_les_issues_sont_affichees_et_rien_n_est_demande_a_github(tmp_path, capsys):
    github = GitHubFactice()

    with github.client() as client:
        _passer_en_panne(tmp_path, client_issues(sans_push=True, environ=ENV_DU_WORKFLOW, client=client))

    assert github.requetes == []
    assert "Panne : Permis CAMAC (MapServer/537)" in capsys.readouterr().out


def test_avec_push_les_issues_s_ouvrent_dans_le_depot_du_workflow_avec_son_github_token(tmp_path):
    github = GitHubFactice()

    with github.client() as client:
        _passer_en_panne(tmp_path, client_issues(sans_push=False, environ=ENV_DU_WORKFLOW, client=client))

    assert [i["title"] for i in github.issues] == ["Panne : Permis CAMAC (MapServer/537)"]


def test_avec_push_sans_github_token_le_passage_refuse_de_partir():
    with httpx.Client() as client, pytest.raises(SystemExit, match="GITHUB_TOKEN"):
        client_issues(sans_push=False, environ={"GITHUB_REPOSITORY": DEPOT_DONNEES}, client=client)
