# Vigie Vaud

Tableau de bord du canton de Vaud, commune par commune, destiné d'abord aux habitants : il rassemble sur une carte
ce qui se passe dans chaque commune et informe sans prendre position. Chantiers Vaud, l'ancien nom du site, désigne
désormais sa couche Permis.

Le vocabulaire (couche, volet, fiche commune, Objet, Séance, sonde, rattrapage…) est défini dans
[`GLOSSARY.md`](GLOSSARY.md), les décisions dans [`docs/adr/`](docs/adr/) et les sources dans
[`docs/sources.md`](docs/sources.md).

## Le site

Une carte du canton, un **panneau des couches** où chaque couche s'active et ouvre son volet, et le **fil
cantonal**. Un clic sur l'hôtel de ville d'une commune ouvre sa **fiche commune**, qui a un onglet par couche (sauf
Hôtels de ville). Sur téléphone, une seule vue à la fois (Carte, Fil, Couches, Fiche), choisie dans la barre du bas.

### Les couches

L'ordre est celui du panneau des couches ([`web/src/lib/registre/couches.ts`](web/src/lib/registre/couches.ts)) ;
chaque couche a son dossier dans `web/src/lib/couches/`.

- **Permis** (`web/src/lib/couches/permis/`) : les dossiers de la CAMAC, enquêtes publiques en cours avec leur date
  de fin, procédures en attente de décision et historique depuis 1999, une année à la fois. Voie d'accès Direct :
  le navigateur du visiteur interroge lui-même le service du canton (voir [Permis et Routes : lecture en
  direct](#permis-et-routes--lecture-en-direct)). Filtres par statut et par nature de travaux, vue aérienne.
- **Conseils** (`web/src/lib/couches/conseils/`) : les Objets et les Séances du Grand Conseil et des conseils
  communaux couverts. Voie d'accès Cron : le cron les importe une fois par jour, d'OpenParlData (Grand Conseil,
  Lausanne, Yverdon-les-Bains) ou du site de la commune par le robot communal (ADR 0006 et 0010), puis les garde
  dans le dépôt de données ; le site lit les fichiers que celui-ci publie (voir [Cron et dépôt de
  données](#cron-et-dépôt-de-données)). Sur la carte, seul le marqueur du Grand Conseil, qui ouvre la fiche du
  Grand Conseil ; les conseils communaux sont dans l'onglet Conseil de leur fiche commune. Les Objets du Grand
  Conseil sont rattachés aux communes qu'ils nomment (ADR 0016), sous « Au Grand Conseil ».
- **Routes** (`web/src/lib/couches/routes/`) : les restrictions de circulation en cours et à venir de la DGMR
  (fermetures, déviations, feux…) ; chaque restriction renvoie aux autres de ses travaux. Voie d'accès Direct, sur le même service du canton que les
  Permis ; chaque restriction est rattachée à chaque commune qu'elle traverse.
- **Hôtels de ville** (`web/src/lib/couches/hotels-de-ville/`) : un marqueur par commune, sur le siège de son
  administration, ou en terre ferme quand sa position est approximative. Couche permanente, dessinée au-dessus des
  autres. Voie d'accès Préparée : les positions viennent de `pipeline/hotels-de-ville.csv` par
  `pipeline/communes.py`.

Le volet de chaque couche porte le badge de fraîcheur de ses sources. La page `/couverture` dit ce que chaque source apporte à chaque commune
(Couverture : mode et état, mesuré par les sondes du cron).

### Le fil cantonal

Le fil cantonal ([`web/src/lib/fil/`](web/src/lib/fil/)) liste les nouveautés des 14 derniers jours de toutes les
couches qui en déclarent : Objets déposés et Séances tenues, nouveaux dossiers, restrictions de circulation
commencées ; puis les Séances et les restrictions à venir, groupées par jour. Il est filtrable par type, limité à la
zone visible de la carte ou étendu au canton, et ne dépend pas des couches activées. Chaque entrée ouvre son élément
sur la carte.

### Pages et adresses

| Chemin | Contenu |
|---|---|
| `/` | La carte, avec le fil cantonal ouvert |
| `/commune/<slug>` | La carte, avec la fiche d'une commune ouverte (300 pages pré-générées, ADR 0012) |
| `/grand-conseil` | La carte, avec la fiche du Grand Conseil ouverte |
| `/a-propos` | Les couches, le robot de Vigie Vaud, les sources, le contact, la licence |
| `/couverture` | La Couverture de chaque source, commune par commune, et l'état des sondes |
| `/enquete-publique` | L'enquête publique : consultation, observations, oppositions et recours |
| `/protection-des-donnees` | Masquage, retrait, et ce que la visite transmet à chaque destinataire |
| `/sitemap.xml`, `/robots.txt` | Générés à la construction depuis `config.json` |

Les pages de la carte sont dans `web/src/routes/(carte)/`. Le reste de l'état de la carte est dans la requête de
l'adresse, lue et écrite par le registre ([`web/src/lib/registre/url.ts`](web/src/lib/registre/url.ts)) :

- l'élément ouvert, par la clé de sa couche : `?d=<n° CAMAC>` (dossier), `?c=<conseil>/<numéro ou date>` (Objet ou
  Séance, par exemple `?c=vd/26_INT_140`), `?r=<n°>` (restriction de circulation) ;
- `couches` (couches activées), `vue` (centre et zoom), `volet` (volet ouvert), `affichage` (vue du téléphone),
  `onglet` (onglet de la fiche commune) ;
- les réglages des couches : `statuts`, `nature`, `historique`, `depuis` et `tri` (Permis), `communes` (Conseils),
  `sortes` et `etats` (Routes).

Le marqueur « Autour de moi » n'est jamais écrit dans l'adresse ; le centre de la carte, lui, l'est. La mesure
d'audience GoatCounter, active seulement si `VITE_GOATCOUNTER` est défini à la construction, compte chaque page par
son chemin seul, sans ces paramètres ([`web/src/lib/audience.ts`](web/src/lib/audience.ts)).

### Masquage

Les noms de propriétaire, de requérant ou d'architecte des avis officiels ne sont pas repris. Dans les textes
libres, les noms de particuliers sont masqués (ADR 0007) : dans le navigateur, avant affichage, pour les dossiers
([`web/src/lib/masquage.ts`](web/src/lib/masquage.ts), portage exact de `mask_names` de la version qui hébergeait
les données, conservée sous l'étiquette `chantiers-hebergee`) ; par le cron, avant tout commit, pour les conseils
([`pipeline/masquage.py`](pipeline/masquage.py), qui épargne en plus les élu·e·s connu·e·s). Les entreprises et
collectivités restent nommées. Un retrait suit [`docs/retrait.md`](docs/retrait.md).

### Permis et Routes : lecture en direct

Le site **ne stocke ni ne rediffuse les données CAMAC ni DGMR** (norme DCG 8401). C'est le navigateur de chaque
visiteur qui interroge le MapServer public du canton, `www.ogc.vd.ch` (`wmsVD/MapServer/537` pour les Permis, `596`
et `595` pour les restrictions en cours et à venir). Aucun fichier de ces données n'est produit, versionné ou
publié ; la CI et la publication échouent si le site construit en contient
([`.github/scripts/verifier-sans-rediffusion.sh`](.github/scripts/verifier-sans-rediffusion.sh)).

- Client ArcGIS partagé : [`web/src/lib/api.ts`](web/src/lib/api.ts). Pagination parallèle, 6 requêtes au plus en
  même temps, délai d'attente de 20 s, une nouvelle tentative, messages d'erreur si le service ne répond pas. Le
  module refuse de s'exécuter hors du navigateur : ni la construction ni le serveur de développement n'interrogent
  le canton.
- Dossiers en cours au chargement (enquête, ou procédure de moins de 3 ans), fiche d'un dossier par son n° CAMAC,
  historique en points légers une année à la fois : `web/src/lib/couches/permis/donnees.svelte.ts`.
- Restrictions de circulation : `web/src/lib/couches/routes/dgmr.ts`, sans emprise dans les requêtes (le canton ne
  reçoit pas la zone affichée).
- Rattachement aux communes : [`web/src/lib/socle/communes.ts`](web/src/lib/socle/communes.ts) (point dans
  polygone, sinon commune la plus proche), avec les limites simplifiées de `web/static/communes-limites.json` et
  l'index `web/static/communes.json`, produits par `pipeline/communes.py` (swisstopo, données ouvertes) et
  versionnés.

Limites du serveur cantonal, constatées le 13 octobre 2026 :

- `export` (image) n'affiche rien au-delà du 1:10 000, et `dynamicLayers` ne lève pas cette limite. Les images ne
  servent donc pas pour l'historique à l'échelle du canton : la carte charge des points légers.
- Avec un **polygone** comme filtre, le serveur tronque les résultats (la limite de 2000 s'applique avant le
  filtre spatial) et ses comptages divergent (7119, 7132 ou 7144 dossiers pour Lausanne selon la requête). On
  n'utilise donc que des **emprises rectangulaires** et des numéros de dossier.

## Structure

| Dossier | Rôle |
|---|---|
| `web/` | Site statique SvelteKit + MapLibre (fond swisstopo) : pages dans `src/routes/`, couches dans `src/lib/couches/`, registre (adresse, volets, fiches) dans `src/lib/registre/`, carte et recherche dans `src/lib/socle/`, fil cantonal dans `src/lib/fil/` |
| `pipeline/` | Python (uv) : préparation des communes, cron, import des conseils, robot communal, schéma commun (voir ci-dessous) |
| `schema/` | JSON Schema générés depuis `pipeline/schema.py` (ne pas modifier) |
| `sources.json` | Déclaration de chaque source (attribution, voie d'accès, fraîcheur, Couverture, sonde, site d'une commune scrapée) et des plateformes, lue par le site et le cron |
| `config.json` | Adresses du dépôt, du courriel de contact, du site public et des Pages du dépôt de données |
| `docs/` | ADR, inventaire des sources, marches à suivre, recherches |
| `.github/` | Contrôles des PR, publication du site, workflow réutilisable du cron |
| `scripts/` | Scripts ponctuels de mise en ligne des jalons |

### Modules du pipeline

**Préparation des communes**, relancée à chaque fusion (sources Préparées, publiées avec le site) :

- `pipeline/communes.py` : index, limites, hôtels de ville et anciens noms des communes (`web/static/`) ;
- `pipeline/terre.py` : partie terrestre des communes, leurs limites moins les lacs ;
- `pipeline/hotels_de_ville.py` : outil d'initialisation de `pipeline/hotels-de-ville.csv`, seulement pour une
  nouvelle commune ;
- `pipeline/telechargement.py` : téléchargement des fichiers sources, une seule fois dans `data/cache/`.

**Cron et import des conseils** (ADR 0005, 0014, 0015 et 0017) :

- `pipeline/cron.py` : un passage du cron (sondes, état des sources, issues, import, commit et push) ;
- `pipeline/conseils.py` : import des conseils dans l'archive du dépôt de données, et sa reconstruction ;
- `pipeline/bruts.py` : les enregistrements bruts d'un conseil, communs à OpenParlData et aux sites des communes ;
- `pipeline/lecture_conseils.py` : fichiers de lecture que le site liste (`conseils/index.json`, `fil.json`…) ;
- `pipeline/masquage.py` : masquage des noms de particuliers avant tout commit (ADR 0007) ;
- `pipeline/rattachement.py` : rattachement par le nom des Objets du Grand Conseil (ADR 0016) ;
- `pipeline/retraits.py` : retraits de `retraits.json`, réappliqués à chaque import (ADR 0007).

**Sites communaux** (ADR 0006 et 0010) :

- `pipeline/robot_communal.py` : le robot communal, seul client HTTP des sites des communes ;
- `pipeline/sites_communaux.py` : lecture du conseil d'une commune scrapée, aux mêmes `Bruts` qu'OpenParlData ;
- `pipeline/lecture_iweb.py`, `pipeline/lecture_quicksite.py` : modules de lecture des plateformes i-web et
  Quicksite ;
- `pipeline/pages_html.py` : analyse du HTML, partagée par les modules de lecture ;
- `pipeline/sonde_sites.py` : sonde des sites communaux, la même pour toutes les plateformes.

**Scripts lancés à la main** :

- `pipeline/preparation_sources.py` : remesure les sites d'une plateforme pour écrire les sources communales de
  `sources.json` ;
- `pipeline/mesure_sites.py` : ce que les modules de lecture partagent pour cette mesure ;
- `pipeline/echantillon_sites.py`, `pipeline/echantillon_openparldata.py` : réenregistrent les échantillons réels
  des tests (`pipeline/tests/`).

**Schéma commun** : `pipeline/schema.py`, les modèles Pydantic de `sources.json` et des fichiers du dépôt de données
(ADR 0013).

## Lancer en local

Prérequis : Node 24+, pnpm. [uv](https://docs.astral.sh/uv/) seulement pour régénérer les communes ou le schéma
commun, et pour le cron et les tests du pipeline.

```bash
cd web && pnpm install && pnpm dev
```

Tests du site (Vitest, sans navigateur ni appel au canton) :

```bash
cd web && pnpm test
```

Tests du pipeline (pytest, sans réseau) :

```bash
cd pipeline && uv run pytest
```

Préparation des communes, relancée à chaque fusion : limites, hôtels de ville (lus dans
`pipeline/hotels-de-ville.csv`), cadre de la partie terrestre et anciens noms (répertoire historisé de l'OFS). Elle
échoue si un hôtel de ville du CSV tombe hors de la partie terrestre de sa commune, et place une commune absente du
CSV en repli avec un avertissement. Elle télécharge environ 450 Mo dans `data/cache/` la première fois.

```bash
cd pipeline && uv run python communes.py
```

Hôtels de ville, seulement pour une nouvelle commune : l'outil d'initialisation réécrit `pipeline/hotels-de-ville.csv`
(qui fait foi ; les lignes `manuel` n'y bougent jamais) et la liste des cas à revoir,
`pipeline/hotels-de-ville-a-revoir.csv`. Il télécharge environ 500 Mo dans `data/cache/hotels-de-ville/`.

```bash
cd pipeline && uv run python hotels_de_ville.py
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
`etat-sources.json` et `schema/` dans le dépôt de données `vigie-vaud-donnees`, committe et pousse. En local, on le
lance contre un clone de ce dépôt ; `--sans-push` écrit l'état et committe sans pousser, et affiche les issues
`panne-source` qu'il ouvrirait ou fermerait au lieu de toucher à GitHub :

```bash
cd pipeline && uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push
```

Le site lit `etat-sources.json` et les fichiers des conseils sur les Pages du dépôt de données (`donnees` dans
`config.json`). Pour qu'il lise plutôt ce clone local, par exemple sur la page `/couverture`, on le désigne au
serveur de développement :

```bash
cd web && DONNEES_LOCALES=../../vigie-vaud-donnees pnpm dev
```

Le déclencheur `pipeline/depot-donnees/.github/workflows/cron.yml` se pose tel quel dans le dépôt de données : il
appelle le workflow réutilisable `.github/workflows/cron.yml` (planifié toutes les 30 minutes, lancé en pratique 5 à
8 fois par jour par GitHub, voir l'ADR-0014), qui fait le passage puis publie le dépôt de données sur Pages, avec son
seul `GITHUB_TOKEN`. Ce jeton sert aussi aux issues `panne-source` : une issue « Panne : <nom de la source> » s'ouvre
quand la source passe en panne (sauf si elle est déjà ouverte), puis est commentée et fermée à son retour. Une erreur
de l'API des issues ne fait pas échouer le passage : l'état est publié quand même, et le passage suivant ouvre ou
ferme ce qui a manqué.

Le même passage importe les conseils (ADR 0015) : chacun une fois par jour, au premier passage après 7 h à Lausanne,
depuis le jour de son dernier import réussi (`conseils/import.json`), et de nouveau au passage suivant si l'import a
échoué. Quand aucun import d'un conseil n'a réussi depuis plus de 24 h (ou dès le premier échec d'un conseil qui n'a
jamais été importé), une issue `import-conseils` « Import en échec : <nom de la source> » s'ouvre, puis est commentée
et fermée au premier import réussi ; la source n'est pas mise en panne pour autant, seules les sondes en décident. Le
rattrapage de tout l'historique d'OpenParlData suit le même chemin avec `--rattrapage`, sans toucher aux sites des
communes ; le rattrapage ciblé des sites communaux, avec `--rattrapage-cible` suivi d'une plateforme (`i-web`) ou du
n° OFS d'une commune scrapée, rouvre toutes leurs pages, sans plafond de requêtes, au même débit, sans relire
OpenParlData ni les autres communes, et note son heure dans `conseils/import.json` (`rattrapages`). En local sans
rien pousser :

```bash
cd pipeline && uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push --rattrapage
cd pipeline && uv run python cron.py --depot ../../vigie-vaud-donnees --sans-push --rattrapage-cible i-web
```

ou dans le dépôt de données, par un lancement manuel du workflow « Cron » avec la case `rattrapage` cochée ou le
champ `rattrapage_cible` rempli. Rattrapages et passages ordinaires partagent le même groupe `concurrency` : ils ne
tournent jamais en même temps. Mais ce groupe ne garde qu'**une seule exécution en attente** : un rattrapage lancé
pendant un passage attend sa fin, et si le passage planifié suivant (à :17 ou :47) arrive avant, il prend sa place
dans la file et le rattrapage est annulé, sans autre trace que dans l'onglet Actions. On lance donc un rattrapage
quand aucun passage ne tourne : quelques minutes après :17 ou :47, une fois le passage fini (hors du premier passage
après 7 h à Lausanne, qui importe les sites et dure jusqu'à 45 minutes), puis on vérifie dans Actions qu'il a démarré
et on le relance s'il a été annulé. Une fois lancé, c'est lui qui retient les passages planifiés jusqu'à sa fin.

Les fichiers de lecture (`conseils/index.json`, `fil.json`, les listes par conseil et par commune) se reconstruisent
seuls depuis l'archive, sans aucune requête à OpenParlData, après un changement de leur forme ou une réécriture à la
main de l'archive (ADR 0017) :

```bash
cd pipeline && uv run python conseils.py --depot ../../vigie-vaud-donnees --reconstruire
```

## Configuration

Les adresses du dépôt, du courriel de contact, du site public et des Pages du dépôt de données sont écrites une
seule fois, dans `config.json` à la racine. Le site les lit par `web/src/lib/config.ts`.

## Contrôles et publication

Le workflow `ci.yml` se lance sur chaque PR : `svelte-check`, les tests du site (Vitest), la construction (qui
valide `sources.json`), la vérification qu'aucune donnée CAMAC ni DGMR n'est dans le site construit, la régénération
du schéma commun (qui doit ne rien changer) et les tests du pipeline (pytest).

Le workflow `publier.yml` se lance à la main. Il construit le site, sans aucune donnée CAMAC ni DGMR, et le publie
sur GitHub Pages si la variable `PUBLIER` vaut `true`. Variables : `BASE_PATH` (ex. `/vigie-vaud` sans domaine
propre), `GOATCOUNTER` (facultatif).

## Marches à suivre

Les procédures écrites, une ligne chacune :

- Retrait d'un nom à la demande d'une personne : [`docs/retrait.md`](docs/retrait.md).

## Données et licence

Le code est sous licence AGPL-3.0 (fichier [`LICENSE`](LICENSE)). Les données restent sous les conditions de leur
source : chaque attribution est déclarée dans `sources.json` et affichée par le site, et
[`docs/sources.md`](docs/sources.md) en tient l'inventaire.

- **Permis** : Géodonnées Etat de Vaud, couche « Demandes de permis de construire (enquête publique) » de la CAMAC
  ([fiche viageo](https://viageo.ch/md/cb71405f-13f6-421b-b2ee-3ca76efbd56d)). Ces données sont dépourvues de foi
  publique : seule la Feuille des avis officiels (FAO) fait foi.
- **Routes** : Géodonnées Etat de Vaud, restrictions de circulation de la DGMR.
- **Conseils** : OpenParlData (CC BY 4.0) et les sites des communes, dont le robot ne reprend que les métadonnées
  et les liens des actes officiels (ADR 0006).
- **Communes et hôtels de ville** : swisstopo (limites, lacs, adresses de bâtiments, fond de carte et recherche
  d'adresses), annuaire de l'Union des communes vaudoises, répertoire historisé des communes de l'OFS.

L'utilisation des géodonnées de l'État de Vaud est régie par la norme
[DCG 8401](https://www.vd.ch/fileadmin/user_upload/dinf/8000/8401.pdf), qui interdit la rediffusion à des tiers sans
autorisation de la Direction du cadastre et de la géoinformation. Vigie Vaud ne rediffuse ni les Permis ni les
Routes : il ne fait qu'orienter le navigateur du visiteur vers le service public du canton, dont il met en forme les
réponses.
