# Fraîcheur des sources Direct : d'où vient la date du badge ?

Recherche pour l'issue #2 (carte #1, J0 Socle spécifié). Question : pour chaque source en voie Direct de
`docs/sources.md`, la réponse ou les métadonnées du service exposent-elles une date de mise à jour, cette date
est-elle lisible depuis le navigateur (CORS), et sinon quel substitut retenir pour le badge de fraîcheur ?

Méthode : appels `curl` du 13 octobre 2026 vers 19 h 35 UTC avec l'en-tête `Origin: https://example.org`, lecture
des en-têtes `Access-Control-*`, `Last-Modified`, `ETag`, des métadonnées des services et des champs des réponses.

## Rappel : ce que le navigateur peut lire

En CORS, le code JavaScript ne lit que les en-têtes de réponse « safelisted » (`Cache-Control`, `Content-Language`,
`Content-Length`, `Content-Type`, `Expires`, `Last-Modified`, `Pragma`) et ceux que le serveur cite dans
`Access-Control-Expose-Headers` ([Fetch Standard, CORS-safelisted response-header name](https://fetch.spec.whatwg.org/#cors-safelisted-response-header-name)).
`Date` et `ETag` ne sont donc **pas** lisibles sans `Expose-Headers`. Aucune source ci-dessous n'expose `ETag` ou
`Date`.

## Synthèse

| Source | Date de mise à jour exposée ? | Où | Lisible en CORS ? | Substitut recommandé pour le badge |
|---|---|---|---|---|
| Permis `MapServer/537` | **Non** (service) | — ; seule la fiche viageo l'affiche, en HTML | Non (viageo sans CORS) | Heure de la requête ; mention « mise à jour quotidienne » |
| Routes DGMR `596` / `595` | **Non** | — | — | Heure de la requête |
| OpenParlData | Oui, par élément | `updated_at`, `created_at` | Oui | `created_at` le plus récent (`sort_by=-created_at&limit=1`) |
| CFF `rail-traffic-information` | Oui, par jeu de données et par élément | `metas.default.modified` / `data_processed` ; `published` | Oui | `metas.default.data_processed` |
| `transport.opendata.ch` | **Non** | — | — | Heure de la requête (temps réel calculé à la demande) |
| MétéoSuisse `messwerte-*-10min` | Oui, par élément, par fichier et en en-tête | `properties.reference_ts`, `creation_time`, `Last-Modified` | Oui | `reference_ts` (heure de la mesure, UTC) |
| Open-Meteo | Pas dans la réponse ; oui dans les métadonnées du modèle | `/data/meteoswiss_icon_ch1/static/meta.json` | Oui | `last_run_initialisation_time` (heure du run) |
| Accidents ASTRA | Oui, sous forme de millésime | `layersConfig` → `timestamps` ; STAC `updated` | Oui | Millésime (« données 2025 »), pas un âge |

Trois sources (permis, routes DGMR, `transport.opendata.ch`) n'exposent aucune date : le badge doit y afficher
l'heure de la requête, ce qui mesure la fraîcheur de l'affichage et non celle de la donnée. Le badge devra donc
distinguer au moins deux cas (« données du … » contre « consulté il y a … »), plus le cas du millésime annuel
(ASTRA). C'est une décision de conception à prendre dans le ticket du badge, pas ici.

## Détail par source

### Permis : `ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/537`

- Métadonnées de la couche (`/537?f=json`) : ArcGIS Server `currentVersion` 11.5, couche
  `vd.demande_permis_construire`. **Pas de `editingInfo`**, donc pas de `lastEditDate` ; `isDataVersioned: false`,
  `archivingInfo.supportsQueryWithHistoricMoment: false`, `timeInfo` absent. Le service (`MapServer?f=json`) n'a
  pas non plus de date (`documentInfo` ne donne que le nom du projet `wmsVD_geosvc_replicat-app_datawarehousegeomatique_va.aprx`).
- En-têtes : pas de `Last-Modified` ; `ETag` présent mais pas exposé (`Access-Control-Allow-Origin` renvoie
  l'origine, sans `Access-Control-Expose-Headers`) ; `Cache-Control: must-revalidate,max-age=0,public`.
- Champs : `DATE_ENQUETE` et `DATE_DECISION` sont des **chaînes** (`esriFieldTypeString`), par exemple
  `"Du 14.10.2026 au 12.11.2026"`. Le tri `orderByFields=DATE_ENQUETE DESC` est alphabétique (il remonte
  « Du 31.12.2022 … »), et les enquêtes publiées d'avance commencent dans le futur (le 14 octobre pour une requête du
  13). Ni l'une ni l'autre ne mesure la fraîcheur. `OBJECTID` le plus grand (158 402) n'a pas de date associée.
- Hors service : la fiche viageo de la couche, citée par sa `description`
  ([viageo.ch/md/cb71405f-…](https://viageo.ch/md/cb71405f-13f6-421b-b2ee-3ca76efbd56d)), affiche
  « Dernière mise à jour 13.10.2026 » et « Fréquence de mise à jour : Journalière ». Cette date n'existe que dans le
  HTML ; les exports XML (GM03 et eCH-0271) ne donnent que la fréquence `daily` et la date de la métadonnée
  (2026-09-29). Aucun des trois n'envoie d'en-tête CORS.
- **Substitut** : heure de la requête, avec la mention que la couche est rafraîchie une fois par jour. Si l'on
  tient à la vraie date, seul le cron pourrait la relever sur viageo (scraping HTML), ce qui ne vaut pas la peine
  pour une source quotidienne.

### Routes DGMR : `MapServer/596` (en cours) et `/595` (à venir)

- Même serveur, mêmes constats que la couche 537 : pas de `editingInfo`, pas de `Last-Modified`, `ETag` non exposé.
- `DATE_DEBUT` et `DATE_FIN` sont de vraies dates (`esriFieldTypeDate`, millisecondes epoch), mais elles décrivent la
  période de la restriction, pas sa saisie. Aucun champ de suivi des modifications (`OBJECTID`, `RESTRICTION`, `RHRC`,
  `ARRDT`, `NOM`, `TYPE`, `DATE_DEBUT`, `HEURE_DEBUT`, `DATE_FIN`, `HEURE_FIN`, `WEEK_END`, `ENTITE`, `REMARQUE`).
  Au 13 octobre : 47 restrictions en cours, 21 à venir.
- La `description` de la couche ne renvoie pas vers une fiche viageo.
- **Substitut** : heure de la requête.

### OpenParlData : `api.openparldata.ch/v1/`

- Attention : `/v1/affairs?…` répond `307` vers `/v1/affairs/?…` ; il faut la barre oblique finale.
- Chaque objet (`affairs`) et chaque séance (`meetings`) porte `created_at` et `updated_at` (horodatage
  d'OpenParlData, format `2026-10-07T18:37:30` **sans fuseau** ; la [spécification OpenAPI](https://api.openparldata.ch/openapi.json)
  ne le précise pas). `updated_external_at` (date côté parlement) vaut `null` pour Vaud, Lausanne et Yverdon.
- Le paramètre `sort_by` (préfixe `-` pour décroissant) et `fields` sont documentés dans la spécification et
  fonctionnent : `?body_key=VD&sort_by=-created_at&limit=1&fields=created_at` renvoie le plus récent.
- `updated_at` bouge à chaque réimportation : le 13 octobre, des objets de 2020 et des séances de 2009 portent
  `updated_at` du jour vers 07 h 02. Il mesure donc la dernière synchronisation d'OpenParlData, pas la dernière
  nouveauté.
- En-têtes : CORS ouvert (origine renvoyée, `allow-credentials`), pas de `Last-Modified`, pas de `Cache-Control` ;
  un cache intermédiaire (`x-cache`) est présent.
- **Substitut** : `created_at` le plus récent pour « dernier objet connu » ; `updated_at` le plus récent si l'on
  veut « dernière synchronisation ». Traiter le fuseau comme inconnu (afficher le jour plutôt que « il y a 4 min »),
  ou le confirmer auprès d'OpenParlData.

### CFF : `data.sbb.ch/api/explore/v2.1/catalog/datasets/rail-traffic-information`

- Plateforme Opendatasoft. La fiche du jeu de données (même URL sans `/records`) contient
  `metas.default.modified` et `metas.default.data_processed` (UTC, avec fuseau), ici `2026-10-13T15:40:12+00:00`,
  avec `modified_updates_on_data_change: true`. Le modèle de métadonnées du portail définit `modified` comme
  « Date of the latest data update » (`dct:modified`), voir
  [`/catalog/metadata_templates/basic`](https://data.sbb.ch/api/explore/v2.1/catalog/metadata_templates/basic).
- Contrôle : le message le plus récent (`order_by=published desc`) date de 15:36:50, juste avant `data_processed`
  (15:40:12) ; la date suit bien les changements de données, pas les passages à vide.
- `dcat.accrualperiodicity` vaut « alle 5 Minuten », mais `default.update_frequency` vaut `ANNUAL` : ce second
  champ est faux, ne pas l'afficher.
- Chaque message porte aussi `published` (UTC), triable.
- En-têtes : `Access-Control-Allow-Origin: *`, `Cache-Control: public, max-age=60`, pas de `Last-Modified`.
- **Substitut** : aucun besoin, `data_processed` convient (une requête de plus, mise en cache 60 s). À défaut,
  `published` du message le plus récent, dans la même requête que les messages.

### `transport.opendata.ch/v1/stationboard`

- La réponse ne contient que `station` et `stationboard` ; les horaires (`departure`, `prognosis`) sont des heures
  de passage, pas une date de mise à jour.
- En-têtes : `Access-Control-Allow-Origin: *`, `Cache-Control: no-cache`, pas de `Last-Modified`.
- **Substitut** : heure de la requête ; c'est ici fidèle, car les prévisions sont calculées à la demande.

### MétéoSuisse : `data.geo.admin.ch/ch.meteoschweiz.messwerte-*-10min/…_fr.json`

- Chaque station porte `properties.reference_ts` (heure de la mesure, UTC, par exemple `2026-10-13T19:20:00Z`) ;
  le fichier porte `creation_time` (`"13.10.2026 21:25"`, heure locale sans fuseau).
- En-têtes : `Access-Control-Allow-Origin: *` et `Last-Modified` (lisible en CORS, car safelisted), ici
  19:26:17 GMT pour la température ; vérifié aussi pour les précipitations et le vent.
- **Substitut** : aucun besoin. Retenir `reference_ts`, qui date la mesure elle-même. Prendre le maximum sur les
  stations : une station en panne peut garder un horodatage ancien.

### Open-Meteo : `api.open-meteo.com/v1/forecast?models=meteoswiss_icon_ch1`

- La réponse ne date pas le run : `current.time` est l'heure de validité (pas de 15 min), `generationtime_ms` la
  durée de calcul.
- Les métadonnées du modèle,
  [`/data/meteoswiss_icon_ch1/static/meta.json`](https://api.open-meteo.com/data/meteoswiss_icon_ch1/static/meta.json),
  donnent en secondes epoch `last_run_initialisation_time` (15:00 UTC), `last_run_availability_time` (16:54 UTC),
  `last_run_modification_time` et `update_interval_seconds` (10 800, soit 3 h). La page
  [Model Updates](https://open-meteo.com/en/docs/model-updates) décrit ces champs et conseille d'attendre 10 min
  après `last_run_availability_time`.
- En-têtes : `Access-Control-Allow-Origin: *` sur les deux URL ; `meta.json` a aussi un `Last-Modified`.
- **Substitut** : aucun besoin. `last_run_initialisation_time` donne « prévision du run de 17 h ».

### Accidents ASTRA : geo.admin.ch `ch.astra.unfaelle-personenschaeden_alle`

- Données annuelles : les éléments (`identify`) n'ont que `accidentyear`, le mois, le jour de la semaine et l'heure.
- `layersConfig` ([api3.geo.admin.ch/rest/services/api/MapServer/layersConfig](https://api3.geo.admin.ch/rest/services/api/MapServer/layersConfig?lang=fr))
  liste les `timestamps` de la couche : `99990101` (toutes les années), puis `20250101` … `20110101`.
- La collection STAC ([data.geo.admin.ch/api/stac/v1/collections/ch.astra.unfaelle-personenschaeden_alle](https://data.geo.admin.ch/api/stac/v1/collections/ch.astra.unfaelle-personenschaeden_alle))
  donne `updated: 2026-03-19T10:10:07Z` et une étendue temporelle au 2026-02-25.
- En-têtes : `Access-Control-Allow-Origin: *` partout, `Cache-Control: max-age=1800` (api3) ou `600` (STAC).
- **Substitut** : afficher le millésime le plus récent tiré de `timestamps` (« données 2025 ») ; un âge
  (« il y a 7 mois ») n'aurait pas de sens pour une statistique annuelle.

## Questions ouvertes

- Fuseau de `created_at` / `updated_at` chez OpenParlData : non documenté ; à confirmer (issue GitLab ou
  info@openparldata.ch) avant d'afficher un âge en minutes.
- La date « Dernière mise à jour » de viageo pour la couche 537 correspond-elle au rafraîchissement réel du service
  ArcGIS ? Rien dans le service ne permet de le vérifier depuis le navigateur.
