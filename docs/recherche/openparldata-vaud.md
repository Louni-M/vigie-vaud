# OpenParlData pour Vaud : quels conseils, quels champs, quelles limites ?

Recherche pour l'issue #46 (carte #43, J1 Conseils spécifié). Question : que fournit OpenParlData pour Vaud, et
avec quelles limites ?

Méthode : appels réels à `https://api.openparldata.ch/v1/` le 15 octobre 2026 entre 21 h 14 et 21 h 30 UTC, avec
l'en-tête `Origin: https://example.org` ; téléchargement complet des objets, séances, ordres du jour, documents,
contributeurs et événements des trois conseils vaudois couverts ; lecture de la
[spécification OpenAPI](https://api.openparldata.ch/openapi.json), du
[`robots.txt` de l'API](https://api.openparldata.ch/robots.txt), de l'[index des exports](https://files.openparldata.ch/exports/index.json)
et du code source public de l'API ([dépôt `data-infrastructure`](https://gitlab.com/opendata.ch/openparldatach/data-infrastructure),
dossier `fastapi/`). Les chiffres valent pour cette date ; le point de départ était
[`docs/recherche/fraicheur-sources-direct.md`](https://github.com/Louni-M/vigie-vaud/blob/research/fraicheur-sources-direct/docs/recherche/fraicheur-sources-direct.md)
(issue #2).

Vocabulaire : un *body* d'OpenParlData est une collectivité (le canton, une commune) ; ses *affairs* sont nos
Objets, ses *meetings* nos Séances, ses *agendas* les points d'un ordre du jour.

## Synthèse

| Conseil | `body_key` | Objets | Séances | Ordres du jour | Depuis |
|---|---|---|---|---|---|
| Grand Conseil (et Conseil d'État, voir plus bas) | `VD` | 8 338 | 1 646 (661 du Grand Conseil, 985 du Conseil d'État) | 28 019 points | objets 2008, séances du Grand Conseil 2008, du Conseil d'État 2000 |
| Conseil communal de Lausanne | `5586` | 1 559 | 375 | 11 621 points (111 séances, depuis 2022) | séances 2010 ; objets surtout depuis 2020 |
| Conseil communal d'Yverdon-les-Bains | `5938` | **0** | 258 | 1 238 points | séances 2001 |
| 298 autres communes vaudoises | — | 0 | 0 | 0 | — |

- **Aucun autre conseil vaudois** n'a d'objets ni de séances : la liste des trois de `docs/sources.md` est complète.
- **Les séances du body `VD` mélangent deux organes** : le Grand Conseil (`group_id=1965`) et le Conseil d'État
  (`group_id=3726`), un exécutif. Il faut filtrer par `group_id`.
- **Champs riches** : type (texte libre et harmonisé), statut (texte libre seulement), auteur·e et parti (via
  `contributors`), historique des étapes (via `events`), lien vers la page officielle, documents PDF **avec leur
  texte intégral extrait**. Tout est en français ; la langue n'est déclarée que sur une partie des documents.
- **CORS ouvert**, y compris sur les erreurs ; pas de clé.
- **Pas de quota technique observé** (140 requêtes en rafale, aucun refus, aucun en-tête de limite), mais un
  **usage loyal déclaré** : au plus 1 requête par seconde et 10 000 par jour pour un client automatisé, avec un
  User-Agent portant une adresse de contact.
- **Filtres de date** par `from_<champ>` / `to_<champ>` (au jour près), dont `from_updated_at` ; **non documentés**
  dans la spécification. Les noms intuitifs (`date_from`, `begin_date_from`…) sont ignorés sans erreur.
- **`updated_at` ne signale pas un changement réel** : il bouge à chaque réimportation (5 690 objets du Grand Conseil
  portent la date du 24 mai 2026, 1 622 celle du 15 octobre).
- **Piège de cache** : un paramètre répété (`body_key=VD&body_key=5586`) partage la clé de cache de sa dernière
  valeur ; `?body_key=VD` peut alors renvoyer les objets de Lausanne **et** du Grand Conseil (reproduit, voir plus bas).
- **Licence** : CC BY 4.0, attribution « Source: OpenParlData.ch », présentée comme valable « actuellement ».
- **Stabilité** : préfixe `/v1/`, spécification en version `1.1`, sans changelog ni politique de dépréciation publiés.

## Les conseils vaudois exposés

`GET /v1/bodies/?canton_key=VD&limit=1000` renvoie 301 bodies : le canton (`VD`), 16 villes (`type: city`) et 284
communes (`type: municipality`). Seuls trois ont `indexed: true` : `VD`, Lausanne (`5586`) et Yverdon-les-Bains
(`5938`). Les 13 autres villes (Aigle, Bussigny, Crissier, Ecublens, Gland, La Tour-de-Peilz, Montreux, Morges, Nyon,
Payerne, Prilly, Pully, Renens, Vevey) ont `has_parliament: true` et un nombre de sièges, mais aucune donnée.

Les comptes par body (`/v1/<entité>/group_by/body_key`) confirment :

| Entité | `VD` | `5586` | `5938` | Autres communes vaudoises |
|---|---|---|---|---|
| `affairs` (Objets) | 8 338 | 1 559 | 0 | 0 |
| `meetings` (Séances) | 1 646 | 375 | 258 | 0 |
| `agendas` (points d'ordre du jour) | 28 019 | 11 621 | 1 238 | 0 |
| `docs` | 21 107 | 19 125 | 3 268 | 0 |
| `texts` | 7 | 1 330 | 0 | 0 |
| `contributors` | 12 687 | 1 555 | 36 | 0 |
| `events` (étapes d'un objet) | 20 009 | 4 811 | 435 | 0 |
| `persons` | 390 | 334 | 208 | 0 |
| `votings`, `votes`, `speeches` | 0 | 0 | 0 | 0 |
| `news` | 314 | 7 969 | 1 029 | 1 chacune pour 38 communes |

Remarques :

- **Ni votes ni débats** pour Vaud, comme l'indiquait déjà `docs/sources.md`. Les débats du Grand Conseil existent
  seulement sous forme de liens vidéo (voir *Documents*).
- **Les `news` des petites communes sont des erreurs de rattachement** : la seule « news » de Pully (`5590`) est un
  communiqué de la ville de Kriens dont l'`external_id` vaut `5590`. Les 38 communes concernées n'ont rien d'autre.
- **Yverdon n'a aucun objet**, mais 1 971 documents marqués `parent_type: affair` avec `affair_id` nul : les objets
  ne sont pas importés, leurs documents si. Ses `contributors` (36) sont rattachés à des séances.
- `/v1/bodies/?canton_key=VD&indexed=true` renvoie exactement ces trois bodies : c'est la requête à relancer pour
  savoir si un nouveau conseil vaudois est couvert.

## Objets (`affairs`)

### Champs

Chaque objet porte : `id`, `body_key`, `body_id`, `external_id`, `number`, `title`, `title_long`, `type_name`,
`type_harmonized`, `type_harmonized_id`, `type_harmonized_wikidata_id`, `state_name`, `state_name_harmonized`,
`begin_date`, `end_date`, `active`, `url_external`, `created_at`, `updated_at`, `updated_external_at`, `url_api` et
`links` (vers `contributors`, `docs`, `events`, `texts`, `agendas`, `meetings`…).

Remplissage pour le Grand Conseil (8 338 objets) et Lausanne (1 559) :

| Champ | Grand Conseil | Lausanne |
|---|---|---|
| `number` | toujours, ex. `26_QUE_85`, `25_INT_100` | toujours, ex. `POS25/115`, `INT26/056` |
| `title`, `title_long` | toujours, en `fr` seulement | toujours, en `fr` seulement |
| `type_name` | toujours (18 valeurs) | toujours (9 valeurs) |
| `type_harmonized` | 5 965 objets ; nul pour 2 373 | 1 257 ; nul pour 302 |
| `state_name` | 7 546 (23 valeurs) ; vide pour 792 | **jamais** |
| `state_name_harmonized` | **jamais** | **jamais** |
| `begin_date` (date de dépôt) | toujours | 1 558 sur 1 559 |
| `end_date`, `active`, `updated_external_at` | **jamais** | **jamais** |
| `url_external` | 8 333 | toujours |

`title_long` ajoute le type et l'auteur·e : « Simple question Didier Lohri - Recours à des consultants externes et
statut de la directive DRUIDE 1.5.2 question 8. » Il n'y a **ni résumé ni texte** dans l'objet lui-même : ils
viennent des documents et, pour Lausanne, de `texts` (voir plus bas).

Les dates sont des horodatages sans fuseau (`2026-10-06T00:00:00`) ; pour les objets, l'heure vaut toujours minuit.

### Types (`type_name`) du Grand Conseil

| `type_name` | Objets | `type_harmonized` |
|---|---|---|
| Interpellation | 2 904 | Interpellation |
| Décret/Loi | 1 123 | — |
| Postulat | 1 016 | Postulat |
| Question orale | 835 (depuis 2020) | Question |
| Motion | 712 | Motion |
| Simple question | 481 | Question |
| Rapport | 355 | — |
| Pétition | 243 | — |
| Résolution | 235 | — |
| Recours de compétence | 170 | — |
| Initiative | 130 | — |
| Détermination | 44 | — |
| Grâce | 33 | — |
| Réponse | 29 | — |
| Consultation | 9 | Consultation |
| Election | 8 | Élection |
| Divers | 7 | — |
| Préavis | 4 | — |

Le préfixe du numéro suit le type : `INT` (interpellation), `HQU` (question orale), `QUE` (simple question), `MOT`,
`POS`, `LEG` (décret ou loi), `RAP`, `PAR`, `PET`, `RES`, `INI`, `DET`, `GRA`, `REP`. Les numéros `LEG`, `RAP` et
`REP` ne se suivent pas (`26_LEG` : 4 objets pour un maximum de 173) : seule une partie de cette série passe au
Grand Conseil.

Lausanne : Postulat (656), Interpellation (423), Préavis (162), Question écrite (134), Pétition (93), Divers (37),
Compte d'attente (35), Projet de règlement (12), Motion (7).

### Statuts (`state_name`) du Grand Conseil

Adopté (2 118), Traité (1 573), Renvoyée au Conseil d'Etat (906), Terminée (834), *vide* (792), Transmise au CE
(369), Pris en considération (332), Renvoyé par manque de temps (315), Renvoyée à commission (309), Refusé (296),
Retiré (208), Non pris en considération (141), Transformée en postulat (59), Classée (37), Décision du GC disponible
(22), Non entrée en matière (11), Rejetée (10), et sept valeurs isolées (« RENV_CE », « 3ème débat requis »,
« Refusé (Motion transformée en postulat) »…). Ce sont les libellés de vd.ch, non harmonisés, avec des doublons
d'orthographe (« Renvoyée au Conseil d'Etat » et « Renvoyé au CE »).

Lausanne n'a **aucun statut** sur l'objet ; l'état se lit dans les `events` (« Décision : Renvoi en Municipalité »,
« Décision : Prend acte »…).

### Auteur·e·s (`contributors`)

`GET /v1/affairs/{id}/contributors`, ou `expand=contributors` sur la liste. Chaque contributeur a `type` (`person`
ou `group`), `fullname`, `firstname`, `lastname`, `party` (abréviation, ex. `VER`), `party_harmonized` (« Les
Verts »), `role` et `role_harmonized`, `person_id`.

- Grand Conseil : 8 095 objets sur 8 338 ont au moins un contributeur (toutes les simples questions et questions
  orales, 2 850 interpellations sur 2 904). Rôles : Auteur (5 463), « Federführung » (2 627, un département du
  Conseil d'État, `type: group`), Rapporteur de commission (3 672 en trois libellés), Rapporteur de majorité ou de
  minorité, Editeur.
- Lausanne : 1 555 sur 1 559, rôles Auteur (1 453) et Cosignataires (102) ; parti renseigné pour 1 123.

### Étapes (`events`)

L'historique d'un objet : `date`, `title_harmonized` (« Déposé », « A l'ordre du jour », « Transférer »,
« Répondu », « Adopté », « Liquidé », « Rejeté », « Retiré »…), `last` (dernière étape), `details_url` (page
vd.ch du point). Grand Conseil : 20 009 étapes ; Lausanne : 4 811, avec la décision en français dans `title.fr`.

### Volume par an (selon `begin_date`)

| Année | Grand Conseil | Lausanne |
|---|---|---|
| 2008–2016 | 281 à 401 par an | 0 à 10 par an |
| 2017 | 192 | 19 |
| 2018 | 448 | 35 |
| 2019 | 417 | 48 |
| 2020 | 449 | 84 |
| 2021 | 549 | 120 |
| 2022 | 663 | 262 |
| 2023 | 648 | 252 |
| 2024 | 708 | 235 |
| 2025 | 742 | 288 |
| 2026 (au 15 octobre) | 567 | 195 |

Soit, ces dernières années, environ 2 nouveaux Objets par jour ouvrable pour le Grand Conseil et 1 pour Lausanne.
Un objet isolé du Grand Conseil est daté de 1950 (`V 01.1.1950`).

### Complétude

2017 est lacunaire au Grand Conseil : 192 objets (contre 355 en 2016 et 448 en 2018), aucun en avril, et 2 séances
seulement.

Pour 2024 et 2025, les séries d'interventions (`INT`, `HQU`, `QUE`, `MOT`, `POS`) sont complètes (aucun numéro
manquant). En 2026, il manque des trous groupés de février–mars : `26_HQU_34` à `26_HQU_50`, `26_INT_32` à `_38`,
`26_QUE_13` à `_23`, `26_MOT_10` à `_13`. C'est le trou signalé dans
[l'issue GitLab #142](https://gitlab.com/opendata.ch/openparldatach/data-infrastructure/-/work_items/142)
(fermée le 2 mai 2026, sans rattrapage depuis). Les objets récents manquent aussi parfois quelques jours :
`26_QUE_88` figure dans l'ordre du jour du 6 octobre mais pas encore parmi les objets.

## Séances (`meetings`)

### Champs

`id`, `body_key`, `external_id`, `name`, `type` (toujours `meeting`), `group_id`, `begin_date`, `end_date`,
`url_external`, `created_at`, `updated_at` et `links` (`agendas`, `docs`, `group`…). Toujours vides pour Vaud :
`number`, `location`, `state`, `description`, `type_external`, `abbreviation`, `parent_*`, `updated_external_at`.

Exemples de `name` :

- `VD` : « Séance du Grand Conseil du mardi 6 octobre 2026 » et « Séance du Conseil d'Etat du 7 octobre 2026 » ;
- `5586` : « Séance - Mardi 06 octobre 2026 2026 à 18:00 & 20:30 » (année doublée dans la source) ;
- `5938` : « Séance du Conseil communal du 1er octobre 2026 » ; `begin_date` porte l'heure (`20:00`) pour Yverdon
  seulement.

### Le Conseil d'État dans le body `VD`

Le body `VD` contient deux groupes de séances :

| `group_id` | Groupe | Séances | Période |
|---|---|---|---|
| 1965 | Grand Conseil du canton de Vaud (`Conseil législatif`) | 661 | 2008–2026, 33 à 43 par an, sauf 2017 (2 séances seulement, 10 janvier et 19 décembre) |
| 3726 | Conseil d'État du canton de Vaud (`Conseil exécutif`) | 985 | 2000–2026, 35 à 41 par an |

Le filtre `group_id=1965` fonctionne (`/v1/meetings/?body_key=VD&group_id=1965` : 661). De même, 67 objets du body
`VD` renvoient vers `vd.ch/actualites/decisions-du-conseil-detat` et 9 vers les consultations.

Lausanne (`group_id` 1044) et Yverdon (8921) n'ont qu'un groupe.

### Ordres du jour (`agendas`)

`GET /v1/meetings/{id}/agendas`. Chaque point a `item_number`, `item_title`, `item_affair_number`,
`item_affair_id`, `item_result`, `item_category`, `item_url`, `item_language`, `item_date`.

| | Grand Conseil | Lausanne | Yverdon |
|---|---|---|---|
| Séances avec ordre du jour | 639 / 661 (toutes en 2025 et 2026) | 111 / 375 (depuis 2022) | 88 / 258 (depuis 2018) |
| Points | 28 019 (y c. Conseil d'État) | 11 621 | 1 238 |
| Lien vers l'objet | `item_affair_number` seulement (18 533 points), jamais `item_affair_id` ; 13 562 numéros retrouvés parmi les objets | `item_affair_id` (11 348 points) | aucun |
| Résultat (`item_result`) | 17 818 points : « RENV-T », « Renvoyée par manque de temps », « RENV-CE », « TRAITE »… | 11 527 : « Reporté », « Renvoi en Municipalité », « Prend acte »… | aucun |

Exemple Grand Conseil, séance du 6 octobre 2026 : 52 points, dont le point 2 « Simple question Laurence Cretegny
et consorts - Valorisation lors du démantèlement de la galère La Liberté. » (`item_affair_number: 26_QUE_88`).

### Séances à venir

Aucune séance future n'est présente le 15 octobre 2026 (la plus récente : 6 octobre pour le Grand Conseil et
Lausanne, 1er octobre pour Yverdon). Délai d'apparition mesuré en 2026 (`created_at` − `begin_date`) :

- Grand Conseil et Conseil d'État : médiane 1,6 jour **après** la séance ;
- Lausanne : médiane 8 jours **avant** la séance (l'ordre du jour est publié d'avance) ;
- Yverdon : chargé en bloc le 10 juin 2026, pas de mesure fiable.

## Documents et textes

### `docs`

Chaque document a `name`, `url` (source), `url_oparl` (copie sur `files.openparldata.ch`), `format`, `size`,
`date`, `language`, `category`, `category_harmonized`, `parent_type` (`affair`, `meeting`, `agenda`, `news`), les
clés `affair_id` / `meeting_id`, et **`text`, le texte intégral extrait du fichier** (Apache Tika).

| | Grand Conseil | Lausanne | Yverdon |
|---|---|---|---|
| Documents | 21 107 | 19 125 (dont 13 341 de `news`) | 3 268 |
| Formats | PDF 14 122, vidéo Sonomix 4 121, HTML 2 211 | PDF 13 915, images, liens, vidéo 487 | PDF 3 094, vidéo 77 |
| Avec `text` | 14 994 (médiane 6 714 caractères, max 1,98 million) | 4 938 | 717 |
| Avec `url_oparl` | 20 843 | 5 294 | 717 |
| `language: fr` | 6 194 (sinon nul) | 5 784 | 2 454 |

Noms les plus fréquents au Grand Conseil : « Visionner le débat de ce point à l'ordre du jour » (3 370 vidéos),
« Objet » (2 755), « Texte adopté par le Conseil d'Etat » (2 316), « Rapport de la commission » (1 509), « Objet et
développement » (721).

Couverture : 6 908 objets du Grand Conseil sur 8 338 ont au moins un document, mais la part baisse pour les objets
récents (2024 : 554 / 708 ; 2025 : 484 / 742 ; 2026 : 70 / 567). Exemple : `26_QUE_85`, déposé le 6 octobre, n'a
encore aucun document. Lausanne : 1 538 objets sur 1 559.

Le corps d'une réponse avec `text` est lourd : tous les documents du Grand Conseil font 340 Mo en JSON. Le paramètre
`fields` permet d'exclure `text`.

### `texts`

Lausanne a 1 330 textes de type « Résumé » (HTML, en français), un par objet environ ; le Grand Conseil en a 7
(« Texte déposé »), Yverdon aucun.

### Langue

Tous les titres et libellés sont en `fr` uniquement. Le format par défaut (`lang_format=nested`) renvoie des objets
`{"fr": "…"}` ; `lang_format=flat` renvoie `title_fr`, `type_name_fr`… (et `title_de: null`). Les libellés
harmonisés (`type_harmonized`, `role_harmonized`, `events.title_harmonized`) existent en `de`, `fr`, `it`, `en` ;
le libellé brut d'une étape (`events.title`) est souvent en allemand seulement (« Eingereicht »).

## Pagination, filtres, tri, recherche

Sources : description de la spécification OpenAPI, code `fastapi/app/utils/date_filters.py`,
`fastapi/app/schemas/endpoints/affairs.yaml`, et essais.

- **URL** : barre oblique finale obligatoire (`/v1/affairs?…` répond `307` vers `/v1/affairs/?…`, avec CORS).
- **Pagination** : `offset` + `limit` ; la réponse a `meta.total_records`, `has_more`, `next_page`, `last_page`.
  `limit` vaut 500 par défaut et **n'a pas de plafond effectif** (`limit=10000` accepté : 8 338 objets du Grand
  Conseil, 15,6 Mo, 4,8 s). `offset` est plafonné à 100 000 (`400`, `application/problem+json`, renvoi vers les
  exports). Une pagination par curseur est proposée
  ([GitLab #153](https://gitlab.com/opendata.ch/openparldatach/data-infrastructure/-/work_items/153), ouverte).
- **Filtres par champ** : `?<champ>=<valeur>` pour les champs déclarés `filterable` dans le YAML de l'entité
  (`number`, `type_harmonized_id`, `group_id`, `type_name`, `state_name`…). Valeurs multiples par virgule
  (`body_key=VD,5586` → 9 897) ou par répétition (voir le piège de cache). Un paramètre inconnu est **ignoré sans
  erreur** (`foo=bar`, `date_from=…`, `begin_date_from=…`, `updated_since=…` renvoient tout).
- **Filtres de date** : `from_<champ>` (≥) et `to_<champ>` (≤), au format `AAAA-MM-JJ`, `AAAA-MM` ou `AAAA`. Seule
  la date compte : `from_updated_at=2026-10-15T12:00:00` équivaut à `from_updated_at=2026-10-15`. Vérifié sur
  `begin_date` (`from_begin_date=2026-01-01` → 567), `created_at` (`from_created_at=2026-10-01` → 20) et
  `updated_at` (`from_updated_at=2026-10-15` → 1 622). Ces paramètres n'apparaissent **pas** dans la spécification
  OpenAPI ; la documentation cite à tort `date_from` / `date_to`.
- **Tri** : `sort_by=<champ>`, `-` pour décroissant, plusieurs champs séparés par des virgules. Défaut des objets :
  `begin_date` décroissant. En tri décroissant, **les valeurs nulles viennent en tête** malgré
  `default_sort_nulls: LAST` (Lausanne : `sort_by=-begin_date` commence par `POS25/115`, sans date) ; ajouter
  `exclude_null=begin_date`.
- **Sélection de champs** : `fields=id,number,title`, y compris dans les relations (`contributors.fullname`).
- **Relations** : `expand=contributors,docs,events` sur la liste, chaque relation paginée (`docs_limit`…).
- **Recherche** : `search=` (par défaut sous-chaîne insensible à la casse, sur les métadonnées), modes `exact`,
  `natural`, `boolean`, et `search_scope=docs` pour chercher dans le texte des documents.
  `?body_key=VD&search=Yverdon` → 33 objets.
- **Exports** : `output_format=csv|excel` sur chaque liste ; exports complets quotidiens en NDJSON gzippé sur
  [files.openparldata.ch/exports/](https://files.openparldata.ch/exports/) (toute la Suisse : `affairs` 50 Mo pour
  326 218 objets, `meetings` 1,3 Mo, générés le 15 octobre à 05 h 05–05 h 38 UTC), avec CORS `*` et
  `Last-Modified`.

## CORS

- `Access-Control-Allow-Origin` renvoie l'origine appelante, avec `Access-Control-Allow-Credentials: true`
  (`CORSMiddleware` de FastAPI avec `allow_origins=["*"]`, `fastapi/app/main.py`).
- Présent aussi sur les `307`, les `400` (offset trop grand, date invalide) et les `404`.
- Une requête `GET` simple ne déclenche pas de requête préalable. La requête `OPTIONS` répond
  `Access-Control-Allow-Headers: Authorization,Content-Type,X-Client-Name` et `Access-Control-Max-Age: 100` ;
  l'en-tête `X-Client-Name` n'est documenté nulle part.
- Aucun en-tête de cache HTTP (`Cache-Control`, `Last-Modified`, `ETag`) sur l'API ; seuls `x-cache` et
  `x-cache-key` (non exposés en CORS).

## Quotas, limites de débit et cache serveur

- **Aucune limite technique observée** : 80 requêtes séquentielles puis 60 en parallèle (20 simultanées) toutes en
  `200`, sans `429` ni en-tête `RateLimit` / `Retry-After`. La spécification ne mentionne une limite (100 requêtes
  par heure et par IP) que pour `/v1/analytics/*`.
- **Usage loyal déclaré** dans [`robots.txt`](https://api.openparldata.ch/robots.txt) : « at most 1 request per
  second », « at most 10000 requests per day », « a User-Agent with a contact address », et les exports pour les gros
  volumes. Un navigateur ne peut pas fixer son `User-Agent` (en-tête interdit au JavaScript).
- **Cache Redis côté serveur** (`fastapi/app/middleware/cache_middleware.py`) : toute réponse `200` d'un `GET` est
  gardée 24 h (`REDIS_CACHE_TTL=86400`), et le cache est « cleared by HOP ETL process after data loads ».
- **Piège : la clé de cache ignore les valeurs répétées.** Elle vaut `md5(str(sorted(request.query_params.items())))`,
  et `items()` ne garde que la dernière valeur d'un paramètre répété. Reproduit le 15 octobre :
  `?limit=2&fields=id&body_key=VD&body_key=5586` (9 897 résultats) partage la clé `da4e8ffdfeff` avec
  `?limit=2&fields=id&body_key=5586`, qui renvoie alors `x-cache: HIT` et 9 897 résultats au lieu de 1 559 ; de même
  `?body_key=VD` a renvoyé 9 897 au lieu de 8 338. N'importe quel client peut ainsi empoisonner, jusqu'au prochain
  vidage, la réponse d'une requête courante. Parade côté client : ajouter un paramètre propre (ignoré par l'API,
  donc sans effet sur le résultat) change la clé ; utiliser la virgule plutôt que la répétition.
- Temps de réponse mesurés (cache manquant) : 0,13 à 0,16 s pour 10 à 20 éléments (12 à 35 Ko).

## Fraîcheur et date de mise à jour

- `created_at` / `updated_at` : horodatages d'OpenParlData, sans fuseau ; `updated_external_at` (date côté
  parlement) toujours nul pour Vaud. Le fuseau reste non documenté ; seul indice, les exports sont nommés et datés
  en UTC (`export_20261015_050518.log`, `created: 2026-10-15T05:05:19Z`).
- `updated_at` mesure la dernière **réimportation**, pas un changement : 5 690 objets du Grand Conseil portent le
  24 mai 2026, 1 622 le 15 octobre (dont des objets de 2008). Lausanne : 356 séances sur 375 mises à jour le
  15 octobre. Un « vrai » `updated_at` est demandé dans
  [GitLab #86](https://gitlab.com/opendata.ch/openparldatach/data-infrastructure/-/work_items/86) (ouverte depuis
  janvier 2026).
- Chargement initial : 7 490 objets du Grand Conseil et 1 128 de Lausanne ont `created_at` au 14 août 2025.
- Rythme : les créations se concentrent la nuit et le matin (UTC) ; le 15 octobre à 21 h 22 UTC, la mise à jour la
  plus récente de toute l'API datait de 06 h 09. Les données changent donc **au plus une fois par jour**.
- Délai d'apparition d'un objet en 2026 (`created_at` − `begin_date`) : Grand Conseil médiane 7,3 jours (90 % sous
  42 jours) ; Lausanne médiane 1,6 jour (90 % sous 26 jours).

## Licence et attribution

- Spécification OpenAPI (`info.description`) : « We currently publish our data under the Creative Commons Licence
  CC BY 4.0. Please attribute as: "Source: OpenParlData.ch" ».
- Même formule dans `robots.txt` (« Data licence: CC BY 4.0, attribution "Source: OpenParlData.ch" ») et sur la page
  « Projet » du site, qui lie [openparldata.ch](https://openparldata.ch/) : « Nous publions actuellement nos données
  sous licence Creative Commons CC BY 4.0 ("Source: OpenParlData.ch") ».
- Le mot « actuellement » (« currently ») ne promet rien pour l'avenir. Les documents copiés (`url_oparl`) restent
  des documents officiels de vd.ch, Lausanne ou Yverdon.

## Version et stabilité

- Préfixe d'URL `/v1/` ; `info.version` de la spécification : `1.1` ; `/health` répond `"version": "2.0.0"` (version
  de l'application, pas de l'API).
- Aucun changelog, calendrier de dépréciation ni annonce de rupture publiés dans la documentation ou sur le site.
  Les changements se suivent dans les issues et commits GitLab ; une lettre d'information existe (listmonk).
- Changements récents visibles : plafond d'offset ajouté le 16 mai 2026 (GitLab #153), en réaction à un client qui
  bloquait la reconstruction nocturne de la base.
- La spécification ne décrit pas les schémas de réponse (`"schema": {}` pour chaque `200`) : les champs ne sont
  connus que par l'observation et les fichiers YAML du dépôt.
- Le code de l'API est public, dans l'espace GitLab `opendata.ch/openparldatach`.

## Conséquences évidentes pour le choix Direct/Cron (#48)

Ces constats ne tranchent pas, mais pèsent sur le ticket #48 :

- **Direct est techniquement possible** : CORS ouvert même sur les erreurs, pas de clé, réponses de 12 à 35 Ko en
  0,15 s pour une page de 20 objets, filtres par conseil, groupe, date et texte.
- **Les données ne changent qu'une fois par jour** (import nocturne) : un cron à 30 min n'apporterait rien de plus
  qu'un cron quotidien.
- **Le cache serveur peut servir une réponse fausse** à une requête courante (piège des paramètres répétés) ; un
  appel Direct comme un cron doit s'en protéger.
- **L'usage loyal** (1 requête par seconde, 10 000 par jour, User-Agent avec contact) est formulé pour un client
  automatisé ; un cron peut le respecter et s'identifier, des navigateurs ne peuvent pas fixer leur User-Agent.
- **Synchronisation incrémentale** : `from_updated_at` existe, mais `updated_at` bouge à chaque réimportation ;
  l'historique complet d'un conseil tient en une requête (Grand Conseil : 15,6 Mo, ou bien moins avec `fields`).
- **Le filtrage du Conseil d'État** (`group_id`) et le **rattachement** (titres en français, recherche
  `search=<commune>`) se font de la même façon dans les deux voies.

## Questions ouvertes

- Fuseau de `created_at` / `updated_at` : toujours non documenté (déjà ouvert dans l'issue #2).
- Les trous de février–mars 2026 (GitLab #142) seront-ils rattrapés ?
- Le piège de cache est-il connu d'OpenParlData ? Aucune issue publique ne le décrit au 15 octobre 2026.
- Le rôle de l'en-tête `X-Client-Name`, autorisé en CORS mais non documenté.
