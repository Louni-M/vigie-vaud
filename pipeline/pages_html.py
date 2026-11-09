"""L'analyse du HTML des sites communaux, partagée par les modules de lecture des plateformes (`lecture_iweb`,
`lecture_quicksite`) : un arbre tolérant aux balises mal fermées, et le texte d'un nœud ou d'un fragment.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser

VIDES = frozenset("area base br col embed hr img input link meta source track wbr".split())


@dataclass
class Noeud:
    tag: str
    attrs: dict[str, str]
    enfants: list[Noeud | str] = field(default_factory=list)

    def attr(self, nom: str) -> str | None:
        return self.attrs.get(nom)

    def classes(self) -> list[str]:
        """Les classes de l'élément (son attribut `class`)."""
        return (self.attr("class") or "").split()

    def premier(self, condition: Callable[[Noeud], bool]) -> Noeud | None:
        """Le premier élément descendant qui remplit `condition`, dans l'ordre du document, sinon `None`."""
        return next((n for n in self.elements() if condition(n)), None)

    def texte_du_premier(self, condition: Callable[[Noeud], bool]) -> str:
        """Le texte, espaces réduites, du premier élément descendant qui remplit `condition` ; vide s'il n'y en a
        pas."""
        premier = self.premier(condition)
        return espaces(premier.texte()) if premier else ""

    def elements(self, sauf: list[Noeud] | None = None):
        """Les éléments descendants, dans l'ordre du document, sans ceux de `sauf` ni leurs descendants."""
        for e in self.enfants:
            if isinstance(e, Noeud) and not any(e is x for x in sauf or ()):
                yield e
                yield from e.elements(sauf)

    def enfants_elements(self) -> list[Noeud]:
        return [e for e in self.enfants if isinstance(e, Noeud)]

    def texte(self) -> str:
        return " ".join(e if isinstance(e, str) else e.texte() for e in self.enfants)


class _Arbre(HTMLParser):
    """Un arbre tolérant : une balise fermante sans ouvrante est ignorée, une fermante referme ce qu'elle englobe."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.racine = Noeud("#document", {})
        self._pile = [self.racine]

    def handle_starttag(self, tag, attrs):
        noeud = Noeud(tag, {k: v or "" for k, v in attrs})
        self._pile[-1].enfants.append(noeud)
        if tag not in VIDES:
            self._pile.append(noeud)

    def handle_endtag(self, tag):
        for i in range(len(self._pile) - 1, 0, -1):
            if self._pile[i].tag == tag:
                del self._pile[i:]
                return

    def handle_data(self, data):
        self._pile[-1].enfants.append(data)


def arbre(texte: str) -> Noeud:
    analyse = _Arbre()
    analyse.feed(texte)
    analyse.close()
    return analyse.racine


def texte_html(fragment: str) -> str:
    """Le texte d'un fragment HTML, balises retirées, entités décodées, espaces réduites."""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", fragment)).split())


def espaces(texte: str) -> str:
    return " ".join(texte.split())
