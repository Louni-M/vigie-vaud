"""Un passage du cron (ADR 0005 et 0014) : sondes des sources et état des sources.

Le passage relit `sources.json` et l'état précédent dans un clone du dépôt de données, sonde chaque source qui a
un bloc `sonde`, écrit `etat-sources.json`, copie `schema/`, puis committe (l'historique sert d'archive) et pousse.
Quand une source passe en panne ou revient, il ouvre ou ferme son issue `panne-source` dans le dépôt de données.

En local, contre un clone du dépôt de données (depuis `pipeline/`) :

    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push

`--sans-push` écrit l'état et committe sans pousser, et affiche les issues au lieu de les ouvrir. En production, le
workflow réutilisable `.github/workflows/cron.yml` lance la même commande sans cette option, avec le `GITHUB_TOKEN`
et le `GITHUB_REPOSITORY` du dépôt de données dans l'environnement, puis publie le dépôt sur Pages.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import ssl
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import ValidationError

from schema import DOSSIER_SCHEMA, RACINE, EtatSource, EtatSources, FichierSources, Sonde, Source, lire_sources

FICHIER_ETAT = "etat-sources.json"
ECHECS_AVANT_PANNE = 2
# L'adresse du dépôt vient de `config.json`, puisque le dépôt est renommé à la fin de J0.
USER_AGENT = f"VigieVaud-sonde (+{json.loads((RACINE / 'config.json').read_text())['depot']})"


class ClientIssues(Protocol):
    """Ce que le passage signale des issues `panne-source` du dépôt de données : `IssuesGitHub` en production,
    `IssuesAffichees` sans push."""

    def panne(self, source: Source, etat: EtatSource) -> None:
        """La source vient de passer en panne ; `etat.depuis` est l'heure de la première sonde en échec."""

    def retour(self, source: Source, panne: EtatSource, etat: EtatSource) -> None:
        """La source en panne depuis `panne.depuis` est de nouveau disponible depuis `etat.depuis`."""


class IssuesAffichees:
    """Client d'issues du mode local : il affiche ce qu'il signalerait, sans rien ouvrir."""

    def panne(self, source: Source, etat: EtatSource) -> None:
        print(f"Panne : {source.nom} (depuis {etat.depuis:%Y-%m-%d %H:%M}Z, {etat.motif})")

    def retour(self, source: Source, panne: EtatSource, etat: EtatSource) -> None:
        print(f"Retour : {source.nom} (en panne depuis {panne.depuis:%Y-%m-%d %H:%M}Z)")


ETIQUETTE_PANNE = "panne-source"


class IssuesGitHub:
    """Client d'issues du cron : il ouvre et ferme les issues `panne-source` du dépôt de données `depot`
    (« propriétaire/nom ») avec le `GITHUB_TOKEN` de ce dépôt (ADR 0014)."""

    def __init__(self, client: httpx.Client, depot: str, jeton: str) -> None:
        self._client = client
        self._api = f"https://api.github.com/repos/{depot}/issues"
        self._entetes = {
            "Authorization": f"Bearer {jeton}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }

    def panne(self, source: Source, etat: EtatSource) -> None:
        if self._ouvertes(source):
            return
        corps = (
            f"La sonde de {source.nom} échoue depuis le {etat.depuis:%Y-%m-%d à %H:%M} UTC ({etat.motif}).\n\n"
            "Le cron commentera puis fermera cette issue au retour de la source."
        )
        self._requete(
            "POST", self._api, json={"title": titre_panne(source), "body": corps, "labels": [ETIQUETTE_PANNE]}
        )

    def retour(self, source: Source, panne: EtatSource, etat: EtatSource) -> None:
        commentaire = f"{source.nom} est de nouveau disponible après {duree(etat.depuis - panne.depuis)}."
        for numero in self._ouvertes(source):
            self._requete("POST", f"{self._api}/{numero}/comments", json={"body": commentaire})
            self._requete("PATCH", f"{self._api}/{numero}", json={"state": "closed", "state_reason": "completed"})

    def _ouvertes(self, source: Source) -> list[int]:
        """Numéros des issues `panne-source` ouvertes pour `source`, retrouvées par leur titre."""
        params = {"labels": ETIQUETTE_PANNE, "state": "open", "per_page": 100}
        issues = self._requete("GET", self._api, params=params).json()
        return [i["number"] for i in issues if "pull_request" not in i and i["title"] == titre_panne(source)]

    def _requete(self, methode: str, url: str, **options) -> httpx.Response:
        reponse = self._client.request(methode, url, headers=self._entetes, **options)
        reponse.raise_for_status()
        return reponse


def client_issues(sans_push: bool, environ: Mapping[str, str], client: httpx.Client) -> ClientIssues:
    """Sans push, les issues sont seulement affichées. Avec push, elles s'ouvrent dans le dépôt de données avec son
    `GITHUB_TOKEN` : dans le workflow, `GITHUB_REPOSITORY` désigne ce dépôt, qui porte le déclencheur."""
    if sans_push:
        return IssuesAffichees()
    manquantes = [v for v in ("GITHUB_TOKEN", "GITHUB_REPOSITORY") if not environ.get(v)]
    if manquantes:
        raise SystemExit(f"{' et '.join(manquantes)} absent(s) : lancer le passage avec --sans-push hors du workflow")
    return IssuesGitHub(client, environ["GITHUB_REPOSITORY"], environ["GITHUB_TOKEN"])


def titre_panne(source: Source) -> str:
    return f"Panne : {source.nom}"


def duree(ecart: timedelta) -> str:
    """Durée d'une panne à la minute : « 3 h 10 », « 2 h », « 40 min »."""
    heures, minutes = divmod(int(ecart.total_seconds()) // 60, 60)
    if not heures:
        return f"{minutes} min"
    return f"{heures} h {minutes:02d}" if minutes else f"{heures} h"


def passage(
    depot: Path,
    sources: FichierSources,
    client: httpx.Client,
    horloge: Callable[[], datetime],
    issues: ClientIssues,
) -> EtatSources:
    """Sonde chaque source qui a un bloc `sonde`, puis écrit `etat-sources.json` et copie `schema/` dans `depot`,
    un clone du dépôt de données. L'état précédent est relu dans ce clone ; absent, illisible ou d'une autre
    version, le passage repart de zéro. Le commit et le push sont l'affaire de l'appelant."""
    genere = _a_la_seconde(horloge())
    precedent = _lire_etat(depot / FICHIER_ETAT)
    etats: dict[str, EtatSource] = {}
    for source in sources.sources:
        if source.sonde is None:
            continue
        heure = _a_la_seconde(horloge())
        etats[source.id] = _suivant(precedent.get(source.id), heure, sonder(client, source.sonde))
    etat = EtatSources(version=1, genere=genere, sources=etats)
    (depot / FICHIER_ETAT).write_text(etat.model_dump_json(indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(depot / "schema", ignore_errors=True)
    shutil.copytree(DOSSIER_SCHEMA, depot / "schema")

    for source in sources.sources:
        avant, apres = precedent.get(source.id), etats.get(source.id)
        if apres is None:
            continue
        if apres.etat == "en_panne" and (avant is None or avant.etat != "en_panne"):
            issues.panne(source, apres)
        elif apres.etat == "disponible" and avant is not None and avant.etat == "en_panne":
            issues.retour(source, avant, apres)
    return etat


def _a_la_seconde(heure: datetime) -> datetime:
    return heure.astimezone(UTC).replace(microsecond=0)


def _lire_etat(chemin: Path) -> dict[str, EtatSource]:
    try:
        return EtatSources.model_validate_json(chemin.read_bytes()).sources
    except (FileNotFoundError, ValidationError):
        return {}


def sonder(client: httpx.Client, sonde: Sonde) -> str | None:
    """Envoie la sonde : une seule requête, sans nouvel essai. Renvoie `None` si elle réussit, sinon le motif court
    de son échec. Rien de la réponse n'est conservé (DCG 8401)."""
    try:
        reponse = client.get(sonde.url, headers={"User-Agent": USER_AGENT}, timeout=sonde.delai)
    except httpx.TimeoutException:
        return "délai dépassé"
    except httpx.RequestError as e:
        return "erreur TLS" if _cause_tls(e) else "erreur réseau"
    if not reponse.is_success:
        return f"HTTP {reponse.status_code}"
    try:
        corps = reponse.json()
    except ValueError:
        return "JSON illisible"
    if not isinstance(corps, dict):
        return "réponse sans enregistrements"
    # ArcGIS répond 200 avec un objet `error` quand la requête est refusée.
    if isinstance(corps.get("error"), dict):
        return f"erreur du service ({corps['error'].get('code', '?')})"
    enregistrements = corps.get("features")
    if not isinstance(enregistrements, list):
        return "réponse sans enregistrements"
    if not enregistrements:
        return "réponse vide" if sonde.jamais_vide else None
    for enregistrement in enregistrements:
        absents = [c for c in sonde.champs if c not in _champs(enregistrement)]
        if absents:
            return "champs absents : " + ", ".join(absents)
    return None


def _champs(enregistrement: object) -> dict:
    """Champs d'un enregistrement : `attributes` (JSON ArcGIS) ou `properties` (GeoJSON)."""
    if not isinstance(enregistrement, dict):
        return {}
    for cle in ("attributes", "properties"):
        if isinstance(enregistrement.get(cle), dict):
            return enregistrement[cle]
    return {}


def _cause_tls(erreur: BaseException) -> bool:
    while erreur is not None:
        if isinstance(erreur, ssl.SSLError):
            return True
        erreur = erreur.__cause__ or erreur.__context__
    return False


def _suivant(avant: EtatSource | None, heure: datetime, motif: str | None) -> EtatSource:
    if avant is None:
        avant = EtatSource(
            etat="disponible",
            depuis=None,
            derniere_sonde=heure,
            dernier_succes=None,
            echecs_consecutifs=0,
            motif=None,
        )
    if motif is None:
        retour = avant.etat == "en_panne" or avant.depuis is None
        return EtatSource(
            etat="disponible",
            depuis=heure if retour else avant.depuis,
            derniere_sonde=heure,
            dernier_succes=heure,
            echecs_consecutifs=0,
            motif=None,
        )
    echecs = avant.echecs_consecutifs + 1
    en_panne = echecs >= ECHECS_AVANT_PANNE
    if avant.etat == "en_panne":
        depuis = avant.depuis
    elif en_panne:
        # Avec 2 échecs avant la panne, la sonde précédente était le premier de la série : la panne part de son heure.
        depuis = avant.derniere_sonde if avant.echecs_consecutifs else heure
    else:
        depuis = avant.depuis
    return EtatSource(
        etat="en_panne" if en_panne else "disponible",
        depuis=depuis,
        derniere_sonde=heure,
        dernier_succes=avant.dernier_succes,
        echecs_consecutifs=echecs,
        motif=motif,
    )


# --- Commit et push (hors du point de test : l'option sans push sert de vérification locale) -------------------

NOUVEAUX_ESSAIS_PUSH = 2


def _git(depot: Path, *args: str, verifier: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(depot), *args], check=verifier, text=True)


def committer(depot: Path, etat: EtatSources) -> None:
    _git(depot, "add", "--all", "--", FICHIER_ETAT, "schema")
    _git(depot, "commit", "--quiet", "-m", f"Passage du cron du {etat.genere:%Y-%m-%d %H:%M}Z")


def pousser(depot: Path) -> None:
    """Pousse ; si le push est refusé, `pull --rebase` puis nouvel essai, deux fois au plus. Au-delà, le passage
    échoue et le suivant repart de l'état relu."""
    for essai in range(NOUVEAUX_ESSAIS_PUSH + 1):
        if _git(depot, "push", "--quiet", verifier=False).returncode == 0:
            return
        if essai == NOUVEAUX_ESSAIS_PUSH:
            break
        print(f"Push refusé : pull --rebase puis nouvel essai ({essai + 1}/{NOUVEAUX_ESSAIS_PUSH})", file=sys.stderr)
        if _git(depot, "pull", "--rebase", "--quiet", verifier=False).returncode != 0:
            _git(depot, "rebase", "--abort", verifier=False)
            break
    raise SystemExit("Push refusé : le passage échoue, le suivant repartira de l'état relu.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Lance un passage du cron contre un clone du dépôt de données.")
    parser.add_argument("--depot", type=Path, required=True, help="clone local du dépôt de données")
    parser.add_argument("--sources", type=Path, default=RACINE / "sources.json", help="déclaration des sources")
    parser.add_argument("--sans-push", action="store_true", help="écrire l'état et committer sans pousser")
    args = parser.parse_args(argv)

    depot = args.depot.resolve()
    if not (depot / ".git").exists():
        raise SystemExit(f"{depot} n'est pas un clone git du dépôt de données")
    with httpx.Client() as client, httpx.Client(timeout=30) as client_github:
        issues = client_issues(args.sans_push, os.environ, client_github)
        etat = passage(depot, lire_sources(args.sources), client, lambda: datetime.now(UTC), issues)
    for id_source, e in etat.sources.items():
        print(f"{id_source} : {e.etat}" + (f" ({e.motif}, {e.echecs_consecutifs} échec(s))" if e.motif else ""))

    committer(depot, etat)
    if args.sans_push:
        print("Commit fait, sans push (--sans-push).")
        return
    pousser(depot)


if __name__ == "__main__":
    main()
