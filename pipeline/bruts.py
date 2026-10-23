"""Les enregistrements bruts d'un conseil, tels que les rendent les deux adaptateurs de l'import (ADR 0010) :
OpenParlData (`conseils.importer`) et les sites des communes (`sites_communaux.lire_site`)."""

from __future__ import annotations

from dataclasses import dataclass, field

from schema import Conseil


@dataclass
class Bruts:
    """Les Objets (*affairs*) et les Séances (*meetings*) d'un conseil, relations développées, à la forme
    d'OpenParlData : un site communal rend la même forme, réduite aux champs que l'import lit."""

    conseil: Conseil
    objets: list[dict] = field(default_factory=list)
    seances: list[dict] = field(default_factory=list)
