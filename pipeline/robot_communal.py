"""Le robot communal (ADR 0006) : le seul client HTTP des sites communaux, partagé par le cron et les scripts de
préparation.

Son interface tient en une opération, `Robot.lire(url, role)`, qui rend la page (`Reponse` : corps décodé, statut,
en-têtes utiles) ou lève une `PageNonLue` qui dit pourquoi elle ne l'a pas été.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import threading
import time
from collections.abc import Callable
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
    ) -> None:
        self._http = http
        self._horloge = horloge
        self._attendre = attendre
        self._resoudre = resoudre
        self._verrou = threading.Lock()
        self._reseaux: dict[str, str] = {}  # hôte → réseau
        self._dernieres: dict[str, datetime] = {}  # réseau → fin de sa dernière requête

    def lire(self, url: str, role: Role) -> Reponse:
        """La page `url`, lue pour `role` ; lève une `PageNonLue` si elle ne l'a pas été."""
        with self._verrou:
            return self._lire(url, role)

    def _lire(self, url: str, role: Role) -> Reponse:
        # Les redirections sont suivies à la main : chaque étape est une requête, soumise au débit de son réseau.
        for _ in range(REDIRECTIONS + 1):
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
        reseau = self._reseau(httpx.URL(url).host)
        self._patienter(reseau)
        try:
            return self._http.get(
                url, headers={"User-Agent": user_agent(role)}, timeout=DELAI, follow_redirects=False
            )
        except httpx.TimeoutException as e:
            raise DelaiDepasse(f"{url} : délai de {DELAI:.0f} s dépassé") from e
        except httpx.TransportError as e:
            raise Injoignable(f"{url} : {e}") from e
        finally:
            self._dernieres[reseau] = self._horloge()

    def _reseau(self, hote: str) -> str:
        if hote not in self._reseaux:
            try:
                adresse = ipaddress.ip_address(self._resoudre(hote))
            except (OSError, ValueError) as e:
                raise Injoignable(f"{hote} : adresse introuvable ({e})") from e
            prefixe = 24 if adresse.version == 4 else 64
            self._reseaux[hote] = str(ipaddress.ip_network(f"{adresse}/{prefixe}", strict=False))
        return self._reseaux[hote]

    def _patienter(self, reseau: str) -> None:
        derniere = self._dernieres.get(reseau)
        if derniere is not None:
            ecart = (self._horloge() - derniere).total_seconds()
            if ecart < INTERVALLE:
                self._attendre(INTERVALLE - ecart)
