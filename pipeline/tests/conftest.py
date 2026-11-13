"""La suite du pipeline passe hors ligne : aucune résolution de nom ne doit partir vers le vrai DNS.

Le garde-fou est un crochet d'audit (`sys.addaudithook`) installé avant l'import de tout module du pipeline : il
intercepte aussi les `socket.gethostbyname` liés comme valeur par défaut (`passage(resoudre=...)`), qu'aucun
`monkeypatch` posé après l'import n'atteindrait. Il lève une erreur, que le code testé peut attraper (le robot
communal attrape `OSError`), et note l'hôte : le test qui a tenté la résolution échoue à son démontage.
"""

import ipaddress
import os
import sys

import pytest
from faux_depot import IDENTITE, DepotNu

_EVENEMENTS_DNS = {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex"}
_tentatives: list[str] = []


class ResolutionInterdite(OSError):
    """Une résolution de nom réelle pendant les tests."""


def _litteral(hote) -> bool:
    if hote is None:
        return True
    if isinstance(hote, bytes):
        hote = hote.decode("ascii", "replace")
    try:
        ipaddress.ip_address(hote)
    except ValueError:
        return hote == "localhost"
    return True


def _garde_dns(evenement: str, args: tuple) -> None:
    if evenement in _EVENEMENTS_DNS and not _litteral(args[0]):
        _tentatives.append(str(args[0]))
        raise ResolutionInterdite(f"résolution DNS réelle interdite dans les tests : {args[0]}")


sys.addaudithook(_garde_dns)


@pytest.fixture(autouse=True)
def _hors_ligne():
    _tentatives.clear()
    yield
    tentees = sorted(set(_tentatives))
    _tentatives.clear()
    assert not tentees, f"{len(tentees)} résolution(s) DNS réelle(s) tentée(s) : {', '.join(tentees)}"


@pytest.fixture
def depot_nu(tmp_path, monkeypatch):
    """Un dépôt nu amorcé (`faux_depot.DepotNu`), avec git isolé de la configuration de la machine et l'identité
    du workflow."""
    for variable, valeur in IDENTITE.items():
        monkeypatch.setenv(variable, valeur)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return DepotNu(tmp_path)
