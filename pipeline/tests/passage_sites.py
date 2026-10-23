"""Ce que partagent les tests des sites communaux, qui passent tous par le passage du cron (spec de J3, « Décisions
de test ») : les sources de test, l'échantillon i-web servi par le faux réseau (`faux_sites.Reseau`) et ses retouches,
le faux OpenParlData du même passage, et `_passer`, le seul seam.

Les noms gardent leur tiret bas initial : ce sont des aides de test, importées par chaque fichier de tests des sites.
"""

import html
import json
import re
from datetime import UTC, datetime, timedelta

import httpx

from cron import passage
from faux_openparldata import Affaire, Monde
from faux_sites import Page, Reseau, echantillon
from schema import FichierSources
from test_cron import IssuesFactices

# 07:17 à Lausanne, le jour où l'échantillon a été enregistré : la fenêtre du passage part du 23 avril 2026.
T0 = datetime(2026, 10, 23, 5, 17, tzinfo=UTC)
S = timedelta(seconds=1)
PREVERENGES = "https://www.preverenges.ch"
BLONAY = "https://www.blonay-saint-legier.ch"
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


def _passer(depot, horloge, reseau, sources=SOURCES, *, monde=None, heure=None, issues=None, **options):
    """Un passage du cron, le seul seam des tests des sites (spec de J3, « Décisions de test ») : `cron.passage` sur
    le dépôt de données `depot`, avec un seul transport qui sert les sites de `reseau` et, pour tout autre hôte, le
    faux OpenParlData de `monde` (par défaut, `_monde`), la résolution d'adresse du faux réseau, et une attente qui
    fait avancer l'horloge, mise d'abord à `heure` s'il y en a une. `options` : celles de `passage` (rattrapages).
    Rend le client d'issues, factice par défaut."""
    horloge.heure = heure or horloge.heure
    monde = monde if monde is not None else _monde(horloge)
    issues = issues if issues is not None else IssuesFactices()
    with httpx.Client(transport=reseau.transport(repli=monde.transport())) as client:
        passage(
            depot,
            sources,
            client,
            horloge=horloge,
            issues=issues,
            attendre=horloge.attendre,
            resoudre=reseau.resoudre,
            **options,
        )
    return issues


def _lire(depot, chemin):
    return json.loads((depot / chemin).read_text(encoding="utf-8"))
