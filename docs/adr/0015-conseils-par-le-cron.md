# Les conseils passent par le cron

Les Objets et les Séances d'OpenParlData passent par le cron et le dépôt de données. Le site ne lit que ce dépôt, bien
qu'OpenParlData ait un CORS ouvert et pas de clé, ce qui permettrait la voie Direct par défaut de l'ADR-0004. Quatre
raisons :

- **Rattachement** : un objet du Grand Conseil n'atteint une commune que par son nom, cherché dans son titre et le
  texte de ses documents, avec des exclusions. Le navigateur ne peut pas faire ce calcul sur tout le canton à chaque
  visite. Le fil cantonal et la section « Au Grand Conseil » ont besoin du rattachement déjà calculé.
- **Archive** : l'ADR-0008 conserve les objets parlementaires sans limite de durée. OpenParlData a des trous, n'a ni
  changelog ni politique de dépréciation, et publie « actuellement » sous CC BY 4.0. L'historique git du dépôt de
  données est donc l'archive.
- **Usage loyal** : OpenParlData demande au plus 1 requête/s, 10 000 par jour, et un User-Agent avec un contact. Le
  cron s'y tient ; le navigateur de chaque visiteur ne pourrait pas s'identifier, et le nombre de requêtes croîtrait
  avec l'audience.
- **Fraîcheur** : OpenParlData importe une fois par nuit. Un appel Direct ne serait pas plus à jour qu'un import
  quotidien.

Écarté : la voie Direct ; un index par le cron et le détail d'un objet en Direct au clic (deux chemins, et le détail
disparaît pendant une panne) ; une voie par conseil (pas de code propre à un conseil).

## Conséquences

- Les conseils sont importés une fois par jour, au premier passage du cron après une heure fixe. L'import demande ce
  qui a changé depuis le jour du dernier import réussi (`from_updated_at`), avec au moins un jour de recouvrement, et
  ne committe que les vrais changements : `updated_at` change à chaque réimportation d'OpenParlData. Un import en échec
  est refait au passage suivant.
- Tout l'historique disponible est importé une fois, à la main, avant la mise en ligne de J1 (rattrapage de
  l'ADR-0008). Les trous comblés plus tard par OpenParlData arrivent par l'import quotidien.
- Le texte des documents ne sert qu'au rattachement et n'est pas conservé : le dépôt de données garde le rattachement
  et les liens vers les PDF. Un changement de la règle de rattachement se recalcule en relançant le rattrapage.
- L'import filtre les séances du Conseil d'État et ne répète jamais un paramètre de requête (le cache du serveur ne
  garde que sa dernière valeur).
