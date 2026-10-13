# Trois voies d'accès aux données, sans serveur

Le site n'a pas de serveur. Chaque source passe par l'une de trois voies d'accès :

1. **Direct**, la voie par défaut : le navigateur appelle la source dès qu'elle le permet (CORS ouvert, pas de
   clé). Pas d'infrastructure, des données toujours à jour, et rien n'est rediffusé. Pour les permis, la norme
   DCG 8401 interdit d'ailleurs la rediffusion des données CAMAC sans autorisation.
2. **Cron** : un workflow GitHub Actions (Python + uv, dans `pipeline/`, toutes les 30 min) pour les flux RSS et
   les scrapers. Il écrit du JSON dans le dépôt de données (voir ADR-0005).
3. **Worker** : un Worker Cloudflare (offre gratuite), seulement en phase 2, pour relayer les API temps réel à
   clé ou sans CORS (DATEX II, GTFS-RT, SIRI-SX), avec un cache commun à tous les visiteurs.

## Conséquences

On ne passe à un vrai serveur que si des alertes ou une recherche plein texte deviennent nécessaires.
