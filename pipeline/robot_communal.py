"""Le robot communal (ADR 0006) : le seul client HTTP des sites communaux, partagé par le cron et les scripts de
préparation.

Son interface tient en une opération, `Robot.lire(url, role)`, qui rend la page (`Reponse` : corps décodé, statut,
en-têtes utiles) ou lève une `PageNonLue` qui dit pourquoi elle ne l'a pas été.
"""

from __future__ import annotations

import ipaddress
import json
import re
import socket
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import httpx

from schema import RACINE

Role = Literal["sonde", "import"]
INTERVALLE = 5.0  # secondes, au moins, entre deux requêtes vers un même /24
DELAI = 30.0  # secondes, au plus, pour une requête
REDIRECTIONS = 5  # redirections suivies, au plus, pour une page

_CONFIG = json.loads((RACINE / "config.json").read_text())
A_PROPOS = f"{_CONFIG['site']}/a-propos#robot"


def user_agent(role: Role) -> str:
    """`VigieVaud-sonde` ou `VigieVaud-import`, avec le lien vers l'À propos et le courriel de contact : les règles
    de `robots.txt` visent `VigieVaud`, le suffixe dit le rôle."""
    return f"VigieVaud-{role} (+{A_PROPOS}; {_CONFIG['courriel']})"


# En-têtes dont dépend la lecture d'une page ; les autres ne sont pas rendus.
ENTETES_UTILES = ("content-type", "content-disposition", "content-encoding")


@dataclass(frozen=True)
class Reponse:
    url: str
    statut: int
    texte: str
    entetes: dict[str, str]


class PageNonLue(Exception):
    """La page n'a pas été lue ; la sous-classe dit pourquoi."""


class ErreurHttp(PageNonLue):
    """Le site a répondu par une erreur (ou une redirection sans fin) ; `retry_after` est son en-tête, s'il y en a."""

    def __init__(self, url: str, statut: int, retry_after: str | None = None) -> None:
        super().__init__(f"{url} : HTTP {statut}")
        self.url, self.statut, self.retry_after = url, statut, retry_after


class DelaiDepasse(PageNonLue):
    pass


class Injoignable(PageNonLue):
    """Connexion refusée, ou nom d'hôte qui ne se résout pas."""


class PageIllisible(PageNonLue):
    """La réponse est arrivée mais son corps ne se décode pas (compression annoncée et corps qui n'en est pas une)."""


class PageInterdite(PageNonLue):
    """`robots.txt` interdit la page au robot : elle n'a pas été demandée."""


class RobotsIndisponible(PageInterdite):
    """`robots.txt` a répondu par une erreur 5xx, ou un corps illisible : tout l'hôte est interdit (RFC 9309).
    `raison` le dit en court (« HTTP 500 »)."""

    def __init__(self, url: str, raison: str) -> None:
        super().__init__(f"{url} : {raison}, tout est interdit")
        self.raison = raison


class Robot:
    """Une requête à la fois, même appelé de plusieurs fils, et au moins `INTERVALLE` secondes entre deux requêtes
    vers un même réseau /24 (IPv6 : /64), mesurées depuis la fin de la précédente. Les réseaux ne s'attendent pas
    entre eux : l'appelant qui alterne entre les réseaux n'attend que le sien. Le réseau d'un hôte est résolu à sa
    première requête et gardé pour la vie du robot (un passage).

    Le client HTTP, l'horloge, l'attente et la résolution d'adresse sont reçus, jamais créés."""

    def __init__(
        self,
        http: httpx.Client,
        horloge: Callable[[], datetime],
        attendre: Callable[[float], None] = time.sleep,
        resoudre: Callable[[str], str] = socket.gethostbyname,
        *,
        intervalles: Mapping[str, float] | None = None,
    ) -> None:
        self._http = http
        self._intervalles = dict(intervalles or {})  # réseau → intervalle ralenti à la main
        self._horloge = horloge
        self._attendre = attendre
        self._resoudre = resoudre
        self._verrou = threading.Lock()
        self._reseaux: dict[str, str] = {}  # hôte → réseau
        self._robots: dict[str, Regles | PageInterdite] = {}  # hôte → ses règles, ou tout interdit
        self._dernieres: dict[str, datetime] = {}  # réseau → fin de sa dernière requête

    def lire(self, url: str, role: Role) -> Reponse:
        """La page `url`, lue pour `role` ; lève une `PageNonLue` si elle ne l'a pas été."""
        with self._verrou:
            return self._lire(url, role)

    def _lire(self, url: str, role: Role, robots: bool = True) -> Reponse:
        # Les redirections sont suivies à la main : chaque étape est une requête, soumise au débit de son réseau et,
        # sauf pour `robots.txt` lui-même, aux règles de son hôte.
        for _ in range(REDIRECTIONS + 1):
            if robots:
                self._verifier_robots(url, role)
            reponse = self._requete(url, role)
            lieu = reponse.headers.get("location")
            if not reponse.is_redirect or not lieu:
                break
            url = str(httpx.URL(url).join(lieu))
        else:
            raise ErreurHttp(url, reponse.status_code)  # plus de REDIRECTIONS redirections
        if reponse.status_code >= 300:
            raise ErreurHttp(url, reponse.status_code, reponse.headers.get("retry-after"))
        entetes = {k: reponse.headers[k] for k in ENTETES_UTILES if k in reponse.headers}
        return Reponse(url, reponse.status_code, reponse.text, entetes)

    def _requete(self, url: str, role: Role) -> httpx.Response:
        hote = httpx.URL(url).host
        reseau = self._reseau(hote)
        self._patienter(reseau, hote)
        try:
            return self._http.get(
                url, headers={"User-Agent": user_agent(role)}, timeout=DELAI, follow_redirects=False
            )
        except httpx.TimeoutException as e:
            raise DelaiDepasse(f"{url} : délai de {DELAI:.0f} s dépassé") from e
        except httpx.TransportError as e:
            raise Injoignable(f"{url} : {e}") from e
        except httpx.DecodingError as e:
            raise PageIllisible(f"{url} : corps illisible ({e})") from e
        finally:
            self._dernieres[reseau] = self._horloge()

    def _verifier_robots(self, url: str, role: Role) -> None:
        adresse = httpx.URL(url)
        if adresse.path == "/robots.txt":
            return
        regles = self._regles(adresse, role)
        if isinstance(regles, PageInterdite):
            raise regles
        chemin = adresse.raw_path.decode("ascii", "replace")
        if not regles.permis(chemin):
            raise PageInterdite(f"{url} : interdite par robots.txt")

    def _regles(self, adresse: httpx.URL, role: Role) -> Regles | PageInterdite:
        """Les règles de `robots.txt` pour l'hôte de `adresse`, lues à sa première requête et gardées pour la vie du
        robot. Une erreur 4xx (ou trop de redirections) permet tout ; une erreur 5xx ou un corps illisible interdit
        tout. Une erreur qui bloque le réseau (429, 503, refus, délai) est levée telle quelle."""
        hote = adresse.host
        if hote not in self._robots:
            url = str(adresse.copy_with(path="/robots.txt", query=None, fragment=None))
            try:
                self._robots[hote] = Regles.lire(self._lire(url, role, robots=False).texte)
            except ErreurHttp as e:
                if e.statut >= 500:
                    self._robots[hote] = RobotsIndisponible(url, f"HTTP {e.statut}")
                else:
                    self._robots[hote] = Regles.lire("")
            except PageIllisible:
                self._robots[hote] = RobotsIndisponible(url, "illisible")
        return self._robots[hote]

    def _reseau(self, hote: str) -> str:
        if hote not in self._reseaux:
            try:
                adresse = ipaddress.ip_address(self._resoudre(hote))
            except (OSError, ValueError) as e:
                raise Injoignable(f"{hote} : adresse introuvable ({e})") from e
            prefixe = 24 if adresse.version == 4 else 64
            self._reseaux[hote] = str(ipaddress.ip_network(f"{adresse}/{prefixe}", strict=False))
        return self._reseaux[hote]

    def _patienter(self, reseau: str, hote: str) -> None:
        """Attend que l'intervalle du réseau soit passé depuis sa dernière requête : 5 s, ou plus si le `Crawl-delay`
        de l'hôte le demande."""
        derniere = self._dernieres.get(reseau)
        if derniere is None:
            return
        regles = self._robots.get(hote)
        delai = regles.crawl_delay if isinstance(regles, Regles) and regles.crawl_delay else 0.0
        intervalle = max(INTERVALLE, self._intervalles.get(reseau, 0.0), delai)
        ecart = (self._horloge() - derniere).total_seconds()
        if ecart < intervalle:
            self._attendre(intervalle - ecart)


# --- robots.txt (RFC 9309) ----------------------------------------------------------------------------------------

NOM = "vigievaud"  # le nom auquel s'appliquent les règles de `robots.txt`, quel que soit le rôle


@dataclass(frozen=True)
class Regles:
    """Les règles de `robots.txt` qui s'appliquent à `VigieVaud` : celles de ses groupes, sinon celles de `*`."""

    regles: tuple[tuple[bool, str], ...] = ()  # (permis, motif de chemin)
    crawl_delay: float | None = None

    @classmethod
    def lire(cls, texte: str) -> Regles:
        groupes: list[tuple[set[str], list[tuple[bool, str]], list[float]]] = []
        agents: set[str] | None = None  # les agents du groupe en cours, tant qu'aucune règle ne l'a fermé
        for ligne in texte.splitlines():
            cle, deux_points, valeur = ligne.split("#", 1)[0].partition(":")
            if not deux_points:
                continue
            cle, valeur = cle.strip().lower(), valeur.strip()
            if cle == "user-agent":
                if agents is None:
                    agents = set()
                    groupes.append((agents, [], []))
                agents.add(valeur.lower())
                continue
            if not groupes:
                continue
            agents = None
            _, regles, delais = groupes[-1]
            if cle in ("allow", "disallow") and valeur:
                regles.append((cle == "allow", valeur))
            elif cle == "crawl-delay":
                try:
                    delais.append(float(valeur))
                except ValueError:
                    pass
        for nom in (NOM, "*"):
            choisis = [g for g in groupes if nom in g[0]]
            if choisis:
                delais = [d for _, _, ds in choisis for d in ds]
                return cls(tuple(r for _, rs, _ in choisis for r in rs), max(delais) if delais else None)
        return cls()

    def permis(self, chemin: str) -> bool:
        """La règle dont le motif est le plus long l'emporte ; à égalité, `Allow`. Sans règle qui s'applique, permis."""
        meilleure: tuple[int, bool] | None = None
        for permis, motif in self.regles:
            if _motif(motif).match(chemin):
                cle = (len(motif), permis)
                meilleure = cle if meilleure is None or cle > meilleure else meilleure
        return meilleure is None or meilleure[1]


def _motif(motif: str) -> re.Pattern[str]:
    fin = motif.endswith("$")
    corps = ".*".join(re.escape(morceau) for morceau in motif.removesuffix("$").split("*"))
    return re.compile(corps + ("$" if fin else ""))
