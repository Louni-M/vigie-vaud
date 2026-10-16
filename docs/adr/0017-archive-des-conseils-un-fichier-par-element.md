# Archive des conseils : un fichier par élément, fichiers de lecture reconstruits

Le cron écrit chaque Objet et chaque Séance dans son propre fichier du dépôt de données
(`conseils/vd/objets/26_INT_140.json`, `conseils/5586/seances/2026-10-06.json`) : c'est l'archive de l'ADR-0008, et
le site le charge quand on ouvre l'élément. Ce que le site lit pour lister (index des conseils, fil, listes par conseil
et par année, « Au Grand Conseil » par commune) est un ensemble de **fichiers de lecture** que le cron reconstruit en
entier depuis l'archive à chaque import. Un élément est nommé par son conseil (`body_key` en minuscules, le n° OFS pour
une commune) et par la référence que lui donne le conseil : le numéro d'un Objet, le jour d'une Séance. L'`id`
d'OpenParlData n'est qu'un champ.

Écartés : un fichier par conseil et par année (chaque changement réécrit un gros bloc et le site charge du détail
inutile) ; un fichier par conseil (8 Mo pour le Grand Conseil) ; des index mis à jour pas à pas (ils peuvent diverger
de l'archive) ; l'`id` d'OpenParlData comme nom de fichier (rien ne garantit qu'une réimportation le conserve).

## Conséquences

- Environ 11 000 petits fichiers, dont l'historique git se lit élément par élément.
- Le cron compare chaque fichier à l'ancien sans `genere` et ne réécrit que ce qui change : le `genere` d'un fichier
  est l'heure de son dernier vrai changement. Seul `conseils/import.json` (dernier import réussi de chaque conseil, chacun importé à part) change chaque jour.
- L'import ne supprime jamais un élément : une absence chez OpenParlData n'efface rien de l'archive. Seule une
  réécriture à la main (ADR-0007) retire quelque chose.
- Les fichiers de lecture se recalculent sans import : un changement de leur forme, de la règle de rattachement ou de
  `communes.json` se règle par une reconstruction, ou par le rattrapage quand il faut relire OpenParlData.
- Les communes y sont désignées par leur n° OFS ; le site les traduit en slug par `communes.json`.
