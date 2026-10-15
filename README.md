# Vigie Vaud

Tableau de bord du canton de Vaud, commune par commune. Sa première couche, Permis (l'ancien site Chantiers
Vaud), est décrite ci-dessous.

> **Branche `prototype/live-api`.** Ce site **ne stocke ni ne rediffuse les données CAMAC**. C'est le navigateur
> de chaque visiteur qui interroge directement le service public du canton
> (`ogc.vd.ch`, couche ArcGIS `wmsVD/MapServer/537`). Aucun fichier de données cantonales n'est produit,
> versionné ou publié. La version qui héberge les données reste sur `main`, pour comparer les deux.

Carte citoyenne des demandes de permis de construire du canton de Vaud : enquêtes publiques en cours avec leur
date de fin, décisions attendues, et historique depuis 1999 (environ 112 000 dossiers). Le site informe ; il ne
prend pas position sur les projets.

- **Carte** : enquêtes en cours et procédures en attente de décision, recherche d'adresse, « autour de moi »,
  filtres par statut et par nature de travaux, historique par année, vue aérienne. L'état de la carte (dossier
  ouvert, centre, filtres) est dans l'URL : `/?d=<n°>` ouvre un dossier, `/?commune=<slug>` cadre une commune.
  Le marqueur « autour de moi » n'est jamais écrit dans l'URL ; le centre de la carte, lui, l'est (après
  « Autour de moi », un lien partagé montre donc le quartier). La page d'accueil déclare une URL canonique sans
  paramètres, que la mesure d'audience GoatCounter utilise à la place de l'adresse complète.
- **Une page par commune** (300 communes) : dossiers en cours, chiffres, demandes par année, historique.
- **Une fiche par dossier**, avec un lien à partager et les modalités de consultation du dossier.
- **Informations légales** (`/infos-legales`) : consultation, observations, oppositions et recours, avec renvois
  aux textes officiels (LATC, RLATC, LPA-VD, LAT, LTF).

Les noms de propriétaire, de requérant ou d'architecte des avis officiels ne sont pas repris. Dans les descriptions
libres, les noms de particuliers sont masqués **dans le navigateur, avant affichage**
(`web/src/lib/masquage.ts`, portage exact de `mask_names` dans `pipeline/fetch.py`, vérifié sur les 112 534
descriptions : 229 masquées, aucune différence) ; les entreprises et collectivités restent nommées.

## Fonctionnement

| Besoin | Requête au canton (depuis le navigateur) |
|---|---|
| Dossiers en cours (au chargement) | `ETAT` = enquête, ou procédure de moins de 3 ans : ~2400 dossiers, 2 pages en parallèle, ~0,4 s |
| Fiche d'un dossier | `NO_CAMAC = <n°>` (~0,2 à 0,5 s), ou par lots `NO_CAMAC IN (…)` pour la liste |
| Historique sur la carte | Points légers (n°, statut, nature, date), une année à la fois : ~4 000 points / ~60 Ko par année |
| Page commune | Points légers de l'emprise de la commune, rattachés à la commune dans le navigateur |

- Rattachement aux communes : `web/src/lib/communes.ts` (point dans polygone, sinon commune la plus proche),
  avec les limites simplifiées de `web/static/communes-limites.json`. Ces limites et l'index
  `web/static/communes.json` viennent de swisstopo (swissBOUNDARIES3D, données ouvertes). Ils sont produits par
  `pipeline/communes.py` et versionnés.
- Client ArcGIS : `web/src/lib/api.ts`. Pagination parallèle, 6 requêtes au plus en même temps, cache mémoire
  pour la visite, délai d'attente de 20 s, messages d'erreur si `ogc.vd.ch` ne répond pas. Le module refuse de
  s'exécuter hors du navigateur : ni le build ni le serveur de développement n'interrogent le canton.
- Le service accepte les appels d'autres origines (CORS ouvert) et renvoie du JSON compressé (gzip), plus léger
  ici que le PBF.

Limites du serveur cantonal, constatées le 13 octobre 2026 :

- `export` (image) n'affiche rien au-delà du 1:10 000, et `dynamicLayers` ne lève pas cette limite. Les images ne
  servent donc pas pour l'historique à l'échelle du canton : la carte charge des points légers.
- Avec un **polygone** comme filtre, le serveur tronque les résultats (la limite de 2000 s'applique avant le
  filtre spatial) et ses comptages divergent (7119, 7132 ou 7144 dossiers pour Lausanne selon la requête). On
  n'utilise donc que des **emprises rectangulaires** et des numéros de dossier.

### Compromis par rapport à `main`

- Plus de journal des changements de statut (« Évolution suivie ») : il supposait de conserver des instantanés.
- Plus de fiches dossier pré-générées : pas d'aperçu de lien ni de référencement par dossier. Les 300 pages commune
  restent pré-générées, mais sans chiffres dans le HTML.
- L'historique complet depuis 1999 représente environ 1,7 Mo, chargé année par année à la demande, contre des
  tuiles PMTiles chargées par zone.
- Le site dépend de la disponibilité de `ogc.vd.ch`.
- Gain : les dates de décision s'affichent (le pipeline ne lisait pas le format `jj/mm/aaaa` de
  `DATE_DECISION`), et les données sont toujours celles du jour.

## Structure

| Dossier | Rôle |
|---|---|
| `web/` | Site statique SvelteKit + MapLibre (fond swisstopo) ; données CAMAC lues en direct par `src/lib/api.ts` et `src/lib/couches/permis/donnees.svelte.ts` |
| `pipeline/` | `communes.py` produit l'index et les limites des communes (swisstopo). `schema.py` : modèles du schéma commun. `cron.py` : un passage du cron. `fetch.py` (version hébergée, `main`) n'est plus utilisé par le site |
| `schema/` | JSON Schema générés depuis `pipeline/schema.py` (ne pas modifier) |
| `sources.json` | Déclaration de chaque source (attribution, voie d'accès, fraîcheur, Couverture, sonde), lue par le site et le cron |
| `.github/workflows/` | Construction et publication sur GitHub Pages, sans aucune donnée CAMAC |

## Lancer en local

Prérequis : Node 24+, pnpm. [uv](https://docs.astral.sh/uv/) seulement pour régénérer les communes ou le schéma commun, et pour les tests du pipeline.

```bash
cd web && pnpm install && pnpm dev
```

Tests du site (Vitest, sans navigateur ni appel au canton) :

```bash
cd web && pnpm test
```

Limites communales (après une fusion de communes, par exemple) :

```bash
cd pipeline && uv run python communes.py
```

## Sources et schéma commun

Chaque source est déclarée une seule fois, dans `sources.json` à la racine ; toutes les attributions affichées en
viennent. La construction du site échoue si le fichier ne suit pas le schéma ou cite un n° OFS qui n'est pas une
commune actuelle.

Le schéma commun (ADR 0013) s'écrit seulement dans les modèles Pydantic de `pipeline/schema.py`. On en tire le JSON
Schema (`schema/`) puis les types du site (`web/src/lib/schema.ts`), tous deux versionnés. Après une modification
des modèles :

```bash
pnpm --dir web schema          # régénère schema/ et web/src/lib/schema.ts (uv et pnpm requis)
cd pipeline && uv run pytest   # tests du pipeline
```

## Cron et dépôt de données

Le cron (ADR 0005 et 0014) envoie une sonde à chaque source de `sources.json` qui a un bloc `sonde`, puis écrit
`etat-sources.json` et `schema/` dans le dépôt de données `vigie-vaud-donnees`, committe et pousse. Pendant J0, on le
lance en local contre un clone de ce dépôt ; `--sans-push` écrit l'état et committe sans pousser, et affiche les
issues `panne-source` qu'il ouvrirait ou fermerait au lieu de toucher à GitHub :

```bash
cd pipeline && uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push
```

Au passage public, le déclencheur `pipeline/depot-donnees/.github/workflows/cron.yml` se pose tel quel dans le dépôt
de données : il appelle toutes les 30 minutes le workflow réutilisable `.github/workflows/cron.yml`, qui fait le
passage puis publie le dépôt de données sur Pages, avec son seul `GITHUB_TOKEN`. Ce jeton sert aussi aux issues
`panne-source` : une issue « Panne : <nom de la source> » s'ouvre quand la source passe en panne (sauf si elle est
déjà ouverte), puis est commentée et fermée à son retour.

## Configuration

Les adresses du dépôt, du courriel de contact, du site public et des Pages du dépôt de données sont écrites une
seule fois, dans `config.json` à la racine. Le site les lit par `web/src/lib/config.ts`.

## Contrôles et publication

Le workflow `ci.yml` se lance sur chaque PR : `svelte-check`, la construction (qui valide `sources.json`), la
vérification qu'aucune donnée CAMAC n'est dans le site construit, la régénération du schéma commun (qui doit ne rien
changer) et les tests du pipeline (pytest).

Le workflow `publier.yml` se lance à la main. Il construit le site, sans aucun fichier de données cantonales, et le
publie sur GitHub Pages si la variable `PUBLIER` vaut `true`. Variables : `BASE_PATH` (ex. `/vigie-vaud` sans
domaine propre), `GOATCOUNTER` (facultatif).

## Données et licence

Le code est sous licence AGPL-3.0 (fichier `LICENSE`). Les données restent sous les conditions de leur source.

Source : Géodonnées Etat de Vaud, couche « Demandes de permis de construire (enquête publique) » de la CAMAC
([fiche viageo](https://viageo.ch/md/cb71405f-13f6-421b-b2ee-3ca76efbd56d)). Ces données sont dépourvues de foi
publique : seule la Feuille des avis officiels (FAO) fait foi.

Leur utilisation est régie par la norme
[DCG 8401](https://www.vd.ch/fileadmin/user_upload/dinf/8000/8401.pdf), qui interdit la rediffusion à des tiers sans
autorisation de la Direction du cadastre et de la géoinformation. Ce prototype ne rediffuse rien : il ne fait
qu'orienter le navigateur du visiteur vers le service public du canton, dont il met en forme les réponses.

Limites communales, fond de carte et recherche d'adresses © swisstopo.
