# Chantiers Vaud

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
libres, les noms de particuliers sont masqués automatiquement (`mask_names` dans `pipeline/fetch.py`, environ
230 dossiers) ; les entreprises et collectivités restent nommées. Le cache brut local (`data/cache/raw.json.gz`)
contient encore les descriptions d'origine et ne doit jamais être publié.

## Structure

| Dossier | Rôle |
|---|---|
| `pipeline/` | `fetch.py` télécharge la couche CAMAC, rattache chaque dossier à sa commune actuelle (swissBOUNDARIES3D), journalise les changements de statut et écrit les fichiers du site dans `web/static/data/` |
| `web/` | Site statique SvelteKit + MapLibre (fond swisstopo, tuiles PMTiles pour l'historique) |
| `data/` | Instantané du jour et journal des changements (**non versionné ici**, dépôt privé séparé) |
| `.github/workflows/` | Mise à jour quotidienne et publication sur GitHub Pages |

## Lancer en local

Prérequis : [uv](https://docs.astral.sh/uv/), Node 24+, pnpm, [tippecanoe](https://github.com/felt/tippecanoe).

```bash
cd pipeline && uv run python fetch.py
```

```bash
cd web && pnpm install && pnpm dev
```

`fetch.py --offline` réutilise le dernier téléchargement (`data/cache/raw.json.gz`).

## Mise à jour automatique

Le workflow `mise-a-jour.yml` tourne chaque jour. Il a besoin :

- des secrets `DATA_REPO` (dépôt **privé** qui contient `snapshot.json` et `changes.jsonl`) et `DATA_TOKEN` ;
- des variables `BASE_PATH` (ex. `/chantiers-vaud` sans domaine propre), `GOATCOUNTER` (facultatif) et
  `PUBLIER` (`true` pour déployer sur GitHub Pages).

Le script refuse la mise à jour si le nombre de dossiers chute de plus de 5 %, et le site affiche toujours la date
des données.

## Données et licence

Source : Géodonnées Etat de Vaud, couche « Demandes de permis de construire (enquête publique) » de la CAMAC
([fiche viageo](https://viageo.ch/md/cb71405f-13f6-421b-b2ee-3ca76efbd56d)). Ces données sont dépourvues de foi
publique : seule la Feuille des avis officiels (FAO) fait foi.

Leur utilisation est régie par la norme
[DCG 8401](https://www.vd.ch/fileadmin/user_upload/dinf/8000/8401.pdf), qui interdit la rediffusion à des tiers sans
autorisation de la Direction du cadastre et de la géoinformation. C'est pourquoi les données ne sont pas versionnées
dans ce dépôt et que la publication du site est désactivée par défaut.

Limites communales, fond de carte et recherche d'adresses © swisstopo.
