"""Un faux réseau de sites communaux écrit à la main, sur le modèle du faux OpenParlData de J1.

Un `Reseau` sert des pages par URL (corps en octets ou en texte, en-têtes, statut), suit la résolution d'adresse
de chaque hôte (`adresses`, pour le /24 du robot) et sait répondre ce qu'un site réel répond quand il refuse : un
statut d'erreur avec ses en-têtes (`Retry-After`), une redirection, une connexion refusée, un délai dépassé, une
erreur TLS. Chaque
requête est notée dans `journal` avec son URL, son User-Agent et l'heure de l'horloge factice ; `en_vol_max` dit
combien de requêtes ont été en cours en même temps, au plus.

`echantillon(plateforme, variante)` sert les pages enregistrées par le script d'échantillon (`echantillon-sites/`,
un dossier par variante, ou par vue `coreapi` : `coreapi-documentconseil`), chacune à son URL, avec la redirection
de l'URL demandée vers l'URL finale. Le passage du cron reçoit un seul transport : `Reseau.transport(repli)` sert
les sites de `adresses` et passe toute autre requête à `repli`, le faux OpenParlData.
"""

from __future__ import annotations

import gzip
import json
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
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
TLS = "tls"  # certificat refusé à la poignée de main TLS


@dataclass
class Requete:
    url: str
    user_agent: str
    heure: datetime


@dataclass
class Reseau:
    horloge: Callable[[], datetime]
    pages: dict[str, Page | str] = field(default_factory=dict)  # URL → page, ou REFUS / DELAI / TLS
    adresses: dict[str, str] = field(default_factory=dict)  # hôte → adresse IP
    journal: list[Requete] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)
    en_vol_max: int = 0
    duree: float = 0.0  # secondes réelles que dure chaque réponse, pour voir des requêtes simultanées
    _en_vol: int = 0
    _verrou: threading.Lock = field(default_factory=threading.Lock)

    def transport(self, repli: httpx.BaseTransport | None = None) -> httpx.MockTransport:
        """Le transport du réseau ; avec `repli`, une requête vers un hôte absent de `adresses` lui est passée."""

        def repondre(requete: httpx.Request) -> httpx.Response:
            if repli is not None and requete.url.host not in self.adresses:
                return repli.handle_request(requete)
            return self._repondre(requete)

        return httpx.MockTransport(repondre)

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
            if page == TLS:
                # Comme httpx : une erreur de connexion, causée par l'erreur `ssl` de la poignée de main.
                try:
                    raise ssl.SSLCertVerificationError(1, "certificate verify failed: certificate has expired")
                except ssl.SSLError as e:
                    raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED]", request=requete) from e
            if page is None:
                return httpx.Response(404, text="introuvable")
            return page.reponse()
        finally:
            with self._verrou:
                self._en_vol -= 1

    def heures(self, hote: str | None = None) -> list[datetime]:
        return [r.heure for r in self.journal if hote is None or urlsplit(r.url).hostname == hote]


ECHANTILLONS = Path(__file__).resolve().parent / "echantillon-sites"


def echantillon(plateforme: str, variante: str) -> dict[str, Page]:
    """Les pages de l'échantillon d'une variante, par URL : chaque page à son URL finale, servie avec son
    `Content-Type`, et l'URL demandée qui y redirige. Le corps enregistré est décompressé : une page que le site a
    servie avec `content-encoding: gzip` est recompressée (`Page.gzip`), sans recopier l'en-tête de l'index."""
    dossier = ECHANTILLONS / plateforme / variante
    index = json.loads((dossier / "index.json").read_text(encoding="utf-8"))
    pages: dict[str, Page] = {}
    for p in index["pages"]:
        entetes = {"Content-Type": p["entetes"]["content-type"]}
        gzip_ = p["entetes"].get("content-encoding", "").lower() == "gzip"
        pages[p["finale"]] = Page((dossier / p["fichier"]).read_bytes(), p["statut"], entetes, gzip=gzip_)
        if p["url"] != p["finale"]:
            pages[p["url"]] = redirection(urlsplit(p["finale"]).path)
    return pages


class Ordonnanceur:
    """Le temps virtuel des fils du passage : l'attente (`attendre`) et l'alternance entre réseaux (`alterner`) du
    cron, sur l'horloge factice des tests. Hors d'une alternance, `attendre` avance l'horloge comme
    `HorlogeFactice.attendre`. Pendant une alternance, chaque groupe a son fil, et un fil qui attend dort jusqu'à son
    heure : l'horloge n'avance que quand tous les fils vivants dorment, jusqu'au premier réveil. Deux fils qui
    attendent 5 s chacun en même temps ne font donc passer que 5 s, comme sur le réseau réel."""

    def __init__(self, horloge) -> None:
        self.horloge = horloge
        self._condition = threading.Condition()
        self._vivants = 0
        self._dormeurs: dict[int, datetime] = {}

    def attendre(self, secondes: float) -> None:
        with self._condition:
            if self._vivants == 0:
                self.horloge.attendre(secondes)
                return
            moi = threading.get_ident()
            reveil = self.horloge.heure + timedelta(seconds=secondes)
            self._dormeurs[moi] = reveil
            self._avancer()
            while self.horloge.heure < reveil:
                self._condition.wait()
            del self._dormeurs[moi]

    def _avancer(self) -> None:
        if self._dormeurs and len(self._dormeurs) == self._vivants:
            self.horloge.heure = max(self.horloge.heure, min(self._dormeurs.values()))
            self._condition.notify_all()

    def alterner(self, groupes):
        resultats: list = [None] * len(groupes)

        def fil(i, taches):
            try:
                resultats[i] = [tache() for tache in taches]
            finally:
                with self._condition:
                    self._vivants -= 1
                    self._avancer()

        with self._condition:
            self._vivants = len(groupes)
        fils = [threading.Thread(target=fil, args=(i, g)) for i, g in enumerate(groupes)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        return resultats
