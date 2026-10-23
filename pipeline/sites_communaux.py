"""Lecture des conseils sur les sites des communes (ADR 0010) : le second adaptateur de l'import des conseils, à côté
d'OpenParlData.

`lire_site` lit le conseil d'une source communale (bloc `site`) par le robot communal, dans la fenêtre du passage,
et rend les mêmes `Bruts` qu'OpenParlData (*affairs* et *meetings*, relations développées, réduits aux champs que
l'import lit), que la suite de l'import (`vers_archive`, `lecture`, `ecrire`) traite comme les autres. Chaque
plateforme a son module de lecture, avec une seule opération publique ; ses variantes et son analyse des pages
restent privées.

**Fenêtre** : le passage ordinaire relit les pages de liste en entier et n'ouvre les pages d'une Séance ou d'un
Objet que pour ceux des 6 derniers mois et à venir ; le rattrapage ouvre tout. Il n'y a pas de « depuis » pour un
site. Un élément illisible est sauté et noté dans le journal du passage ; une liste dont aucune ligne ne se lit lève
une erreur, qui met l'import de la commune en échec.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable, Sequence
from datetime import date

import lecture_iweb
from bruts import Bruts
from robot_communal import Robot
from schema import Plateforme, Source

MOIS_DE_LA_FENETRE = 6

# Le module de lecture de chaque plateforme : `lire(robot, source, depuis)`, où `depuis` est le premier jour de la
# fenêtre (`None` : tout).
LECTEURS: dict[str, Callable[[Robot, Source, date | None], Bruts]] = {"i-web": lecture_iweb.lire}


def mois_plus_tot(jour: date, mois: int) -> date:
    """Le même jour, `mois` mois plus tôt (le dernier du mois s'il n'existe pas)."""
    annee, rang = divmod(jour.year * 12 + jour.month - 1 - mois, 12)
    return date(annee, rang + 1, min(jour.day, calendar.monthrange(annee, rang + 1)[1]))


def debut_de_fenetre(jour: date) -> date:
    """Le premier jour de la fenêtre du passage ordinaire : le même jour, 6 mois plus tôt."""
    return mois_plus_tot(jour, MOIS_DE_LA_FENETRE)


def lire_site(
    robot: Robot, source: Source, plateformes: Sequence[Plateforme], jour: date, rattrapage: bool = False
) -> Bruts:
    """Le conseil de `source` lu sur le site de sa commune, au passage du `jour` (à Lausanne) : les Séances et les
    Objets des 6 derniers mois et à venir, ou tous pour un `rattrapage`. Lève `ValueError` pour une plateforme ou une
    variante non déclarée, ou sans module de lecture, et l'erreur du robot quand un réseau bloqué ou le plafond de
    requêtes a interrompu la lecture."""
    site = source.site
    if site is None or source.conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    plateforme = next((p for p in plateformes if p.id == site.plateforme), None)
    if plateforme is None or site.plateforme not in LECTEURS:
        raise ValueError(f"{source.id} : plateforme {site.plateforme} non déclarée ou sans module de lecture")
    if not any(v.id == site.variante for v in plateforme.variantes):
        raise ValueError(f"{source.id} : variante {site.variante} non déclarée dans {plateforme.nom}")
    lecteur = robot.pour(source.id)
    bruts = LECTEURS[site.plateforme](lecteur, source, None if rattrapage else debut_de_fenetre(jour))
    # Un réseau bloqué ou le plafond atteint en cours de lecture met l'import en échec, même si le module de lecture
    # a sauté la page : l'import sera refait en entier au passage suivant.
    interruption = lecteur.interruption()
    if interruption is not None:
        raise interruption
    return bruts
