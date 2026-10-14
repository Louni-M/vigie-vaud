# Le schéma commun vient des modèles Pydantic du cron

Le JSON du dépôt de données et le fichier de déclaration des sources (`sources.json`) suivent un schéma commun
(ADR-0005). Sa source est un ensemble de modèles Pydantic dans `pipeline/` : on en tire le JSON Schema, puis les types
TypeScript du site avec `json-schema-to-typescript`. Le producteur est Python et valide à l'écriture grâce à ces
modèles ; il n'y a qu'un endroit à modifier. Écarté : un JSON Schema écrit à la main (verbeux, deux générateurs) et un
schéma écrit en TypeScript (le cron dépendrait de Node).

## Conséquences

- Le JSON Schema et les types générés sont versionnés ; la CI vérifie qu'une nouvelle génération ne change rien. Le
  site se construit sans Python.
- Chaque fichier du dépôt de données porte une enveloppe `version` (majeure) et `genere` (heure du passage, UTC).
  Seul un changement incompatible augmente `version` ; le site refuse une version qu'il ne connaît pas, sans autre
  validation à la lecture.
- Le JSON Schema est aussi publié dans `schema/` du dépôt de données, pour qui voudrait réutiliser les données.
