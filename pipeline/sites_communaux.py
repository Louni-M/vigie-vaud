"""Lecture des conseils sur les sites des communes (ADR 0010) : le second adaptateur de l'import des conseils, à côté
d'OpenParlData.

`lire_site` lit le conseil d'une source communale (bloc `site`) par le robot communal, dans la fenêtre du passage,
et rend les mêmes `Bruts` qu'OpenParlData (*affairs* et *meetings*, relations développées, réduits aux champs que
l'import lit), que la suite de l'import (`vers_archive`, `lecture`, `ecrire`) traite comme les autres.

**Une plateforme se déclare en un seul endroit** : la déclaration `PLATEFORME` de son module de lecture
(`socle_lecture.PlateformeLue`), inscrite dans `PLATEFORMES`. Elle porte son nom et son éditeur, ses variantes (leur
marqueur de sonde, les niveaux qu'elles permettent, leur lecture et leur reconnaissance par la mesure des sites) et
la mesure de ses sites. La sonde (`sonde_sites`), l'import (`lire_site`), la mesure des sites (`mesure_sites`) et le
script de préparation des sources (`preparation_sources`) ne lisent que cette déclaration : ajouter une variante,
c'est ajouter une `VarianteLue` à sa plateforme ; ajouter une plateforme, c'est écrire son module et l'inscrire ici.
Ce que la déclaration ne couvre pas :

- la section `plateformes` de `sources.json`, que lisent le site (nom, éditeur) et les règles de déclaration des
  sources (`preparation_sources.verifier_declarations`), en est une copie (`PlateformeLue.declaration`), que les
  tests comparent à la déclaration : ils échouent tant qu'elle n'est pas recopiée ;
- chaque variante a son échantillon (`echantillon_sites.ECHANTILLONS`, ADR 0010), que les tests réclament aussi ;
- une variante qui déclare d'autres paramètres de site, comme les recherches `coreapi` de Quicksite, les ajoute au
  bloc `site` (`schema.Site`), à `mesure_sites.Mesure` et à la comparaison du script de préparation.

**Fenêtre** : le passage ordinaire relit les pages de liste en entier et n'ouvre les pages d'une Séance ou d'un
Objet que pour ceux des 6 derniers mois et à venir ; le rattrapage ouvre tout. Il n'y a pas de « depuis » pour un
site. Un élément illisible est sauté et noté dans le journal du passage ; une liste dont aucune ligne ne se lit lève
une erreur, qui met l'import de la commune en échec.
"""

from __future__ import annotations

import calendar
from datetime import date

import lecture_iweb
import lecture_quicksite
from bruts import Bruts
from robot_communal import Robot
from schema import Site, Source
from socle_lecture import PlateformeLue, VarianteLue

MOIS_DE_LA_FENETRE = 6

# Les plateformes déclarées, par identifiant : la déclaration `PLATEFORME` de chaque module de lecture.
PLATEFORMES: dict[str, PlateformeLue] = {p.id: p for p in (lecture_iweb.PLATEFORME, lecture_quicksite.PLATEFORME)}


def variante_de(site: Site) -> VarianteLue | None:
    """La variante du site d'une commune, ou `None` si sa plateforme ou sa variante n'est pas déclarée."""
    plateforme = PLATEFORMES.get(site.plateforme)
    return plateforme.variante(site.variante) if plateforme else None


def mois_plus_tot(jour: date, mois: int) -> date:
    """Le même jour, `mois` mois plus tôt (le dernier du mois s'il n'existe pas)."""
    annee, rang = divmod(jour.year * 12 + jour.month - 1 - mois, 12)
    return date(annee, rang + 1, min(jour.day, calendar.monthrange(annee, rang + 1)[1]))


def debut_de_fenetre(jour: date) -> date:
    """Le premier jour de la fenêtre du passage ordinaire : le même jour, 6 mois plus tôt."""
    return mois_plus_tot(jour, MOIS_DE_LA_FENETRE)


def lire_site(robot: Robot, source: Source, jour: date, rattrapage: bool = False) -> Bruts:
    """Le conseil de `source` lu sur le site de sa commune, au passage du `jour` (à Lausanne) : les Séances et les
    Objets des 6 derniers mois et à venir, ou tous pour un `rattrapage`. Lève `ValueError` pour une plateforme ou une
    variante non déclarée, et l'erreur du robot quand un réseau bloqué ou le plafond de requêtes a interrompu la
    lecture."""
    site = source.site
    if site is None or source.conseil is None:
        raise ValueError(f"{source.id} : ni bloc `site` ni bloc `conseil`")
    plateforme = PLATEFORMES.get(site.plateforme)
    if plateforme is None:
        raise ValueError(f"{source.id} : plateforme {site.plateforme} non déclarée ou sans module de lecture")
    if plateforme.variante(site.variante) is None:
        raise ValueError(f"{source.id} : variante {site.variante} non déclarée dans {plateforme.nom}")
    lecteur = robot.pour(source.id)
    bruts = plateforme.lire(lecteur, source, None if rattrapage else debut_de_fenetre(jour))
    # Un réseau bloqué ou le plafond atteint en cours de lecture met l'import en échec, même si le module de lecture
    # a sauté la page : l'import sera refait en entier au passage suivant.
    interruption = lecteur.interruption()
    if interruption is not None:
        raise interruption
    return bruts
