"""Un passage du cron (ADR 0005, 0014 et 0015) : sondes et état des sources, puis import quotidien des conseils.

Le passage relit `sources.json` et l'état précédent dans un clone du dépôt de données, sonde chaque source qui a
un bloc `sonde` et le site de chaque commune due (`sonde_sites.py`, par le robot communal), écrit
`etat-sources.json`, copie `schema/`, importe les conseils dus (`conseils.py` : OpenParlData, et les sites des
communes par le robot communal), puis committe (l'historique sert d'archive) et pousse. Il ouvre l'issue
`panne-source` d'une source en panne et ferme celle d'une source disponible, dans le dépôt de données ; pour les
communes scrapées, l'issue est celle de leur plateforme (« Panne : i-web »), avec la liste des communes en panne,
ouverte avec la première et fermée au retour de la dernière. Une erreur de l'API des issues ne fait pas échouer le
passage : l'état est tout de même écrit et publié, et le passage suivant, qui compare de nouveau l'état aux issues
ouvertes, refait ce qui a manqué.

Les sondes des sources tournent à chaque passage (toutes les 30 minutes). Chaque conseil, lui, s'importe une fois
par jour, au premier passage après 7 h à Lausanne, depuis le jour de son dernier import réussi ; un import en échec
est refait au passage suivant. Le site d'une commune est sondé une fois par jour, juste avant son import : une sonde
en échec saute l'import et est refaite au passage suivant. Quand aucun import d'un conseil n'a réussi depuis plus de
24 h, ou dès le premier échec d'un conseil qui n'a jamais été importé, le passage ouvre son issue `import-conseils`,
qu'il commente et ferme au premier import réussi. Seules les sondes mettent une source en panne : un import en échec
ne touche pas à l'état des sources. Pour les communes scrapées, l'issue `import-conseils` est aussi celle de leur
plateforme (« Import en échec : i-web »), comme l'issue `a-verifier` (« À vérifier : i-web »), qui liste les conseils
sans aucune nouvelle Séance, tenue ou annoncée, depuis 9 mois.

En local, contre un clone du dépôt de données (depuis `pipeline/`) :

    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push
    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push --rattrapage
    uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push --rattrapage-cible i-web

`--sans-push` écrit l'état et committe sans pousser, et affiche les issues au lieu de les ouvrir. `--rattrapage`
importe tous les conseils d'OpenParlData depuis tout l'historique, à toute heure (le même chemin, `depuis` vide),
sans toucher aux sites des communes. `--rattrapage-cible` (ADR 0010) prend une plateforme (`i-web`) ou le n° OFS
d'une commune scrapée et rouvre toutes les pages de son site ou de ceux de la plateforme, hors de la fenêtre de
6 mois et sans plafond de requêtes, au même débit, sans toucher à OpenParlData ni aux autres communes ; il note
l'heure de chaque rattrapage dans `conseils/import.json` (`rattrapages`). En production, le workflow réutilisable
`.github/workflows/cron.yml` lance la même commande sans `--sans-push`, avec le `GITHUB_TOKEN` et le
`GITHUB_REPOSITORY` du dépôt de données dans l'environnement, puis publie le dépôt sur Pages ; un lancement manuel
(`workflow_dispatch`) y ajoute `--rattrapage` avec l'entrée `rattrapage`, ou `--rattrapage-cible` avec l'entrée
`rattrapage_cible`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from datetime import time as time_du_jour
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from conseils import OpenParlData, importer_conseils, lire_imports, lire_premiers_imports
from robot_communal import CrawlDelayTropLong, Robot, erreur_tls, robot_des_sources
from schema import (
    DOSSIER_SCHEMA,
    RACINE,
    EtatReseau,
    EtatSource,
    EtatSources,
    FichierSources,
    Plateforme,
    Sonde,
    Source,
    lire_sources,
)
from sites_communaux import mois_plus_tot
from sonde_sites import sonder_site

FICHIER_ETAT = "etat-sources.json"
ECHECS_AVANT_PANNE = 2
# L'adresse du dépôt vient de `config.json`, puisque le dépôt est renommé à la fin de J0.
USER_AGENT = f"VigieVaud-sonde (+{json.loads((RACINE / 'config.json').read_text())['depot']})"


@dataclass(frozen=True)
class SorteIssue:
    """Une sorte d'issue ouverte par plateforme pour les communes scrapées : `panne-source` (`PANNES`),
    `import-conseils` (`IMPORTS`) et `a-verifier` (`A_VERIFIER`). `constat` et `retour` reçoivent `{plateforme}`."""

    etiquette: str
    titre: str  # « Panne » : l'issue s'intitule « Panne : i-web »
    constat: str  # la phrase qui précède la liste des communes
    suite: str  # le paragraphe qui la suit
    touchees: str  # « Communes en panne : … », en commentaire quand la liste change
    revenues: str  # « De nouveau disponibles : … », au même commentaire et à la fermeture
    retour: str  # la phrase du commentaire de fermeture


# Une commune touchée, avec ce qui la touche, dans l'issue de sa plateforme : (source, « depuis le …, marqueur absent »).
Touchee = tuple[Source, str]


class ClientIssues(Protocol):
    """Les issues `panne-source`, `import-conseils` et `a-verifier` du dépôt de données : `IssuesGitHub` en
    production, `IssuesAffichees` sans push. Une erreur de l'API lève `httpx.HTTPError`."""

    def signalees(self, sources: list[Source]) -> set[str] | None:
        """Identifiants des `sources` qui ont une issue `panne-source` ouverte, ou `None` pour un client qui ne voit
        pas les issues : le passage les suppose alors ouvertes pour les sources en panne dans l'état relu."""

    def panne(self, source: Source, etat: EtatSource) -> None:
        """La source est en panne sans issue ouverte ; `etat.depuis` est l'heure de la première sonde en échec."""

    def retour(self, source: Source, panne: EtatSource | None, etat: EtatSource) -> None:
        """La source qui a une issue ouverte est disponible depuis `etat.depuis`. `panne` est son état en panne
        quand elle revient à ce passage, `None` quand son retour date d'un passage précédent."""

    def plateformes_signalees(self, sorte: SorteIssue, plateformes: list[Plateforme]) -> dict[str, set[str]] | None:
        """Pour chaque plateforme qui a une issue ouverte de cette `sorte`, les identifiants des sources communales
        que l'issue liste ; `None` pour un client qui ne voit pas les issues : le passage les déduit alors de l'état
        ou des imports relus."""

    def plateforme_touchee(self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee]) -> None:
        """Des communes de la plateforme sont touchées, sans issue ouverte de cette `sorte` : `communes`, dans
        l'ordre de `sources.json`, chacune avec ce qui la touche (« depuis le …, marqueur absent »)."""

    def liste_plateforme(
        self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee], revenues: list[Source]
    ) -> None:
        """L'issue ouverte de la plateforme liste d'autres communes que `communes` : la liste change. `revenues` sont
        les communes listées qui ne sont plus touchées."""

    def retour_plateforme(self, sorte: SorteIssue, plateforme: Plateforme, revenues: list[Source]) -> None:
        """Plus aucune commune de la plateforme qui a une issue ouverte de cette `sorte` n'est touchée ; `revenues`
        sont celles que l'issue listait."""

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

    def plateformes_signalees(self, sorte: SorteIssue, plateformes: list[Plateforme]) -> None:
        return None

    def plateforme_touchee(self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee]) -> None:
        print(f"{titre_plateforme(sorte, plateforme)} : {', '.join(_commune_touchee(c) for c in communes)}")

    def liste_plateforme(
        self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee], revenues: list[Source]
    ) -> None:
        self.plateforme_touchee(sorte, plateforme, communes)

    def retour_plateforme(self, sorte: SorteIssue, plateforme: Plateforme, revenues: list[Source]) -> None:
        print(f"{titre_plateforme(sorte, plateforme)} : {sorte.retour.format(plateforme=plateforme.nom)}")

    def imports_signales(self, conseils: list[Source]) -> None:
        return None

    def import_en_echec(self, conseil: Source, dernier: datetime | None) -> None:
        reussi = f"dernier import réussi {dernier:%Y-%m-%d %H:%M}Z" if dernier else "aucun import réussi"
        print(f"{titre_import(conseil)} ({reussi})")

    def import_retour(self, conseil: Source, dernier: datetime) -> None:
        print(f"Import de retour : {conseil.nom} (importé {dernier:%Y-%m-%d %H:%M}Z)")


ETIQUETTE_PANNE = "panne-source"
ETIQUETTE_IMPORT = "import-conseils"
ETIQUETTE_A_VERIFIER = "a-verifier"

_SUITE_LISTE = "Le cron tient cette liste à jour à chaque passage et fermera l'issue au retour de la dernière commune."

PANNES = SorteIssue(
    etiquette=ETIQUETTE_PANNE,
    titre="Panne",
    constat="La sonde du site de ces communes de {plateforme} échoue",
    suite="Tant que la sonde d'une commune échoue, son import du jour est sauté ; le site garde ce qui a déjà été "
    f"importé. {_SUITE_LISTE}",
    touchees="Communes en panne",
    revenues="De nouveau disponibles",
    retour="Plus aucune commune de {plateforme} n'est en panne",
)
IMPORTS = SorteIssue(
    etiquette=ETIQUETTE_IMPORT,
    titre="Import en échec",
    constat="Aucun import du conseil de ces communes de {plateforme} n'a réussi depuis plus de 24 h, ou aucun "
    "encore pour un conseil jamais importé",
    suite="Le cron réessaie l'import à chaque passage ; le journal du workflow donne la cause de chaque échec. Une "
    "commune n'est pas en panne pour autant : le site garde ce qui a déjà été importé et seul le badge de fraîcheur "
    f"vieillit. {_SUITE_LISTE}",
    touchees="Communes sans import réussi",
    revenues="De nouveau importées",
    retour="Le conseil de chaque commune de {plateforme} est de nouveau importé",
)
A_VERIFIER = SorteIssue(
    etiquette=ETIQUETTE_A_VERIFIER,
    titre="À vérifier",
    constat="Le site de ces communes de {plateforme} ne montre aucune nouvelle Séance, tenue ou annoncée, depuis "
    "9 mois",
    suite="La page de liste répond et se lit, mais elle est peut-être figée alors que le conseil publie ailleurs : "
    "à vérifier sur le site de la commune. La Couverture ne change pas. Le cron tient cette liste à jour à chaque "
    "passage et fermera l'issue quand la dernière commune aura de nouveau une Séance.",
    touchees="Communes à vérifier",
    revenues="Avec une nouvelle Séance",
    retour="Chaque commune de {plateforme} a de nouveau une Séance de moins de 9 mois",
)


class IssuesGitHub:
    """Client d'issues du cron : il ouvre et ferme les issues `panne-source`, `import-conseils` et `a-verifier` du
    dépôt de données `depot` (« propriétaire/nom ») avec le `GITHUB_TOKEN` de ce dépôt (ADR 0014)."""

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

    def plateformes_signalees(self, sorte: SorteIssue, plateformes: list[Plateforme]) -> dict[str, set[str]]:
        corps = {i["title"]: i.get("body") or "" for i in self._issues_ouvertes(sorte.etiquette)}
        return {
            p.id: _sources_listees(corps[titre_plateforme(sorte, p)])
            for p in plateformes
            if titre_plateforme(sorte, p) in corps
        }

    def plateforme_touchee(self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee]) -> None:
        corps = {"title": titre_plateforme(sorte, plateforme), "body": corps_plateforme(sorte, plateforme, communes)}
        self._requete("POST", self._api, json=corps | {"labels": [sorte.etiquette]})

    def liste_plateforme(
        self, sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee], revenues: list[Source]
    ) -> None:
        titre = titre_plateforme(sorte, plateforme)
        lignes = [f"{sorte.touchees} : {', '.join(s.nom_court for s, _ in communes)}."]
        if revenues:
            lignes.append(f"{sorte.revenues} : {', '.join(s.nom_court for s in revenues)}.")
        corps = corps_plateforme(sorte, plateforme, communes)
        for numero in [i["number"] for i in self._issues_ouvertes(sorte.etiquette) if i["title"] == titre]:
            self._requete("PATCH", f"{self._api}/{numero}", json={"body": corps})
            self._requete("POST", f"{self._api}/{numero}/comments", json={"body": "\n".join(lignes)})

    def retour_plateforme(self, sorte: SorteIssue, plateforme: Plateforme, revenues: list[Source]) -> None:
        lignes = [sorte.retour.format(plateforme=plateforme.nom) + "."]
        if revenues:
            lignes.append(f"{sorte.revenues} : {', '.join(s.nom_court for s in revenues)}.")
        self._fermer(sorte.etiquette, titre_plateforme(sorte, plateforme), "\n".join(lignes))

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


def titre_plateforme(sorte: SorteIssue, plateforme: Plateforme) -> str:
    """« Panne : i-web », « Import en échec : i-web », « À vérifier : i-web »."""
    return f"{sorte.titre} : {plateforme.nom}"


# Les identifiants des communes listées, en fin de corps de l'issue d'une plateforme, invisibles dans GitHub : le
# passage suivant y relit la liste sans dépendre de la mise en forme.
_SOURCES_LISTEES = re.compile(r"<!-- sources : ([^>]*) -->")


def _sources_listees(corps: str) -> set[str]:
    m = _SOURCES_LISTEES.search(corps)
    return set(m[1].split()) if m else set()


def _commune_touchee(commune: Touchee) -> str:
    source, detail = commune
    return f"{source.nom_court} ({detail})"


def corps_plateforme(sorte: SorteIssue, plateforme: Plateforme, communes: list[Touchee]) -> str:
    """Le corps de l'issue d'une plateforme : le constat, la liste des communes touchées et ce qui touche chacune,
    la suite, puis leurs identifiants pour le passage suivant."""
    lignes = "\n".join(f"- {_commune_touchee(c)}" for c in communes)
    return (
        f"{sorte.constat.format(plateforme=plateforme.nom)} :\n\n{lignes}\n\n{sorte.suite}\n\n"
        f"<!-- sources : {' '.join(s.id for s, _ in communes)} -->"
    )


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
    rattrapage_cible: str | None = None,
) -> EtatSources:
    """Sonde chaque source qui a un bloc `sonde` et le site de chaque commune due (`sonder_les_sites`), puis écrit
    `etat-sources.json` et copie `schema/` dans `depot`, un clone du dépôt de données. L'état précédent est relu
    dans ce clone ; absent, illisible ou d'une autre version, le passage repart de zéro. Les issues sont ensuite
    accordées à l'état écrit ; une erreur de leur API est affichée sans faire échouer le passage. Vient ensuite
    l'import des conseils dus (`importer_les_conseils`), sauf ceux dont la sonde du site a échoué ou dont le
    `Crawl-delay` dépasse 30 s ; l'import ne touche pas à l'état des sources. Les sites des communes sont sondés et lus par un robot communal, un seul pour
    tout le passage, sur le même client HTTP, avec la même horloge et la même attente, et `resoudre` pour le /24 de
    chaque hôte ; il ralentit les réseaux de la section `reseaux` de `sources.json`, plafonne chaque commune à
    `PLAFOND` requêtes hors rattrapage ciblé, et reçoit puis rend les réseaux bloqués, gardés dans `etat-sources.json`
    (`reseaux`) pour que le passage suivant les teste d'abord. Le commit et le push sont l'affaire de l'appelant.

    Un `rattrapage` relit tout l'historique des conseils d'OpenParlData, à toute heure, sans toucher aux sites des
    communes. Un `rattrapage_cible` (une plateforme ou le n° OFS d'une commune scrapée, lancé à la main) relit tout
    le site des seules communes visées, à toute heure, chacune sondée d'abord comme au passage ordinaire, sans
    plafond de requêtes mais au même débit, sans toucher à OpenParlData, aux sondes des sources ni aux autres
    communes ; une cible qui ne désigne aucune commune scrapée lève `ValueError` avant toute écriture."""
    rattrapes = _rattrapes(sources, rattrapage, rattrapage_cible)
    genere = _a_la_seconde(horloge())
    precedent = _lire_etat(depot / FICHIER_ETAT)
    etats: dict[str, EtatSource] = {}
    for source in sources.sources:
        if source.sonde is None:
            continue
        if rattrapage_cible is not None:
            # Le rattrapage ciblé ne touche qu'aux sites visés : les sondes des sources gardent leur état.
            if source.id in precedent:
                etats[source.id] = precedent[source.id]
            continue
        heure = _a_la_seconde(horloge())
        etats[source.id] = _suivant(precedent.get(source.id), heure, sonder(client, source.sonde))
    robot = robot_des_sources(
        client,
        sources,
        horloge,
        attendre,
        resoudre,
        rattrapage=rattrapage_cible is not None,
        bloques=_lire_reseaux_bloques(depot / FICHIER_ETAT),
    )
    sondes, sautes = sonder_les_sites(robot, sources, precedent, lire_imports(depot), horloge, rattrapes)
    etats |= sondes
    etat = EtatSources(version=1, genere=genere, sources=etats, reseaux=robot.reseaux_bloques())
    (depot / FICHIER_ETAT).write_text(etat.model_dump_json(indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(depot / "schema", ignore_errors=True)
    shutil.copytree(DOSSIER_SCHEMA, depot / "schema")

    try:
        sondees = [s for s in sources.sources if s.sonde is not None and s.id in etats]
        _accorder_issues(issues, sondees, precedent, etats)
        _accorder_pannes_plateformes(issues, sources, precedent, etats)
    except httpx.HTTPError as e:
        print(f"Issues panne-source non mises à jour, le passage suivant réessaiera : {e}", file=sys.stderr)

    opd = OpenParlData(client, horloge, attendre)
    importer_les_conseils(depot, sources, opd, robot, horloge, issues, rattrapes, sautes)
    if robot.reseaux_bloques() != etat.reseaux:
        # Un réseau bloqué pendant l'import : le passage suivant doit le savoir pour le tester d'abord.
        etat = etat.model_copy(update={"reseaux": robot.reseaux_bloques()})
        (depot / FICHIER_ETAT).write_text(etat.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return etat


def _rattrapes(sources: FichierSources, rattrapage: bool, cible: str | None) -> frozenset[str] | None:
    """Les clés des conseils qu'un rattrapage relit en entier : ceux d'OpenParlData pour un `rattrapage`, ceux des
    communes scrapées de la plateforme ou du n° OFS `cible` pour un rattrapage ciblé ; `None` pour un passage
    ordinaire. Lève `ValueError` si les deux sont demandés, ou si `cible` ne désigne aucune commune scrapée."""
    if cible is None:
        if not rattrapage:
            return None
        return frozenset(s.conseil.cle for s in sources.sources if s.conseil is not None and s.site is None)
    if rattrapage:
        raise ValueError("un rattrapage d'OpenParlData et un rattrapage ciblé ne se lancent pas ensemble")
    cles = frozenset(
        s.conseil.cle
        for s in _sites_sondes(sources)
        if s.site.plateforme == cible.strip() or s.conseil.cle == cible.strip().lower()
    )
    if not cles:
        raise ValueError(
            f"rattrapage ciblé : « {cible} » n'est ni une plateforme ni le n° OFS d'une commune scrapée"
        )
    return cles


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


def _accorder_pannes_plateformes(
    issues: ClientIssues, sources: FichierSources, precedent: Mapping[str, EtatSource], etats: Mapping[str, EtatSource]
) -> None:
    """L'issue `panne-source` de chaque plateforme, pour ses communes en panne : depuis quand et pourquoi."""

    def en_panne(lus: Mapping[str, EtatSource]) -> dict[str, EtatSource]:
        return {i: e for i, e in lus.items() if e.etat == "en_panne"}

    touchees = {
        i: f"depuis le {e.depuis:%Y-%m-%d à %H:%M} UTC, {e.motif}" if e.depuis else f"en panne, {e.motif}"
        for i, e in en_panne(etats).items()
    }
    _accorder_issues_plateformes(issues, PANNES, sources, touchees, en_panne(precedent).keys())


def _accorder_issues_plateformes(
    issues: ClientIssues,
    sorte: SorteIssue,
    sources: FichierSources,
    touchees: Mapping[str, str],
    avant: Collection[str],
) -> None:
    """Une issue de cette `sorte` par plateforme pour les communes scrapées : ouverte avec la première commune
    touchée, sa liste mise à jour quand une commune y entre ou en sort, fermée au retour de la dernière. `touchees`
    donne, par identifiant de source, ce qui touche chaque commune à ce passage. Comme pour une source, la décision
    part des communes que listent les issues ouvertes ; un client qui ne les voit pas les laisse déduire de `avant`,
    les communes touchées d'après l'état ou les imports relus."""
    sites = _sites_sondes(sources)
    plateformes = [p for p in sources.plateformes if any(s.site.plateforme == p.id for s in sites)]
    if not plateformes:
        return
    par_plateforme = {p.id: [s for s in sites if s.site.plateforme == p.id] for p in plateformes}
    signalees = issues.plateformes_signalees(sorte, plateformes)
    if signalees is None:
        deduites = {p: {s.id for s in siennes if s.id in avant} for p, siennes in par_plateforme.items()}
        signalees = {p: ids for p, ids in deduites.items() if ids}
    for plateforme in plateformes:
        siennes = par_plateforme[plateforme.id]
        communes = [(s, touchees[s.id]) for s in siennes if s.id in touchees]
        listees = signalees.get(plateforme.id)
        revenues = [s for s in siennes if listees and s.id in listees and s.id not in touchees]
        if communes and listees is None:
            issues.plateforme_touchee(sorte, plateforme, communes)
        elif communes and {s.id for s, _ in communes} != listees:
            issues.liste_plateforme(sorte, plateforme, communes, revenues)
        elif not communes and listees is not None:
            issues.retour_plateforme(sorte, plateforme, revenues)


def _a_la_seconde(heure: datetime) -> datetime:
    return heure.astimezone(UTC).replace(microsecond=0)


def _lire_etat(chemin: Path) -> dict[str, EtatSource]:
    try:
        return EtatSources.model_validate_json(chemin.read_bytes()).sources
    except (FileNotFoundError, ValidationError):
        return {}


def _lire_reseaux_bloques(chemin: Path) -> dict[str, EtatReseau]:
    try:
        return EtatSources.model_validate_json(chemin.read_bytes()).reseaux
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
        return "erreur TLS" if erreur_tls(e) else "erreur réseau"
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


def _sites_sondes(sources: FichierSources) -> list[Source]:
    """Les sources communales sondées : un bloc `site` et un conseil (une commune non couverte n'en a pas)."""
    return [s for s in sources.sources if s.site is not None and s.conseil is not None]


def sonder_les_sites(
    robot: Robot,
    sources: FichierSources,
    precedent: Mapping[str, EtatSource],
    imports: Mapping[str, datetime],
    horloge: Callable[[], datetime],
    rattrapes: Collection[str] | None = None,
) -> tuple[dict[str, EtatSource], dict[str, str]]:
    """L'état de chaque source communale sondée, et les conseils dont l'import est sauté à ce passage, avec la
    raison. Une commune est sondée une fois par jour, juste avant son import : au passage où son conseil est dû (pour
    un rattrapage, quand sa clé est dans `rattrapes`), sauf si une sonde a déjà réussi depuis le dernier 7 h à
    Lausanne. Une sonde en échec est donc refaite au passage suivant, et la commune passe en panne à deux échecs,
    comme toute source ; tant qu'elle échoue, l'import est sauté. Une commune qui n'est pas sondée à ce passage garde
    son état précédent, comme celle dont le `Crawl-delay` est trop long : ni succès ni panne, mais son import est
    sauté (« Crawl-delay trop long (600 s) »)."""
    sites = _sites_sondes(sources)
    heure = _a_la_seconde(horloge())
    if rattrapes is None:
        dus = conseils_dus(sites, imports, heure)
    else:
        dus = {s.conseil.cle for s in sites} & set(rattrapes)
    seuil = dernier_seuil(heure)
    etats: dict[str, EtatSource] = {}
    lents: dict[str, str] = {}  # les conseils des sites au `Crawl-delay` trop long, et ce motif

    def sonder(source: Source) -> None:
        try:
            motif = sonder_site(robot, source, sources.plateformes)
        except CrawlDelayTropLong as e:
            lents[source.conseil.cle] = e.motif
            if source.id in precedent:
                etats[source.id] = precedent[source.id]
            return
        etats[source.id] = _suivant(precedent.get(source.id), _a_la_seconde(horloge()), motif)

    # Un réseau bloqué à un passage précédent est d'abord testé par une seule sonde, celle de sa première commune
    # due, même si elle a déjà été sondée ce jour : elle le rouvre aux autres, ou il reste bloqué.
    for source in sites:
        if source.conseil.cle in dus and robot.a_tester(source.site.seances):
            sonder(source)
    for source in sites:
        if source.id in etats:
            continue
        avant = precedent.get(source.id)
        reussie_ce_jour = avant is not None and not avant.echecs_consecutifs and avant.derniere_sonde >= seuil
        if source.conseil.cle not in dus or reussie_ce_jour:
            if avant is not None:
                etats[source.id] = avant
            continue
        sonder(source)
    sautes = {
        s.conseil.cle: f"sonde en échec : {etats[s.id].motif}"
        for s in sites
        if s.id in etats and etats[s.id].echecs_consecutifs
    }
    return etats, sautes | lents


def importer_les_conseils(
    depot: Path,
    sources: FichierSources,
    opd: OpenParlData,
    robot: Robot,
    horloge: Callable[[], datetime],
    issues: ClientIssues,
    rattrapes: Collection[str] | None = None,
    sautes: Mapping[str, str] | None = None,
) -> None:
    """Importe les conseils dus (pour un rattrapage, ceux de `rattrapes`, depuis tout l'historique), puis accorde
    les issues `import-conseils` aux dates d'import. `sautes` donne, par clé, les conseils dont le site n'est pas lu
    à ce passage et pourquoi (sonde en échec, `Crawl-delay` trop long) : leur import du jour est sauté, ce qui vaut un
    import en échec ordinaire. Seules les sondes
    décident d'une panne : l'import ne touche pas à l'état des sources, et une erreur de l'API des issues est
    affichée sans faire échouer le passage."""
    conseils = [s for s in sources.sources if s.conseil is not None]
    if not conseils:
        return
    sautes = sautes or {}
    heure = _a_la_seconde(horloge())
    avant = lire_imports(depot)
    if rattrapes is None:
        dus = conseils_dus(conseils, avant, heure)
    else:
        dus = {s.conseil.cle for s in conseils} & set(rattrapes)
    for conseil in conseils:
        if conseil.conseil.cle in dus and conseil.conseil.cle in sautes:
            print(f"Import sauté : {conseil.nom} ({sautes[conseil.conseil.cle]})", file=sys.stderr)
    dus -= sautes.keys()
    apres = avant
    if dus:
        try:
            apres = importer_conseils(
                depot, sources, opd, horloge, dus=dus, rattrapage=rattrapes is not None, robot=robot
            ).conseils
        except Exception:
            # Une erreur imprévue (archive illisible, bogue) vaut un échec de tous les conseils dus : l'état des
            # sources est tout de même publié, et l'issue `import-conseils` s'ouvrira au-delà de 24 h.
            print("Import des conseils en échec, le passage suivant réessaiera :", file=sys.stderr)
            traceback.print_exc()

    try:
        _accorder_issues_import(issues, sources, avant, apres, heure)
    except httpx.HTTPError as e:
        print(f"Issues import-conseils non mises à jour, le passage suivant réessaiera : {e}", file=sys.stderr)
    try:
        _accorder_issues_a_verifier(issues, depot, sources, heure)
    except httpx.HTTPError as e:
        print(f"Issues a-verifier non mises à jour, le passage suivant réessaiera : {e}", file=sys.stderr)


MOIS_AVANT_A_VERIFIER = 9


def _accorder_issues_a_verifier(issues: ClientIssues, depot: Path, sources: FichierSources, heure: datetime) -> None:
    """L'issue `a-verifier` de chaque plateforme, pour ses conseils sans aucune nouvelle Séance, tenue ou annoncée,
    depuis 9 mois : la date de la dernière Séance de l'archive, sinon celle du premier import (jour à Lausanne). Un
    conseil jamais importé n'en a pas : c'est l'affaire de l'issue `import-conseils`. Un client qui ne voit pas les
    issues se voit signaler la liste à chaque passage, sans retour."""
    seuil = mois_plus_tot(heure.astimezone(FUSEAU).date(), MOIS_AVANT_A_VERIFIER)
    premiers = lire_premiers_imports(depot)
    touchees = {}
    for site in _sites_sondes(sources):
        cle = site.conseil.cle
        jours = [f.stem for f in (depot / "conseils" / cle / "seances").glob("*.json")]
        if jours:
            derniere = date.fromisoformat(max(jours))
            if derniere <= seuil:
                touchees[site.id] = f"dernière Séance le {derniere:%Y-%m-%d}"
        elif cle in premiers:
            premier = premiers[cle].astimezone(FUSEAU).date()
            if premier <= seuil:
                touchees[site.id] = f"aucune Séance depuis le premier import, le {premier:%Y-%m-%d}"
    _accorder_issues_plateformes(issues, A_VERIFIER, sources, touchees, ())


DELAI_AVANT_ISSUE_IMPORT = timedelta(hours=24)


def _accorder_issues_import(
    issues: ClientIssues,
    sources: FichierSources,
    avant: Mapping[str, datetime],
    apres: Mapping[str, datetime],
    heure: datetime,
) -> None:
    """Ouvre l'issue de chaque conseil sans import réussi depuis plus de 24 h qui n'en a pas, et ferme celle de
    chaque conseil importé depuis. Un conseil qui n'a jamais été importé n'a pas de date d'où compter : il est dû à
    chaque passage, et son issue s'ouvre dès qu'il manque encore à `apres`. Pour les communes scrapées, l'issue est
    celle de leur plateforme (« Import en échec : i-web »), avec la liste des communes touchées."""

    def perime(imports: Mapping[str, datetime], conseil: Source) -> bool:
        dernier = imports.get(conseil.conseil.cle)
        return dernier is not None and heure - dernier > DELAI_AVANT_ISSUE_IMPORT

    def en_echec(conseil: Source) -> bool:
        return conseil.conseil.cle not in apres or perime(apres, conseil)

    sites = _sites_sondes(sources)
    touchees = {}
    for site in sites:
        if en_echec(site):
            dernier = apres.get(site.conseil.cle)
            touchees[site.id] = f"dernier import réussi le {dernier:%Y-%m-%d à %H:%M} UTC" if dernier else (
                "aucun import réussi"
            )
    _accorder_issues_plateformes(issues, IMPORTS, sources, touchees, {s.id for s in sites if perime(avant, s)})

    conseils = [s for s in sources.sources if s.conseil is not None and s.site is None]
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
    rattrapages = parser.add_mutually_exclusive_group()
    rattrapages.add_argument(
        "--rattrapage",
        action="store_true",
        help="importer tous les conseils d'OpenParlData depuis tout l'historique, à toute heure, sans les sites",
    )
    rattrapages.add_argument(
        "--rattrapage-cible",
        metavar="CIBLE",
        help="relire tout le site des communes d'une plateforme (i-web) ou d'une commune scrapée (n° OFS)",
    )
    args = parser.parse_args(argv)

    depot = args.depot.resolve()
    if not (depot / ".git").exists():
        raise SystemExit(f"{depot} n'est pas un clone git du dépôt de données")
    with httpx.Client() as client, httpx.Client(timeout=30) as client_github:
        issues = client_issues(args.sans_push, os.environ, client_github)
        horloge = lambda: datetime.now(UTC)  # noqa: E731
        etat = passage(
            depot,
            lire_sources(args.sources),
            client,
            horloge,
            issues,
            rattrapage=args.rattrapage,
            rattrapage_cible=args.rattrapage_cible or None,
        )
    for id_source, e in etat.sources.items():
        print(f"{id_source} : {e.etat}" + (f" ({e.motif}, {e.echecs_consecutifs} échec(s))" if e.motif else ""))

    committer(depot, etat)
    if args.sans_push:
        print("Commit fait, sans push (--sans-push).")
        return
    pousser(depot)


if __name__ == "__main__":
    main()
