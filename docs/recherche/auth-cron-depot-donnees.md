# Écrire depuis un workflow dans un autre dépôt : authentification et limites du cron

Recherche pour l'issue #13 (carte #1, J0 Socle spécifié). Question : le cron vit dans le dépôt principal
(`vigie-vaud`, public) et doit écrire dans le dépôt de données (`vigie-vaud-donnees`, ADR 0005), sur le même
**compte personnel** (pas d'organisation). Quel moyen d'authentification, que coûte chacun, et quelles limites
le `schedule` de GitHub Actions impose-t-il ?

Méthode : lecture de docs.github.com (version Markdown des pages via `https://docs.github.com/api/article/body?pathname=…`),
du README de [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token) (dernière
version : `v3.3.0`, 12 octobre 2026) et du changelog GitHub, le 14 octobre 2026. Ce qui est une déduction et non
une phrase de la documentation est signalé comme tel.

## Synthèse

| | Clé de déploiement (SSH, écriture) | Jeton à portée fine (fine-grained PAT) | GitHub App (`create-github-app-token`) |
|---|---|---|---|
| **Portée** | Un seul dépôt ; Git seulement (clone et push), pas d'API REST/GraphQL | Les dépôts choisis (« Only select repositories ») d'un seul propriétaire, avec des permissions choisies (ici `Contents: write`) ; plus la lecture de tous les dépôts publics | Les dépôts où l'App est installée, avec les permissions de l'App ; l'action peut restreindre le jeton à certains dépôts et permissions |
| **Expiration** | Aucune | 1 à 366 jours, ou aucune ; 30 jours par défaut ; révoqué aussi après un an sans usage | Jeton d'installation : 1 h, révoqué par l'action en fin de job. Clé privée de l'App : aucune expiration |
| **Renouvellement** | Manuel (supprimer, recréer) | Manuel : un jeton expiré ne se restaure pas, il faut en créer un et remplacer le secret | Aucun pour le jeton (recréé à chaque job) ; rotation manuelle de la clé privée (jusqu'à 25 clés pour tourner sans coupure) |
| **Secret à stocker** | Clé privée SSH (sans phrase de passe) dans les secrets de `vigie-vaud` ; clé publique dans `vigie-vaud-donnees` avec « Allow write access » | Le jeton `github_pat_…` | Clé privée de l'App (secret) + client ID (variable de configuration) |
| **Fuite** | Écriture Git sur `vigie-vaud-donnees` seulement, sans limite de durée jusqu'à suppression de la clé | Ce que permettent ses permissions sur les dépôts choisis, au nom de l'utilisateur, jusqu'à expiration ou révocation (Git **et** API) | Fuite de la clé privée : « authentification persistante en tant que l'App », donc des jetons sur tous les dépôts où elle est installée, avec toutes ses permissions, jusqu'à suppression de la clé |
| **Le push déclenche-t-il les workflows du dépôt cible ?** | Oui (seul `GITHUB_TOKEN` est exclu ; la doc décrit le « pushed by » d'un push par clé de déploiement) | Oui (documenté) | Oui (documenté) |
| **Mise en place** | La plus simple | Simple | La plus longue (enregistrer, installer, deux valeurs à stocker) |

Le `GITHUB_TOKEN` seul ne convient pas pour écrire dans le dépôt de données : ses permissions sont limitées au
dépôt du workflow. Il suffit en revanche pour ouvrir et fermer les issues `panne-source` dans le dépôt principal,
avec `permissions: issues: write` sur le job.

Limites du `schedule` : intervalle minimal de 5 minutes ; retards aux heures chargées (en particulier au début de
chaque heure) et jobs en file parfois abandonnés, sans chiffre publié ; dans un dépôt public, désactivation
automatique après 60 jours « sans activité du dépôt », et rien dans la documentation n'indique que des commits
dans un **autre** dépôt comptent ; minutes gratuites et illimitées pour un dépôt public sur les runners standard.

Une contrainte en plus vient du dépôt de données publié sur Pages depuis une branche : chaque push y déclenche un
déploiement Pages, et Pages a une limite souple de **10 builds par heure** dans ce mode.

## 1. Les trois moyens d'écrire dans un autre dépôt

### Ce que la documentation recommande

La page sur les runners compromis classe les moyens d'accéder à un dépôt depuis un workflow « in descending
order of preference » : `GITHUB_TOKEN`, puis clé de déploiement, puis jeton de GitHub App, puis PAT ; elle
proscrit le PAT classique et les clés SSH d'un compte personnel
([Compromised runners, Cross-repository access](https://docs.github.com/en/actions/concepts/security/compromised-runners#cross-repository-access)).
Ce classement est écrit pour des organisations : la mise en garde contre le PAT « from your own account »
porte sur le cas où l'on quitte l'organisation, qui ne se pose pas sur un compte personnel.

La page sur les clés de déploiement recommande quant à elle une GitHub App « for enhanced security and
fine-grained control » ([Managing deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys)),
et celle des PAT renvoie aussi vers une App « for long-lived integrations »
([Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)).

### Clé de déploiement

- Clé SSH qui donne accès à **un seul dépôt** ; la partie publique est attachée au dépôt, pas au compte. Lecture
  seule par défaut, écriture si l'on coche « Allow write access »
  ([Managing deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys#deploy-keys)).
- Avec l'écriture, elle peut faire « the same actions as … a collaborator on a personal repository » (même page).
  Déduction : sans règle de protection de branche, elle peut pousser sur n'importe quelle branche, y compris
  celle que publie Pages.
- Inconvénients listés par GitHub : pas de phrase de passe en général, « don't have an expiry date », une clé par
  dépôt (pas de réutilisation) (même page).
- Git seulement : « cannot be used to interact with the REST or GraphQL API »
  ([Compromised runners](https://docs.github.com/en/actions/concepts/security/compromised-runners#cross-repository-access)).
- Durée de vie « Long-lived », révocation « Manual », associée au « Repository »
  ([GitHub credential types reference](https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/github-credential-types)).
- Workflows du dépôt cible : un push par clé de déploiement déclenche bien les workflows `push`. La doc précise
  que dans ce cas le champ « pushed by » de l'interface est « the repository admin who verified the deploy key »
  ([Events that trigger workflows, `push`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push)).
  Pour Pages, seuls les commits poussés avec `GITHUB_TOKEN` sont exclus (voir § 3).

### Jeton à portée fine (fine-grained PAT)

- Un seul **propriétaire de ressource** (ici le compte personnel), « Only select repositories » pour viser
  `vigie-vaud-donnees`, permissions minimales à choisir (ici `Contents: write`). Le jeton a toujours, en plus,
  « read-only access to all public repositories on GitHub »
  ([Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token)).
- Expiration : `expires_in` vaut un entier « between 1 and 366, or `none` », défaut 30 jours ; « Infinite
  lifetimes are allowed » sauf politique d'organisation, qui ne s'applique pas à un compte personnel (même page).
  Le tableau des types d'identifiants donne « up to 1 year, or no expiration »
  ([GitHub credential types reference](https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/github-credential-types)).
- À l'expiration, le jeton est révoqué automatiquement ; un jeton expiré ou révoqué ne peut pas être restauré, il
  faut en créer un nouveau. GitHub révoque aussi un PAT inutilisé depuis un an, et tout PAT poussé dans un dépôt
  public ou un gist public
  ([Token expiration and revocation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation)).
- Le jeton est « tied to the user who generated them » et agit avec les capacités de l'utilisateur, bornées par
  ses permissions ([Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)).
  Les pushes sont donc attribués au compte personnel.
- Workflows du dépôt cible : déclenchés. « you can use a GitHub App installation access token or a personal
  access token instead of `GITHUB_TOKEN` to trigger events »
  ([Triggering a workflow from a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow#triggering-a-workflow-from-a-workflow)).

### GitHub App via `actions/create-github-app-token`

- Une App peut être enregistrée sous un **compte personnel**, et installée « Only on this account »
  ([Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)).
- Mise en place : enregistrer l'App avec les permissions nécessaires, stocker son **client ID** comme variable de
  configuration, générer une **clé privée** et la stocker comme secret, installer l'App sur les dépôts voulus
  ([Making authenticated API requests with a GitHub App in a GitHub Actions workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)).
- Jeton d'installation : « An installation access token expires after 1 hour » ; l'action le révoque dans son
  étape `post` (sauf `skip-token-revoke`), il ne passe donc pas d'un job à l'autre
  ([README de `create-github-app-token`](https://github.com/actions/create-github-app-token#readme)).
- Portée du jeton : si `owner` et `repositories` sont vides, « access will be scoped to only the current
  repository ». Pour écrire dans le dépôt de données, il faut donc passer `repositories: vigie-vaud-donnees`.
  Les entrées `permission-<nom>` restreignent le jeton (par défaut, il hérite de toutes les permissions de
  l'installation) (même README).
- Le README donne la recette pour committer en tant que bot : `user.name` = `<app-slug>[bot]`, courriel
  `<id>+<app-slug>[bot]@users.noreply.github.com`, puis `gh auth setup-git` et `git push` (même README).
- Clé privée : « Private keys do not expire and instead need to be manually revoked » ; jusqu'à 25 clés par App
  pour tourner sans coupure. GitHub l'appelle « the single most valuable secret for a GitHub App » : si un
  attaquant la lit, il obtient « persistent authentication as the GitHub App »
  ([Managing private keys for GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps)).
- Workflows du dépôt cible : déclenchés (même source que pour le PAT ci-dessus).
- À noter : depuis le 2 octobre 2026, les jetons d'installation sont « stateless » et font environ 520 caractères
  au lieu de 40 ; durée de vie, portée et permissions inchangées
  ([changelog du 2 octobre 2026](https://github.blog/changelog/2026-10-02-stateless-github-app-installation-tokens-rolled-out)).
  Sans effet ici tant que le jeton n'est stocké nulle part.

### `GITHUB_TOKEN` (pour mémoire)

- « The token's permissions are limited to the repository that contains your workflow » ; il expire à la fin du
  job, 6 h au plus sur les runners hébergés ([GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)).
  Il ne peut donc pas écrire dans `vigie-vaud-donnees`.
- « events triggered by the `GITHUB_TOKEN` will not create a new workflow run », sauf `workflow_dispatch`,
  `repository_dispatch` et certains `pull_request` (même page).

## 2. Ouvrir les issues `panne-source` avec `GITHUB_TOKEN`

**Oui**, dans le dépôt qui porte le workflow.

- Le tutoriel officiel montre exactement ce cas : un job avec `permissions: issues: write` qui lance
  `gh issue --repo ${{ github.repository }} create …`, et une variante par l'API REST
  ([Use GITHUB_TOKEN for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)).
- La clé `permissions` modifie les permissions par défaut du `GITHUB_TOKEN`, en ajoutant ou en retirant ; dès
  qu'on en précise une, les autres passent à `none` ; `issues: write` « permits an action to add a comment to an
  issue » ([Workflow syntax, `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)).
  Le job du cron devra donc lister aussi ce dont il a besoin par ailleurs (par exemple `contents: read`).
- Par défaut, un nouveau dépôt d'un compte personnel a le réglage restreint (`contents` et `packages` en lecture)
  ([Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#setting-the-permissions-of-the-github_token-for-your-repository) ;
  [changelog du 2 février 2023](https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/)).
  La clé `permissions` du workflow suffit à demander `issues: write` ; aucun réglage du dépôt n'est à changer.
- Conséquence de la règle ci-dessus : une issue ouverte avec `GITHUB_TOKEN` ne déclenche pas de workflow
  `issues` dans le dépôt principal.
- Limite d'API : 1 000 requêtes par heure et par dépôt pour `GITHUB_TOKEN`
  ([Actions limits](https://docs.github.com/en/actions/reference/limits)).
- Déduction : si le cron vivait dans le dépôt de données, son `GITHUB_TOKEN` ne pourrait pas ouvrir d'issue dans le
  dépôt principal ; il faudrait alors un des trois moyens ci-dessus (sauf la clé de déploiement, qui n'a pas
  accès à l'API).

## 3. Limites du `schedule` sur un dépôt public

Source principale : [Events that trigger workflows, `schedule`](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

- **Intervalle minimal** : « The shortest interval you can run scheduled workflows is once every 5 minutes. »
- **Heure** : UTC par défaut ; un champ `timezone` (chaîne IANA) est désormais accepté, avec un décalage à
  l'heure valide suivante lors du passage à l'heure d'été.
- **Branche** : seulement la branche par défaut, et le fichier de workflow doit y exister.
- **Retards et sauts** : « The `schedule` event can be delayed during periods of high loads … High load times
  include the start of every hour. If the load is sufficiently high enough, some queued jobs may be dropped. »
  GitHub conseille une minute décalée dans l'heure. La documentation ne donne **aucun chiffre** (ni retard type,
  ni taux de saut) ; tout chiffre viendrait d'observations tierces, hors des sources retenues ici.
- **Désactivation après 60 jours** : « In a public repository, scheduled workflows are automatically disabled
  when no repository activity has occurred in 60 days » (même page, et
  [Disabling and enabling a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)).
  - La documentation **ne définit pas** « repository activity ». Les seules occurrences dans le dépôt
    `github/docs` sont ces deux phrases (recherche de code du 14 octobre 2026).
  - Elle parle de l'activité **du dépôt** qui porte le workflow. Rien n'indique que les commits du cron dans
    `vigie-vaud-donnees` comptent pour `vigie-vaud` ; il ne faut pas compter dessus. Qu'une issue ouverte ou
    fermée par le cron dans `vigie-vaud` compte comme activité n'est pas documenté non plus.
  - Réactivation : bouton « Enable workflow » de l'onglet Actions, `gh workflow enable`, ou l'API REST ; un commit
    d'un utilisateur ayant l'écriture qui modifie le `cron` réactive aussi le workflow.
  - Seuls les dépôts **publics** sont concernés. Les notifications d'un workflow planifié vont à l'utilisateur qui
    a modifié la syntaxe `cron` en dernier.
- **Minutes** : « GitHub Actions usage is free for … public repositories that use standard GitHub-hosted
  runners » ; un dépôt privé d'un compte GitHub Free a 2 000 minutes par mois
  ([GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).
- **Autres limites** : 6 h par job sur un runner hébergé, 20 jobs simultanés sur le plan Free
  ([Actions limits](https://docs.github.com/en/actions/reference/limits)).

### Le dépôt de données sur Pages

- Si Pages publie depuis une branche, chaque déploiement passe par un workflow Actions du dépôt de données
  ([Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)).
- « Commits pushed by a GitHub Actions workflow that uses the `GITHUB_TOKEN` do not trigger a GitHub Pages
  build » (même page et [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)). Les
  trois moyens ci-dessus ne sont pas visés : leurs pushes déclenchent le déploiement. La même page ajoute que si
  le site ne se publie pas, il faut qu'une personne « with admin permissions and a verified email address » ait
  poussé sur la source de publication.
- « GitHub Pages sites have a *soft* limit of 10 builds per hour. This limit does not apply if you build and
  publish your site with a custom GitHub Actions workflow. » Un déploiement qui dépasse 10 minutes échoue ; 1 Go
  au plus pour le site publié
  ([GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)).
- Déduction : un cron toutes les 5 minutes qui pousse à chaque passage ferait 12 déploiements par heure, au-dessus
  de la limite souple d'une publication depuis une branche.

## Ce que cette recherche ne tranche pas

Le choix du moyen d'authentification, de l'emplacement du cron et de sa fréquence revient au ticket suivant (#14).
Faits utiles pour ce choix :

- clé de déploiement : la plus simple, limitée à un dépôt et à Git, mais sans expiration ;
- PAT à portée fine : simple, attaché au compte, à renouveler à chaque expiration (ou sans expiration) ;
- GitHub App : jeton d'une heure, mais une clé privée sans expiration qui vaut pour tous les dépôts d'installation ;
- l'inactivité de 60 jours se compte dans le dépôt qui porte le cron, pas dans celui où il écrit ;
- Pages publiée depuis une branche plafonne en douceur à 10 déploiements par heure.

## Sources

- [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) (`schedule`, `push`)
- [Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [Disabling and enabling a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)
- [GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token)
- [Use GITHUB_TOKEN for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)
- [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions)
- [Managing GitHub Actions settings for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository)
- [Compromised runners](https://docs.github.com/en/actions/concepts/security/compromised-runners)
- [Managing deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
- [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Token expiration and revocation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation)
- [GitHub credential types reference](https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/github-credential-types)
- [Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
- [Making authenticated API requests with a GitHub App in a GitHub Actions workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)
- [Managing private keys for GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps)
- [`actions/create-github-app-token`](https://github.com/actions/create-github-app-token) (README, `v3.3.0`)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Actions limits](https://docs.github.com/en/actions/reference/limits)
- [Configuring a publishing source for your GitHub Pages site](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- Changelog GitHub : [2 février 2023, `GITHUB_TOKEN` en lecture seule par défaut](https://github.blog/changelog/2023-02-02-github-actions-updating-the-default-github_token-permissions-to-read-only/) ;
  [2 octobre 2026, jetons d'installation « stateless »](https://github.blog/changelog/2026-10-02-stateless-github-app-installation-tokens-rolled-out)
