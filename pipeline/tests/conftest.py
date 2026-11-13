"""La suite du pipeline passe hors ligne : aucune résolution de nom ne doit partir vers le vrai DNS.

Le garde-fou est un crochet d'audit (`sys.addaudithook`) installé avant l'import de tout module du pipeline : il
intercepte aussi les `socket.gethostbyname` liés comme valeur par défaut (`passage(resoudre=...)`), qu'aucun
`monkeypatch` posé après l'import n'atteindrait. Il lève une erreur, que le code testé peut attraper (le robot
communal attrape `OSError`), et note l'hôte : le test qui a tenté la résolution échoue à son démontage.
"""

import importlib.util
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

# Tests de la préparation des communes : ils importent la pile géographique (groupe `geo` de pyproject.toml), que le
# cron n'installe pas. Sans elle, ils ne sont pas collectés et le reste de la suite passe ; avec elle, ils portent
# le marqueur `geo` (`uv run --group geo pytest -m geo` ne lance qu'eux, et échoue s'il n'en trouve aucun).
TESTS_GEO = ["test_communes.py", "test_hotels_de_ville.py"]
GEO_INSTALLE = importlib.util.find_spec("geopandas") is not None
collect_ignore = [] if GEO_INSTALLE else TESTS_GEO


def pytest_report_header():
    if not GEO_INSTALLE:
        return f"groupe geo absent : {', '.join(TESTS_GEO)} non collectés (uv run --group geo pytest pour les lancer)"
    return None


def pytest_collection_modifyitems(items):
    for item in items:
        if item.path.name in TESTS_GEO:
            item.add_marker(pytest.mark.geo)


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
