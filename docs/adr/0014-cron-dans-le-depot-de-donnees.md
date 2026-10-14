# Le cron tourne dans le dépôt de données

Le workflow planifié du cron vit dans `vigie-vaud-donnees`, et non à côté de `pipeline/` dans le dépôt principal. Son
`GITHUB_TOKEN` suffit ainsi pour écrire les données et publier le dépôt sur Pages : il n'y a aucun secret à garder ni à
renouveler. Et comme le cron committe à chaque passage dans le dépôt qui le porte, GitHub ne désactive pas son
`schedule` après 60 jours sans activité, ce qui arriverait au dépôt principal entre deux jalons. Le dépôt de données ne
contient qu'un déclencheur (`schedule`, `workflow_dispatch`, `concurrency`, `permissions`) qui appelle le workflow
réutilisable `.github/workflows/cron.yml@main` du dépôt principal. La logique évolue donc avec `pipeline/`, dans les
mêmes PR.

## Considered Options

- **Cron dans le dépôt principal** : il faut une clé de déploiement, un PAT ou une GitHub App pour écrire dans le dépôt
  de données, et un moyen de maintien en vie contre la désactivation après 60 jours, que GitHub ne documente pas.
- **Workflow complet dans le dépôt de données** : chaque évolution du cron demanderait un commit dans un autre dépôt
  que son code.

## Consequences

- Les issues `panne-source` s'ouvrent dans le dépôt de données, que le `GITHUB_TOKEN` peut écrire ; la page Couverture
  renvoie vers leur liste filtrée.
- Le dépôt de données est public dès sa création, et le workflow réutilisable n'est appelable qu'une fois le dépôt
  principal public : le cron n'est activé qu'au passage public de la fin de J0, et on le lance en local avant.
- Le dépôt de données est publié par GitHub Actions (`upload-pages-artifact`, `deploy-pages`) dans le même job, après
  le commit qui sert d'archive : ni limite de builds Pages, ni doute sur le déclenchement par un push du
  `GITHUB_TOKEN`.
