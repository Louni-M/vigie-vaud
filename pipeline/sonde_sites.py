"""La sonde des sites communaux (ADR 0010) : une seule implémentation pour toutes les plateformes.

`sonder_site` lit la page de liste des Séances d'une commune scrapée (`site.seances`) par le robot communal, sous le
nom `VigieVaud-sonde`, et y cherche le marqueur de sa variante, déclaré dans la section `plateformes` de
`sources.json`. Aucune ligne de code n'est propre à une plateforme : une refonte du site fait disparaître le
marqueur. Rien de la page n'est conservé.

**Pannes** : erreur HTTP, délai dépassé, site injoignable, erreur TLS, page illisible, page de liste interdite par
`robots.txt` (« le site refuse les robots »), réseau bloqué (« accès refusé »), marqueur absent. **Pas des pannes** :
une liste vide (le marqueur est celui du tableau, présent même sans ligne) ni une liste dont aucune ligne ne se lit,
qui ne met en échec que l'import.
"""

from __future__ import annotations

from collections.abc import Sequence

from robot_communal import (
    CrawlDelayTropLong,
    DelaiDepasse,
    ErreurHttp,
    ErreurTls,
    Injoignable,
    PageIllisible,
    PageInterdite,
    PageNonLue,
    PlafondAtteint,
    ReseauBloque,
    Robot,
    RobotsIndisponible,
)
from schema import Plateforme, Source


def sonder_site(robot: Robot, source: Source, plateformes: Sequence[Plateforme]) -> str | None:
    """Sonde le site de `source` : `None` si la page de liste répond avec le marqueur de sa variante, sinon le motif
    court de l'échec (« HTTP 503 », « marqueur absent »…). Lève `CrawlDelayTropLong` quand le `Crawl-delay` du site
    est trop long pour qu'il soit lu : ce n'est ni un succès ni une panne, et la page n'est pas demandée."""
    site = source.site
    if site is None:
        raise ValueError(f"{source.id} : pas de bloc `site`")
    plateforme = next((p for p in plateformes if p.id == site.plateforme), None)
    variante = next((v for v in plateforme.variantes if v.id == site.variante), None) if plateforme else None
    if variante is None:
        return f"variante {site.plateforme}/{site.variante} non déclarée"
    try:
        page = robot.pour(source.id).lire(site.seances, "sonde")
    except CrawlDelayTropLong:
        raise
    except ReseauBloque:
        return "accès refusé"
    except PlafondAtteint:
        return "plafond atteint"
    except RobotsIndisponible as e:
        return f"robots.txt en erreur ({e.raison})"
    except PageInterdite:
        return "le site refuse les robots"
    except ErreurHttp as e:
        return f"HTTP {e.statut}"
    except DelaiDepasse:
        return "délai dépassé"
    except ErreurTls:
        return "erreur TLS"
    except Injoignable:
        return "site injoignable"
    except PageIllisible:
        return "page illisible"
    except PageNonLue:
        return "page non lue"
    return None if variante.marqueur in page.texte else "marqueur absent"
