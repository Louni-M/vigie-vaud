"""Ce que les modules de lecture des plateformes partagent pour mesurer un site, sans rien savoir d'une plateforme :
la mémoire des pages lues par le robot pendant un lancement du script de préparation des sources
(`preparation_sources.py`), la mesure qu'un module en tire, et le robot qui rejoue la lecture d'un module pour
compter les requêtes d'un passage ordinaire (`RobotCompteur`, sans réseau : `RobotSansReseau`).

Chaque module de lecture (`sites_communaux.LECTEURS`) mesure les sites de sa plateforme par deux opérations, à côté
de `lire` : `mesurer` (la plateforme réelle, la variante et les pages d'une commune, d'après sa page du conseil et
les pages déjà déclarées) et `requetes` (les requêtes que coûterait sa lecture au passage ordinaire). Le script de
préparation ne connaît que ces deux opérations.
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from robot_communal import PageNonLue, Reponse, Robot
from schema import Coreapi


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
    recherches: list[Coreapi] = field(default_factory=list)  # les recherches Quicksite de la variante `coreapi`
    niveau: list[str] | None = None
    requetes: int | None = None
    remarques: list[str] = field(default_factory=list)


class RobotCompteur:
    """Un robot qui rend les pages que lui donne `lire` et compte les requêtes que le passage ordinaire ferait pour
    elles : deux pour une page redirigée, une sinon, une aussi pour une page non lue. Avec `PagesLues.lire`, une page
    qui manque est lue par le robot du script, une fois par lancement."""

    def __init__(self, lire: Callable[[str], Reponse | PageNonLue]) -> None:
        self._lire = lire
        self.requetes = 0

    def lire(self, url: str, role: str) -> Reponse:
        page = self._lire(url)
        self.requetes += 1 if isinstance(page, PageNonLue) or page.url == url else 2
        if isinstance(page, PageNonLue):
            raise page
        return page


class RobotSansReseau(RobotCompteur):
    """Le `RobotCompteur` des seules pages déjà lues, sans réseau : une page jamais lue est rendue vide et coûte ce
    que dit `cout` (le module de lecture sait si ses liens stables sont redirigés)."""

    def __init__(self, pages: Mapping[str, Reponse | PageNonLue], cout: Callable[[str], int]) -> None:
        super().__init__(pages.__getitem__)
        self._pages = pages
        self._cout = cout

    def lire(self, url: str, role: str) -> Reponse:
        if url in self._pages:
            return super().lire(url, role)
        self.requetes += self._cout(url)
        return Reponse(url, 200, "", {})


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
