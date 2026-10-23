"""Un faux réseau de sites communaux écrit à la main, sur le modèle du faux OpenParlData de J1.

Un `Reseau` sert des pages par URL (corps en octets ou en texte, en-têtes, statut), suit la résolution d'adresse
de chaque hôte (`adresses`, pour le /24 du robot) et sait répondre ce qu'un site réel répond quand il refuse : un
statut d'erreur avec ses en-têtes (`Retry-After`), une redirection, une connexion refusée, un délai dépassé. Chaque
requête est notée dans `journal` avec son URL, son User-Agent et l'heure de l'horloge factice ; `en_vol_max` dit
combien de requêtes ont été en cours en même temps, au plus.
"""

from __future__ import annotations

import gzip
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

import httpx


@dataclass
class Page:
    corps: bytes | str = ""
    statut: int = 200
    entetes: dict[str, str] = field(default_factory=lambda: {"Content-Type": "text/html; charset=utf-8"})
    gzip: bool = False  # sert le corps compressé, avec `content-encoding: gzip`

    def reponse(self) -> httpx.Response:
        corps = self.corps.encode("utf-8") if isinstance(self.corps, str) else self.corps
        entetes = dict(self.entetes)
        if self.gzip:
            corps = gzip.compress(corps, mtime=0)
            entetes["content-encoding"] = "gzip"
        return httpx.Response(self.statut, content=corps, headers=entetes)


def redirection(vers: str, statut: int = 302) -> Page:
    return Page(statut=statut, entetes={"Location": vers})


REFUS = "refus"  # connexion refusée
DELAI = "delai"  # délai dépassé


@dataclass
class Requete:
    url: str
    user_agent: str
    heure: datetime


@dataclass
class Reseau:
    horloge: Callable[[], datetime]
    pages: dict[str, Page | str] = field(default_factory=dict)  # URL → page, ou REFUS / DELAI
    adresses: dict[str, str] = field(default_factory=dict)  # hôte → adresse IP
    journal: list[Requete] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    en_vol_max: int = 0
    duree: float = 0.0  # secondes réelles que dure chaque réponse, pour voir des requêtes simultanées
    _en_vol: int = 0
    _verrou: threading.Lock = field(default_factory=threading.Lock)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._repondre)

    def resoudre(self, hote: str) -> str:
        self.resolutions.append(hote)
        if hote not in self.adresses:
            raise OSError(f"{hote} : nom inconnu")
        return self.adresses[hote]

    def _repondre(self, requete: httpx.Request) -> httpx.Response:
        with self._verrou:
            self._en_vol += 1
            self.en_vol_max = max(self.en_vol_max, self._en_vol)
        try:
            url = str(requete.url)
            self.journal.append(Requete(url, requete.headers.get("User-Agent", ""), self.horloge()))
            time.sleep(self.duree)
            page = self.pages.get(url)
            if page == REFUS:
                raise httpx.ConnectError("Connection refused", request=requete)
            if page == DELAI:
                raise httpx.ReadTimeout("timed out", request=requete)
            if page is None:
                return httpx.Response(404, text="introuvable")
            return page.reponse()
        finally:
            with self._verrou:
                self._en_vol -= 1

    def heures(self, hote: str | None = None) -> list[datetime]:
        return [r.heure for r in self.journal if hote is None or urlsplit(r.url).hostname == hote]
