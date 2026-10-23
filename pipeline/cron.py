"""Un passage du cron (ADR 0005, 0014 et 0015) : sondes et état des sources, puis import quotidien des conseils.

Le passage relit `sources.json` et l'état précédent dans un clone du dépôt de données, sonde chaque source qui a
un bloc `sonde`, écrit `etat-sources.json`, copie `schema/`, importe les conseils dus (`conseils.py`), puis committe
(l'historique sert d'archive) et pousse. Il ouvre l'issue `panne-source` d'une source en panne et ferme celle d'une
source disponible, dans le dépôt de données. Une erreur de l'API des issues ne fait pas échouer le passage : l'état
est tout de même écrit et publié, et le passage suivant, qui compare de nouveau l'état aux issues ouvertes, refait
ce qui a manqué.

Les sondes tournent à chaque passage (toutes les 30 minutes). Chaque conseil, lui, s'importe une fois par jour, au
premier passage après 7 h à Lausanne, depuis le jour de son dernier import réussi ; un import en échec est refait au
passage suivant. Quand aucun import d'un conseil n'a réussi depuis plus de 24 h, ou dès le premier échec d'un
conseil qui n'a jamais été importé, le passage ouvre son issue `import-conseils`, qu'il commente et ferme au premier
import réussi. Seules les sondes mettent une source en panne :
un import en échec ne touche pas à l'état des sources.

En local, contre un clone du dépôt de données (depuis `pipeline/`) :

    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push
    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push --rattrapage

`--sans-push` écrit l'état et committe sans pousser, et affiche les issues au lieu de les ouvrir. `--rattrapage`
importe tous les conseils depuis tout l'historique, à toute heure (le même chemin, `depuis` vide). En production,
le workflow réutilisable `.github/workflows/cron.yml` lance la même commande sans `--sans-push`, avec le
`GITHUB_TOKEN` et le `GITHUB_REPOSITORY` du dépôt de données dans l'environnement, puis publie le dépôt sur Pages ;
un lancement manuel (`workflow_dispatch`) avec l'entrée `rattrapage` y ajoute `--rattrapage`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from datetime import time as time_du_jour
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from conseils import OpenParlData, importer_conseils, lire_imports
from robot_communal import Robot
from schema import DOSSIER_SCHEMA, RACINE, EtatSource, EtatSources, FichierSources, Sonde, Source, lire_sources

FICHIER_ETAT = "etat-sources.json"
ECHECS_AVANT_PANNE = 2
# L'adresse du dépôt vient de `config.json`, puisque le dépôt est renommé à la fin de J0.
USER_AGENT = f"VigieVaud-sonde (+{json.loads((RACINE / 'config.json').read_text())['depot']})"


class ClientIssues(Protocol):
    """Les issues `panne-source` du dépôt de données : `IssuesGitHub` en production, `IssuesAffichees` sans push.
    Une erreur de l'API lève `httpx.HTTPError`."""

    def signalees(self, sources: list[Source]) -> set[str] | None:
        """Identifiants des `sources` qui ont une issue `panne-source` ouverte, ou `None` pour un client qui ne voit
        pas les issues : le passage les suppose alors ouvertes pour les sources en panne dans l'état relu."""

    def panne(self, source: Source, etat: EtatSource) -> None:
        """La source est en panne sans issue ouverte ; `etat.depuis` est l'heure de la première sonde en échec."""

    def retour(self, source: Source, panne: EtatSource | None, etat: EtatSource) -> None:
        """La source qui a une issue ouverte est disponible depuis `etat.depuis`. `panne` est son état en panne
        quand elle revient à ce passage, `None` quand son retour date d'un passage précédent."""

    def imports_signales(self, conseils: list[Source]) -> set[str] | None:
        """Identifiants des `conseils` qui ont une issue `import-conseils` ouverte, ou `None` pour un client qui ne
        voit pas les issues : le passage lui signale alors chaque conseil en échec, à chaque passage, et le retour
        de ceux qui étaient en échec avant lui."""

    def import_en_echec(self, conseil: Source, dernier: datetime | None) -> None:
        """Aucun import du conseil n'a réussi depuis plus de 24 h, sans issue ouverte ; `dernier` est l'heure du
        dernier import réussi, `None` pour un conseil qui n'a encore jamais été importé."""

    def import_retour(self, conseil: Source, dernier: datetime) -> None:
        """Le conseil qui a une issue ouverte a de nouveau été importé, à `dernier`."""


class IssuesAffichees:
    """Client d'issues du mode local : il affiche ce qu'il signalerait, sans rien ouvrir."""

    def signalees(self, sources: list[Source]) -> None:
        return None

    def panne(self, source: Source, etat: EtatSource) -> None:
        print(f"Panne : {source.nom} (depuis {etat.depuis:%Y-%m-%d %H:%M}Z, {etat.motif})")

    def retour(self, source: Source, panne: EtatSource | None, etat: EtatSource) -> None:
        print(f"Retour : {source.nom} (disponible depuis {etat.depuis:%Y-%m-%d %H:%M}Z)")

    def imports_signales(self, conseils: list[Source]) -> None:
        return None

    def import_en_echec(self, conseil: Source, dernier: datetime | None) -> None:
        reussi = f"dernier import réussi {dernier:%Y-%m-%d %H:%M}Z" if dernier else "aucun import réussi"
        print(f"{titre_import(conseil)} ({reussi})")

    def import_retour(self, conseil: Source, dernier: datetime) -> None:
        print(f"Import de retour : {conseil.nom} (importé {dernier:%Y-%m-%d %H:%M}Z)")


ETIQUETTE_PANNE = "panne-source"
ETIQUETTE_IMPORT = "import-conseils"


class IssuesGitHub:
    """Client d'issues du cron : il ouvre et ferme les issues `panne-source` et `import-conseils` du dépôt de
    données `depot` (« propriétaire/nom ») avec le `GITHUB_TOKEN` de ce dépôt (ADR 0014)."""

    def __init__(self, client: httpx.Client, depot: str, jeton: str) -> None:
        self._client = client
        self._api = f"https://api.github.com/repos/{depot}/issues"
        self._entetes = {
            "Authorization": f"Bearer {jeton}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": USER_AGENT,
        }

    def signalees(self, sources: list[Source]) -> set[str]:
        titres = {i["title"] for i in self._issues_ouvertes(ETIQUETTE_PANNE)}
        return {s.id for s in sources if titre_panne(s) in titres}

    def panne(self, source: Source, etat: EtatSource) -> None:
        corps = (
            f"La sonde de {source.nom} échoue depuis le {etat.depuis:%Y-%m-%d à %H:%M} UTC ({etat.motif}).\n\n"
            "Le cron commentera puis fermera cette issue au retour de la source."
        )
        self._requete(
            "POST", self._api, json={"title": titre_panne(source), "body": corps, "labels": [ETIQUETTE_PANNE]}
        )

    def retour(self, source: Source, panne: EtatSource | None, etat: EtatSource) -> None:
        if panne is not None:
            commentaire = f"{source.nom} est de nouveau disponible après {duree(etat.depuis - panne.depuis)}."
        else:
            commentaire = f"{source.nom} est de nouveau disponible depuis le {etat.depuis:%Y-%m-%d à %H:%M} UTC."
        self._fermer(ETIQUETTE_PANNE, titre_panne(source), commentaire)

    def imports_signales(self, conseils: list[Source]) -> set[str]:
        titres = {i["title"] for i in self._issues_ouvertes(ETIQUETTE_IMPORT)}
        return {s.id for s in conseils if titre_import(s) in titres}

    def import_en_echec(self, conseil: Source, dernier: datetime | None) -> None:
        if dernier is None:
            constat = f"Aucun import de {conseil.nom} n'a encore réussi."
        else:
            constat = f"Aucun import de {conseil.nom} n'a réussi depuis le {dernier:%Y-%m-%d à %H:%M} UTC."
        corps = (
            f"{constat} Le cron le réessaie à chaque passage ; le journal du workflow donne la cause de chaque échec.\n\n"
            "La source n'est pas en panne pour autant : le site garde les données déjà importées et seul le badge "
            "de fraîcheur vieillit. Le cron commentera puis fermera cette issue au premier import réussi."
        )
        self._requete(
            "POST", self._api, json={"title": titre_import(conseil), "body": corps, "labels": [ETIQUETTE_IMPORT]}
        )

    def import_retour(self, conseil: Source, dernier: datetime) -> None:
        commentaire = f"{conseil.nom} est de nouveau importé : import réussi le {dernier:%Y-%m-%d à %H:%M} UTC."
        self._fermer(ETIQUETTE_IMPORT, titre_import(conseil), commentaire)

    def _fermer(self, etiquette: str, titre: str, commentaire: str) -> None:
        """Commente puis ferme les issues ouvertes `etiquette` de ce titre."""
        for numero in [i["number"] for i in self._issues_ouvertes(etiquette) if i["title"] == titre]:
            self._requete("POST", f"{self._api}/{numero}/comments", json={"body": commentaire})
            self._requete("PATCH", f"{self._api}/{numero}", json={"state": "closed", "state_reason": "completed"})

    def _issues_ouvertes(self, etiquette: str) -> list[dict]:
        params = {"labels": etiquette, "state": "open", "per_page": 100}
        issues = self._requete("GET", self._api, params=params).json()
        return [i for i in issues if "pull_request" not in i]

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


def titre_import(conseil: Source) -> str:
    return f"Import en échec : {conseil.nom}"


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
    attendre: Callable[[float], None] = time.sleep,
    rattrapage: bool = False,
    resoudre: Callable[[str], str] = socket.gethostbyname,
) -> EtatSources:
    """Sonde chaque source qui a un bloc `sonde`, puis écrit `etat-sources.json` et copie `schema/` dans `depot`,
    un clone du dépôt de données. L'état précédent est relu dans ce clone ; absent, illisible ou d'une autre
    version, le passage repart de zéro. Les issues sont ensuite accordées à l'état écrit ; une erreur de leur API
    est affichée sans faire échouer le passage. Vient ensuite l'import des conseils dus (`importer_les_conseils`),
    qui ne touche pas à l'état des sources. Les sites des communes sont lus par un robot communal, un seul pour tout
    le passage, sur le même client HTTP, avec la même horloge et la même attente, et `resoudre` pour le /24 de chaque
    hôte. Le commit et le push sont l'affaire de l'appelant."""
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

    try:
        _accorder_issues(issues, [s for s in sources.sources if s.id in etats], precedent, etats)
    except httpx.HTTPError as e:
        print(f"Issues panne-source non mises à jour, le passage suivant réessaiera : {e}", file=sys.stderr)

    opd = OpenParlData(client, horloge, attendre)
    robot = Robot(client, horloge, attendre, resoudre)
    importer_les_conseils(depot, sources, opd, robot, horloge, issues, rattrapage)
    return etat


def _accorder_issues(
    issues: ClientIssues, sondees: list[Source], precedent: dict[str, EtatSource], etats: dict[str, EtatSource]
) -> None:
    """Ouvre l'issue de chaque source en panne qui n'en a pas et ferme celle de chaque source dont la dernière sonde
    a réussi (un seul échec la laisse disponible, sans la faire revenir). La décision part des issues ouvertes, pas
    du seul changement d'état, pour qu'un passage refasse ce qu'un passage précédent a manqué."""
    signalees = issues.signalees(sondees)
    if signalees is None:
        signalees = {id_source for id_source, e in precedent.items() if e.etat == "en_panne"}
    for source in sondees:
        avant, apres = precedent.get(source.id), etats[source.id]
        if apres.etat == "en_panne" and source.id not in signalees:
            issues.panne(source, apres)
        elif apres.echecs_consecutifs == 0 and source.id in signalees:
            issues.retour(source, avant if avant is not None and avant.etat == "en_panne" else None, apres)


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
    enregistrements = corps.get(sonde.enregistrements)
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
    """Champs d'un enregistrement : `attributes` (JSON ArcGIS) ou `properties` (GeoJSON), sinon l'enregistrement
    lui-même, à plat (OpenParlData)."""
    if not isinstance(enregistrement, dict):
        return {}
    for cle in ("attributes", "properties"):
        if isinstance(enregistrement.get(cle), dict):
            return enregistrement[cle]
    return enregistrement


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


# --- Import quotidien des conseils (ADR 0015) ------------------------------------------------------------------

FUSEAU = ZoneInfo("Europe/Zurich")
HEURE_IMPORT = time_du_jour(7)  # à Lausanne


def dernier_seuil(heure: datetime) -> datetime:
    """Le dernier 7 h passé à Lausanne, à `heure` ou avant."""
    locale = heure.astimezone(FUSEAU)
    seuil = datetime.combine(locale.date(), HEURE_IMPORT, tzinfo=FUSEAU)
    if seuil > locale:
        seuil = datetime.combine(locale.date() - timedelta(days=1), HEURE_IMPORT, tzinfo=FUSEAU)
    return seuil


def conseils_dus(conseils: list[Source], imports: Mapping[str, datetime], heure: datetime) -> set[str]:
    """Les clés des conseils à importer à `heure` : ceux dont le dernier import réussi précède le dernier 7 h
    passé à Lausanne, et ceux qui n'ont jamais été importés. Un conseil s'importe ainsi au premier passage après
    7 h, une fois par jour, et un import en échec est refait au passage suivant."""
    seuil = dernier_seuil(heure)
    cles = (s.conseil.cle for s in conseils if s.conseil is not None)
    return {c for c in cles if c not in imports or imports[c] < seuil}


def importer_les_conseils(
    depot: Path,
    sources: FichierSources,
    opd: OpenParlData,
    robot: Robot,
    horloge: Callable[[], datetime],
    issues: ClientIssues,
    rattrapage: bool,
) -> None:
    """Importe les conseils dus (tous, depuis tout l'historique, pour un `rattrapage`), puis accorde les issues
    `import-conseils` aux dates d'import. Seules les sondes décident d'une panne : l'import ne touche pas à l'état
    des sources, et une erreur de l'API des issues est affichée sans faire échouer le passage."""
    conseils = [s for s in sources.sources if s.conseil is not None]
    if not conseils:
        return
    heure = _a_la_seconde(horloge())
    avant = lire_imports(depot)
    dus = {s.conseil.cle for s in conseils} if rattrapage else conseils_dus(conseils, avant, heure)
    apres = avant
    if dus:
        try:
            apres = importer_conseils(
                depot, sources, opd, horloge, dus=dus, rattrapage=rattrapage, robot=robot
            ).conseils
        except Exception:
            # Une erreur imprévue (archive illisible, bogue) vaut un échec de tous les conseils dus : l'état des
            # sources est tout de même publié, et l'issue `import-conseils` s'ouvrira au-delà de 24 h.
            print("Import des conseils en échec, le passage suivant réessaiera :", file=sys.stderr)
            traceback.print_exc()

    try:
        _accorder_issues_import(issues, conseils, avant, apres, heure)
    except httpx.HTTPError as e:
        print(f"Issues import-conseils non mises à jour, le passage suivant réessaiera : {e}", file=sys.stderr)


DELAI_AVANT_ISSUE_IMPORT = timedelta(hours=24)


def _accorder_issues_import(
    issues: ClientIssues,
    conseils: list[Source],
    avant: Mapping[str, datetime],
    apres: Mapping[str, datetime],
    heure: datetime,
) -> None:
    """Ouvre l'issue de chaque conseil sans import réussi depuis plus de 24 h qui n'en a pas, et ferme celle de
    chaque conseil importé depuis. Un conseil qui n'a jamais été importé n'a pas de date d'où compter : il est dû à
    chaque passage, et son issue s'ouvre dès qu'il manque encore à `apres`."""

    def perime(imports: Mapping[str, datetime], conseil: Source) -> bool:
        dernier = imports.get(conseil.conseil.cle)
        return dernier is not None and heure - dernier > DELAI_AVANT_ISSUE_IMPORT

    signales = issues.imports_signales(conseils)
    for conseil in conseils:
        dernier = apres.get(conseil.conseil.cle)
        if dernier is None or perime(apres, conseil):
            if signales is None or conseil.id not in signales:
                issues.import_en_echec(conseil, dernier)
        elif conseil.id in signales if signales is not None else perime(avant, conseil):
            issues.import_retour(conseil, dernier)


# --- Commit et push (hors du point de test : l'option sans push sert de vérification locale) -------------------

NOUVEAUX_ESSAIS_PUSH = 2


def _git(depot: Path, *args: str, verifier: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(depot), *args], check=verifier, text=True)


def committer(depot: Path, etat: EtatSources) -> None:
    chemins = [FICHIER_ETAT, "schema"] + (["conseils"] if (depot / "conseils").is_dir() else [])
    _git(depot, "add", "--all", "--", *chemins)
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
    parser.add_argument(
        "--rattrapage", action="store_true", help="importer tous les conseils depuis tout l'historique, à toute heure"
    )
    args = parser.parse_args(argv)

    depot = args.depot.resolve()
    if not (depot / ".git").exists():
        raise SystemExit(f"{depot} n'est pas un clone git du dépôt de données")
    with httpx.Client() as client, httpx.Client(timeout=30) as client_github:
        issues = client_issues(args.sans_push, os.environ, client_github)
        horloge = lambda: datetime.now(UTC)  # noqa: E731
        etat = passage(depot, lire_sources(args.sources), client, horloge, issues, rattrapage=args.rattrapage)
    for id_source, e in etat.sources.items():
        print(f"{id_source} : {e.etat}" + (f" ({e.motif}, {e.echecs_consecutifs} échec(s))" if e.motif else ""))

    committer(depot, etat)
    if args.sans_push:
        print("Commit fait, sans push (--sans-push).")
        return
    pousser(depot)


if __name__ == "__main__":
    main()
