"""Année des données de référence : les éditions des sources Préparées lues par `communes.py`, `terre.py` et
`hotels_de_ville.py`. Une fusion de communes la fait changer : voir `docs/fusions-de-communes.md`."""

# Édition de swissBOUNDARIES3D (état au 1er janvier de cette année) et année où l'outil d'initialisation des hôtels
# de ville a lu l'annuaire de l'UCV et le répertoire des adresses : on les relit ensemble à chaque fusion.
ANNEE = 2026

# Édition de swissTLMRegio, d'où viennent les lacs. Elle paraît à l'automne (2026 : le 23 septembre), pas au
# 1er janvier, et les lacs ne changent pas avec une fusion : elle ne suit pas ANNEE.
EDITION_LACS = 2026
