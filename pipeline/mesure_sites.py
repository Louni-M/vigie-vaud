"""Ce que les modules de lecture des plateformes partagent pour mesurer un site, sans rien savoir d'une plateforme :
la mémoire des pages lues par le robot pendant un lancement du script de préparation des sources
(`preparation_sources.py`), la mesure qu'un module en tire, et la lecture sans réseau qui compte les requêtes d'un
passage ordinaire.

Chaque module de lecture (`sites_communaux.LECTEURS`) mesure les sites de sa plateforme par deux opérations, à côté
de `lire` : `mesurer` (la plateforme réelle, la variante et les pages d'une commune, d'après sa page du conseil et
les pages déjà déclarées) et `requetes` (les requêtes que coûterait sa lecture au passage ordinaire). Le script de
préparation ne connaît que ces deux opérations.
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from robot_communal import PageNonLue, Reponse, Robot


class PagesLues:
    """Le robot, avec la mémoire des pages lues : une page n'est demandée qu'une fois par lancement, rôle `import`."""

    def __init__(self, robot: Robot) -> None:
        self._robot = robot
        self.pages: dict[str, Reponse | PageNonLue] = {}

    def lire(self, url: str) -> Reponse | PageNonLue:
        if url not in self.pages:
            try:
                self.pages[url] = self._robot.lire(url, "import")
            except PageNonLue as e:
                self.pages[url] = e
        return self.pages[url]

    def texte(self, url: str) -> str | None:
        page = self.lire(url)
        return page.texte if isinstance(page, Reponse) else None


@dataclass
class Mesure:
    """Ce que le site d'une commune montre. `plateforme` : l'identifiant de la plateforme mesurée, `None` si la page du
    conseil n'a pas été lue, « autre » si le site n'est pas sur la plateforme qu'on mesure (`remarques` dit pourquoi).
    `niveau` et `requetes` : le plus haut niveau que la variante permet sous le plafond, et ses requêtes au passage
    ordinaire, `robots.txt` et sonde compris."""

    plateforme: str | None
    variante: str | None = None
    seances: str | None = None
    objets: str | None = None
    membres: str | None = None
    niveau: list[str] | None = None
    requetes: int | None = None
    remarques: list[str] = field(default_factory=list)


class RobotSansReseau:
    """Un robot qui rend les pages déjà lues et compte les requêtes que le passage ordinaire ferait : deux pour une
    page lue redirigée, une sinon ; une page jamais lue est rendue vide et coûte ce que dit `cout` (le module de
    lecture sait si ses liens stables sont redirigés)."""

    def __init__(self, pages: dict[str, Reponse | PageNonLue], cout: Callable[[str], int]) -> None:
        self._pages = pages
        self._cout = cout
        self.requetes = 0

    def lire(self, url: str, role: str) -> Reponse:
        page = self._pages.get(url)
        if isinstance(page, PageNonLue):
            self.requetes += 1
            raise page
        if page is None:
            self.requetes += self._cout(url)
            return Reponse(url, 200, "", {})
        self.requetes += 1 if page.url == url else 2
        return page


def sans_journal(lire: Callable[[], object]) -> object:
    """`lire()`, le journal du module de lecture tu : une lecture sans réseau n'a rien à signaler."""
    with contextlib.redirect_stderr(io.StringIO()):
        return lire()


class _Liens(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.liens: list[tuple[str, str]] = []
        self._ouvert: list[str] | None = None
        self._href = ""

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._ouvert = dict(attrs).get("href") or "", []

    def handle_data(self, data):
        if self._ouvert is not None:
            self._ouvert.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._ouvert is not None:
            self.liens.append((self._href, " ".join(" ".join(self._ouvert).split())))
            self._ouvert = None


def liens(texte: str, url: str) -> list[tuple[str, str]]:
    """Les liens de la page vers d'autres pages du même hôte (ni l'accueil, ni une ancre de la page), dans l'ordre de la
    page, chacun une fois : (URL absolue, texte du lien)."""
    analyse = _Liens()
    analyse.feed(texte)
    hote, vus, trouves = urlsplit(url).hostname, set(), []
    for href, libelle in analyse.liens:
        absolu = urljoin(url, href).split("#")[0]
        parties = urlsplit(absolu)
        if parties.scheme not in ("http", "https") or parties.hostname != hote or absolu in vus:
            continue
        if parties.path in ("", "/"):
            continue
        vus.add(absolu)
        trouves.append((absolu, libelle))
    return trouves
