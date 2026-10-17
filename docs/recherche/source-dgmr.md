# Source DGMR des restrictions de circulation : champs, identité, rythme et géométrie

Recherche pour l'issue #92 (carte #91, J2 Routes spécifié). Question : que vaut la source DGMR des restrictions de
circulation (`www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer`, couches `596` en cours et `595` à venir)
pour une couche Routes ?

Méthode : appels `curl` du samedi 17 octobre 2026 vers 7 h 45 UTC, avec l'en-tête `Origin`, une vingtaine de
requêtes en tout : métadonnées des couches (`?f=json`, `/metadata`), toutes les entités des deux couches
(`/query?where=1=1&outFields=*&outSR=4326&f=geojson`, puis en MN95 pour les longueurs), requêtes statistiques
(`returnDistinctValues`, `groupByFieldsForStatistics`) et couches voisines du groupe « Données routières ».
Géométrie croisée avec `web/static/communes-limites.json` (limites des communes du site, WGS84 à ~1 m), avec
shapely et pyproj, en MN95. Un seul instantané : tout ce qui touche à la durée est indiqué comme **observé**
(ce jour), **déduit** (d'indices) ou **à observer** (seul un relevé sur plusieurs jours tranche).

Le nom d'hôte sans `www.` (`ogc.vd.ch`) ne se résout pas : `docs/sources.md` l'écrit ainsi pour les Routes, mais
seul `www.ogc.vd.ch` répond (c'est l'URL de `web/src/lib/api.ts` pour les Permis).

## Synthèse

| Point | Réponse |
|---|---|
| Volume | 35 entités en cours (`596`), 15 à venir (`595`) ; le 13 octobre : 47 et 21 (recherche #2) |
| Unité | Une entité = un **tracé** (fermeture, déviation, feux…), pas un chantier : un chantier a en général 2 tracés (fermeture + déviation), jusqu'à 4 |
| `RESTRICTION` | `Fermeture`, `Déviation`, `Feux`, `Restriction particulière` (le rendu prévoit aussi `Manifestation` et `Autre`, absents ce jour) |
| `RHRC` | N° de la route cantonale dans le répertoire hiérarchique : `<n°>-<B/C/IL>-<P/S>` (Base, Complémentaire, Intérêt local ; Principale, Secondaire) |
| `HEURE_*` | Remplies pour 8 tracés sur 50, tous à venir ; jamais en cours. Les dates portent déjà l'heure, en heure locale codée comme de l'UTC |
| `REMARQUE` | Remplie pour 29 tracés sur 50 : sens unique, horaires de nuit, accès |
| `OBJECTID` | Probablement stable et commun aux deux couches (même table), **non prouvé** ; une modification pourrait recréer l'entité. À observer |
| Clé naturelle | Aucune n'est unique : `RHRC` + `NOM` + `RESTRICTION` + dates a un doublon ce jour |
| Date de modification | Aucune : ni `editingInfo`/`lastEditDate`, ni champ de suivi |
| Dates dépassées | Aucune fin dépassée en cours, aucun début dépassé à venir : le partage suit l'heure |
| Longueur | Médiane 348 m hors déviations (30 m à 7,7 km), 5,8 km pour les déviations (330 m à 17,7 km) |
| Communes par tracé | Hors déviations : 1 commune pour 27 tracés sur 32 ; déviations : 3 ou plus pour 9 sur 18 ; tous les tracés touchent au moins une commune |
| Traversée de localité | 13 tracés hors déviations sur 32 sont surtout en traversée de localité |
| Hors réseau cantonal | 2 tracés hors déviations sur 32 sont surtout hors du réseau cantonal (chemins communaux) |
| CORS | Ouvert : `Access-Control-Allow-Origin` renvoie l'origine reçue |
| Limites | `maxRecordCount` 2000 ; formats `JSON, geoJSON, PBF` |
| Licence | Pas de licence ouverte. Norme DCG 8401 : « Source : Géodonnées Etat de Vaud », rediffusion interdite |

## Couches et métadonnées

- `596` `vd.circulation_restriction_actuelle` et `595` `vd.circulation_restriction_future`, sous-couches du
  groupe `594` « Restrictions temporaires de circulation (chantier et manifestation) », lui-même dans `289`
  « Données routières ». ArcGIS Server 11.5, polylignes, référence MN95 (EPSG:2056).
- `description` identique pour les deux : « Restrictions de la circulation gérées par la division entretien de la
  DGMR », suivie d'un numéro de téléphone. `copyrightText` vide.
- `/596/metadata` (XML ArcGIS) : titre « Restrictions actuelles », `CreaDate` 20260513, licence (`useLimit`)
  vide. Aucune fiche viageo n'est citée, alors que les couches voisines de la DGMR en citent une (`290`, `292`,
  `293`, `294`, `296`). La recherche STAC de viageo (`/api/catalog/stac/search?q=circulation`) ne trouve rien.
- Le projet publié est `wmsVD_geosvc_replicat-app_datawarehousegeomatique_va.aprx` (`documentInfo` du
  service) : les couches sont servies depuis une **réplique** de l'entrepôt de géodonnées, pas depuis la base
  d'édition de la DGMR.

## Champs et valeurs

Valeurs relevées par `returnDistinctValues=true` et `groupByFieldsForStatistics` (les deux fonctionnent) et sur
les 50 entités.

| Champ | Type | Alias | Valeurs (en cours / à venir) |
|---|---|---|---|
| `RESTRICTION` | texte 25 | Restriction | `Déviation` 13/5, `Fermeture` 8/4, `Restriction particulière` 8/6, `Feux` 6/0 |
| `TYPE` | texte 25 | Type travaux / manifestation | `Infrastructure` 15/4, `Revêtement` 9/1, `Entretien` 2/10, vide 9/0 |
| `ENTITE` | texte 25 | Entité responsable | `IR` 16/2, `Commune` 11/5, `ER` 4/6, `OFROU` 2/0, `CFF` 0/2, vide 2/0 |
| `ARRDT` | texte 10 | Arrondissement | `Ouest` 15/5, `Nord` 9/4, `Est` 5/0, `Centre` 3/6, vide 3/0 |
| `WEEK_END` | texte 100 | Fermeture durant le week-end | `Oui` 32/9, `oui` 2/2, `Non` 1/0, `non` 0/4 |
| `RHRC` | texte 25 | N° RHRC | 20 valeurs distinctes, par exemple `54-B-P`, `7-C-S`, `415-IL-S` |
| `NOM` | texte 200 | Nom / Description | Libre : `Moudon, Sorbiers E2`, `Galerie de Cheseaux 2026 oct`, `2026 OFROU PS Tir Fédéral sens unique` |
| `DATE_DEBUT`, `DATE_FIN` | date | Date de début / de fin | Toujours remplies |
| `HEURE_DEBUT`, `HEURE_FIN` | texte 10 | Heure de début / de fin | `19:30`, `20:00`, `20:30`, `21:00`, `05:00`, `05:30` |
| `REMARQUE` | texte 150 | Remarque | Libre |

- **Pas de domaines** : aucun champ n'a de `domain` ; les valeurs sont saisies librement (casse de `WEEK_END`
  variable, `ENTITE` vide). Les valeurs de `RESTRICTION` sont celles du rendu `uniqueValue` de la couche, qui
  prévoit aussi `Manifestation` et `Autre`.
- **`RHRC`** : numéro du répertoire hiérarchique des routes cantonales. La couche `294`
  `vd.hierarchie_route_cantonale` a les mêmes valeurs dans `NO_RHRC`, avec `HIERARCHIE` (`Base`,
  `Complémentaire`, `Intérêt local`) et `CATEGORIE` (`Principale`, `Secondaire`) : `54-B-P` est Base
  Principale, `7-C-S` Complémentaire Secondaire, `415-IL-S` Intérêt local Secondaire. Le `RHRC` d'un tracé est la
  route du chantier, pas toujours celle sous le tracé : une déviation emprunte d'autres routes, et deux tracés
  hors déviation sont posés sur une autre route que leur `RHRC` (`5243` noté `705-B-P` sur la `706-B-P` ;
  `10042` noté `54-B-P` sur la `30-B-P`).
- **`ARRDT`** : arrondissement d'entretien des routes cantonales, mêmes valeurs que la couche `290`
  `vd.arrondissement_route_cantonale` (Ouest, Centre, Nord, Est).
- **`ENTITE`** : maître d'ouvrage du chantier. `IR` et `ER` sont des sigles internes, non expliqués par la source ;
  d'après les chantiers (`IR` sur des chantiers « Infrastructure », `ER` sur l'entretien des galeries), ce sont
  vraisemblablement des divisions de la DGMR (infrastructure routière, entretien). Déduit, pas vérifié.
- **`WEEK_END`** : « Fermeture durant le week-end », Oui/Non, casse libre.
- **Heures** : `HEURE_DEBUT`/`HEURE_FIN` ne sont remplies que pour 8 tracés sur 50, tous à venir (aucun en cours),
  surtout des fermetures de nuit. Mais les champs date portent déjà une heure dans 21 tracés sur 50 (`07:00`,
  `05:00`, `19:30`…). Cette heure est l'**heure locale codée comme de l'UTC** : `10353` a `HEURE_DEBUT` `19:30` et
  `DATE_DEBUT` à 19 h 30 UTC, alors que la Suisse est en UTC+2. La couche annonce `datesInUnknownTimezone: false`
  et aucun `dateFieldsTimeReference` : il faut donc lire l'epoch comme une heure locale. `00:00` veut dire « jour
  entier ». Trois tracés à venir se contredisent (`10662` : `DATE_FIN` 23:59, `HEURE_FIN` 05:30 ; `10663` et
  `10664` : `DATE_FIN` 00:00, `HEURE_FIN` 05:30) : pour les fermetures de nuit, `HEURE_*` donne la plage
  quotidienne, et les dates la période.
- **`REMARQUE`** : remplie pour 29 tracés sur 50 (19/35 en cours, 10/15 à venir). Contenu : sens unique et sa
  direction, horaires de nuit, accès riverains, largeur maximale, rappel d'une autre route touchée. Souvent
  répétée à l'identique sur la fermeture et sa déviation.

## Identité d'une restriction

### Ce qu'on observe

- **Un chantier, plusieurs tracés** : 50 tracés, 20 `RHRC` distincts. Groupés par `RHRC` + `NOM` + dates :
  31 groupes, dont 16 de 2 tracés (une fermeture ou restriction et sa déviation), 14 d'un seul et 1 de 4
  (`Moudon, Sorbiers E2` : déviation, fermeture, deux restrictions particulières).
- **Phases** : un même chantier change de `NOM` à chaque étape (`Moudon, Sorbiers E2` en cours jusqu'au 21
  octobre, `Moudon, Sorbiers E4` à venir dès le 21 ; `Aubonne Giratoire E1` puis `E2` ; `Nyon - St-Cergue E1`
  puis `E2`), avec des `OBJECTID` différents : chaque phase est une nouvelle entité.
- **Nuits multiples** : les fermetures de nuit en plusieurs fenêtres sont des entités distinctes, de même `NOM`
  (`Galerie de Cheseaux 2026 oct` : `10662` le 26 octobre, `10353` du 27 au 30).
- **Une seule table** : les deux couches ont le même index spatial `A3179_IX1`, la même emprise déclarée (plus
  large que l'union de leurs tracés actuels), les mêmes champs, et des `OBJECTID` entrelacés sans collision
  (à venir : 10342 à 10675 ; en cours : 4368 à 10673 ; 10662 à 10675 se répartissent entre les deux). Les deux
  couches sont donc deux filtres par date sur la même table.
- **Les `OBJECTID` durent** : des tracés en cours depuis des mois ont des `OBJECTID` anciens et dispersés
  (`5031` depuis septembre 2025, `5340`–`5343` depuis mai 2026, `4368` depuis février 2026), ce qui exclut un
  rechargement complet de la réplique avec renumérotation.
- **Mais la séquence avance vite** : environ 300 `OBJECTID` consommés entre `10356` (fermeture du 29 octobre) et
  `10662`, pour une cinquantaine de tracés visibles. `10665`/`10666` (Morcles, en cours depuis le 12 octobre) sont
  plus récents que des tracés qui commencent le 19. Soit la table contient beaucoup d'entités jamais publiées ou
  supprimées, soit une modification supprime et recrée l'entité.
- **Aucun champ de suivi** : ni `editFieldsInfo`, ni `editingInfo` (donc pas de `lastEditDate`),
  `isDataVersioned: false`, `isDataArchived: false`, `archivingInfo.supportsQueryWithHistoricMoment: false`.

### Ce qu'on en déduit

- Quand un tracé passe de « à venir » à « en cours », il change de couche mais pas de ligne : son `OBJECTID`
  devrait rester le même. Déduit de la table commune, pas observé.
- Un `OBJECTID` survit des mois sans modification. Qu'il survive à une **modification** (prolongation, tracé
  corrigé) n'est pas établi : la vitesse de la séquence laisse ouverte une suppression-recréation à chaque
  modification.

### Clé candidate

- `OBJECTID` est la seule clé unique. C'est la clé recommandée pour l'URL et la fiche d'un tracé, en acceptant
  qu'un tracé modifié puisse changer de clé.
- Aucune clé naturelle n'est unique : `RHRC` + `NOM` + `RESTRICTION` + `DATE_DEBUT` + `DATE_FIN` a un doublon ce
  jour (`5341` et `5342`, deux restrictions particulières identiques sauf la géométrie), et `NOM` comme les dates
  changent d'une phase ou d'une prolongation à l'autre. `RHRC` + `NOM` regroupe bien les tracés d'un même chantier
  pour l'affichage, mais n'identifie pas une restriction.

### À observer sur plusieurs jours

Un relevé quotidien (ou deux par jour) des deux couches, `OBJECTID` + attributs + empreinte de géométrie,
trancherait : (1) un `OBJECTID` passe-t-il bien de `595` à `596` à la date de début ; (2) une prolongation
garde-t-elle l'`OBJECTID` ; (3) combien d'entités apparaissent, changent et disparaissent par jour. L'`ETag` des
réponses `/query` (par exemple `"583fea86"`) change avec le contenu et peut servir de détecteur bon marché ; il
n'est pas exposé en CORS, donc seulement lisible par le cron.

## Rythme de mise à jour

- **Pas de date de modification** dans le service : ni `editingInfo.lastEditDate` (absent des deux couches), ni
  champ de date de saisie, ni `Last-Modified`. Le badge de fraîcheur ne peut afficher que l'heure de la requête
  (déjà constaté par la recherche #2).
- **Partage à l'heure près** : à 7 h 45 UTC le 17, aucun tracé en cours n'a une fin passée (la plus proche :
  19 octobre 07:00) et aucun tracé à venir n'a un début passé (le plus proche : 19 octobre 00:00). Le filtre par
  date est donc appliqué à la requête ou rafraîchi souvent ; les tracés finis disparaissent de `596`.
- **Volume** : 47 en cours et 21 à venir le 13 octobre (recherche #2), 35 et 15 le 17 : au moins 12 tracés en
  cours de moins en quatre jours (net). Ordre de grandeur : quelques tracés par jour ouvrable entrent ou sortent.
- **Retraits avant la fin** : impossibles à voir sur un instantané (un tracé retiré ne laisse aucune trace). À
  observer.
- **Délai d'annonce** : les tracés à venir commencent entre 2 et 12 jours plus tard (19 au 29 octobre) ; ce
  jour, la couche « à venir » ne couvre que les deux semaines suivantes (annonce tardive ou filtre ? à observer),
  même pour un chantier d'un an
  (`Moudon, Sorbiers E4`, du 21 octobre 2026 au 1er octobre 2027).

## Géométrie

Tous les tracés sont des `LineString`, sauf 5 `MultiLineString` (2 à 4 morceaux). Longueurs en MN95.

| Tracés | Nombre | Longueur min | Médiane | Max |
|---|---|---|---|---|
| Tous | 50 | 30 m | 766 m | 17,7 km |
| Hors déviations | 32 | 30 m | 348 m | 7,7 km |
| Déviations | 18 | 330 m | 5,8 km | 17,7 km |

### Communes traversées

Intersection de chaque tracé avec les limites des communes du site (en ne comptant que les passages d'au moins
20 m, pour écarter les tracés qui longent une limite).

| Tracés | 1 commune | 2 communes | 3 ou plus | Aucune |
|---|---|---|---|---|
| Tous (50) | 33 | 6 | 11 | 0 |
| Hors déviations (32) | 28 | 2 | 2 | 0 |
| Déviations (18) | 5 | 4 | 9 | 0 |

- Le maximum est de 6 communes (`10047`, déviation de `Nyon - St-Cergue E1`). Hors déviations, les tracés de 3
  communes sont des fermetures ou restrictions longues (`5031` Chavannes-de-Bogis–Chavannes-des-Bois, 2,8 km ;
  `10046` Nyon–St-Cergue, 7,7 km).
- Aucun tracé n'est hors des communes vaudoises. Une déviation (`10047`) a 257 m hors des limites des communes du
  site, vers 6,179 E 46,451 N ; cause non recherchée.
- Pour un **chantier** (fermeture + déviation), le nombre de communes est celui de sa déviation.

### Traversées de localité

Croisement avec la couche `292` `vd.traversee_localite` (285 tronçons de route cantonale en traversée de
localité, avec la commune et un lien vers le plan PDF), à 15 m près.

- Hors déviations : 13 tracés sur 32 ont plus de la moitié de leur longueur en traversée de localité, 18 en ont
  une partie.
- Déviations : 4 sur 18 sont surtout en traversée, toutes en traversent une partie.
- La fiche viageo de la couche `292` rappelle que ces tronçons sont « de compétence communale » : la DGMR publie
  donc aussi des restrictions sur des tronçons qu'elle ne gère pas ; l'`ENTITE` est alors souvent `Commune`.

### Hors du réseau cantonal

Croisement avec le réseau de la couche `294` (449 tronçons numérotés RHRC), à 15 m près.

- Hors déviations : 29 tracés sur 32 sont à 90 % ou plus sur le réseau cantonal ; 2 sont surtout en dehors :
  `10672` (`Chav. de Bogis - En Peguey`, 519 m, 6 % sur le réseau, un chemin communal) et `5342` (41 m à
  Moudon, 29 %).
- Déviations : 12 sur 18 sont à 90 % ou plus sur le réseau cantonal ; les autres empruntent des routes communales
  (`5212`, déviation du chantier OFROU de Chavannes-près-Renens et Ecublens : 17 %).
- La couche `581` `vd.route_cantonale` (140 entités, une par numéro de route) omet des routes d'intérêt local
  (`7-C-S`, `415-IL-S`, `711-IL-S` n'y sont pas) : la référence du réseau cantonal est la `294`.

## Accès

- **CORS** : ouvert. Avec `Origin: https://vigie-vaud.example`, la réponse renvoie
  `Access-Control-Allow-Origin: https://vigie-vaud.example`, `Access-Control-Allow-Credentials: true` et
  `Vary: Origin`, sur `?f=json` comme sur `/query?f=geojson`. Pas d'`Access-Control-Expose-Headers`.
- **En-têtes** : `Cache-Control: must-revalidate,max-age=0,public`, `ETag` (non exposé), pas de `Last-Modified`.
  Un cookie `AGS_ROLES` de 60 s est posé, sans effet pour une lecture anonyme.
- **Formats** : `supportedQueryFormats: JSON, geoJSON, PBF`. `f=geojson` renvoie `application/geo+json` ;
  `outSR=4326` reprojette en WGS84 avec la transformation `CH1903+_To_WGS_1984_1` déclarée par le service.
- **Limites** : `maxRecordCount` 2000 (la totalité tient en une requête par couche), pagination et statistiques
  disponibles (`supportsPagination`, `supportsDistinct`, `groupByFieldsForStatistics`).
- **Poids** : en GeoJSON WGS84 non simplifié, toutes les entités pèsent 331 Ko en cours et 79 Ko à venir ;
  `maxAllowableOffset` ou `geometryPrecision` pourraient l'alléger (non testé).
- **Licence et attribution** : la couche n'a ni `copyrightText` ni licence dans ses métadonnées, et pas de fiche
  viageo. Les géodonnées de l'État de Vaud relèvent de la norme DCG 8401 « Conditions d'utilisation des
  géodonnées de l'Etat de Vaud » (version du 1er juin 2022), à laquelle renvoient les fiches viageo des couches
  sœurs de la DGMR (`292`, par exemple). Elle impose la mention « Source : Géodonnées Etat de Vaud » (art. 19
  RLGéo-VD), réserve les données aux « propres besoins de l'utilisateur » et interdit la rediffusion à des tiers.
  Le catalogue Open Data de viageo (`/api/catalog/dcat-ch/administration-cantonale-vaudoise`) ne compte aucun jeu
  de l'administration cantonale : ce ne sont **pas** des données ouvertes. Les conditions du guichet
  cartographique cantonal permettent la reproduction pour un usage personnel et non commercial, « à condition que
  les mentions et copyrights soient respectés ».
- **Conséquence pour la voie d'accès** (à trancher ailleurs) : la source Permis du même service est déjà déclarée
  dans `sources.json` avec « Géodonnées État de Vaud (CAMAC) » et la licence « Norme DCG 8401, sans
  rediffusion », en voie Direct. Conserver les restrictions dans le dépôt de données public (voie Cron) reviendrait
  à les mettre à disposition de tiers, ce que la norme interdit sans accord préalable de la DCG.

## Autres jeux utiles à J2 (non intégrés)

Sur le même service, groupe `289` « Données routières » :

- `292` `vd.traversee_localite` : tronçons en traversée de localité, commune et plan PDF ;
- `294` `vd.hierarchie_route_cantonale` et `295` `vd.categorie_route_cantonale` : réseau RHRC, hiérarchie et
  catégorie, de quoi afficher « route cantonale 54-B-P (base, principale) » ;
- `296` `vd.classification_route_cantonale` : classification a à d ;
- `290` `vd.arrondissement_route_cantonale` : les quatre arrondissements d'entretien ;
- `293` `vd.axe_maintenance` (avec `DATE_MODIFICATION`), `297` `vd.trafic_journalier_moyen`, `391`
  `vd.itineraire_convoi_exceptionnel`, `581` `vd.route_cantonale`.

Hors service :

- la page vd.ch « Restrictions de circulation et travaux » et l'adresse courte `vd.ch/restrictions-circulation`,
  qui renvoient au guichet cartographique (thème mobilité) depuis le 1er juin 2021 ;
- les avis de restriction de la DGMR, en PDF, souvent republiés par les communes ; leur nom de fichier porte un
  numéro (`…-restr-50172.pdf`) qui n'apparaît pas dans la couche ;
- les routes non déneigées l'hiver (`vd.ch/routes-sans-deneigement`), page HTML ;
- les chantiers des routes nationales de l'ASTRA (page HTML), à côté de DATEX II qui est hors J2.

Aucun de ces jeux ne décrit les déviations mieux que les tracés `Déviation` de la source elle-même.

## Sources

- Service et couches : <https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer?f=json>,
  [`/595?f=json`](https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/595?f=json),
  [`/596?f=json`](https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/596?f=json),
  [`/596/metadata`](https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/596/metadata),
  [`/594?f=json`](https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/594?f=json), couches `290`,
  `292`, `293`, `294`, `295`, `296`, `581` (`?f=json` et `/query`).
- Fiche viageo de la couche `292` (eCH-0271) :
  <https://viageo.ch/api/catalog/metadata/ech-0271/9165c86e-97ff-4ed4-9cb4-f4320f6b1de1.xml>.
- Catalogue Open Data de viageo : <https://viageo.ch/api/catalog/dcat-ch/administration-cantonale-vaudoise> ;
  recherche STAC : <https://viageo.ch/api/catalog/stac/search?q=circulation>.
- Norme DCG 8401, « Conditions d'utilisation des géodonnées de l'Etat de Vaud », version du 01.06.2022 :
  <https://www.vd.ch/fileadmin/user_upload/dinf/8000/8401.pdf>.
- Conditions d'utilisation du guichet cartographique :
  <https://www.vd.ch/territoire-et-construction/cadastre-et-geoinformation/guichets-cartographiques/conditions-dutilisation>.
- vd.ch, « Restrictions de circulation et travaux » :
  <https://www.vd.ch/mobilite/loffre-de-mobilite-a-votre-disposition/transports-individuels-motorises-tim/restrictions-de-circulation-et-travaux> ;
  actualité du 26.07.2021 :
  <https://www.vd.ch/actualites/actualite/news/14688i-sinformer-sur-les-restrictions-de-circulation-des-routes>.
- Exemple d'avis DGMR : <https://www.gimel.ch/files/1781161197-rc-26-c-s-st-george-longirod-restr-50172.pdf>.
- Comptes du 13 octobre : recherche #2, `docs/recherche/fraicheur-sources-direct.md` (branche
  `research/fraicheur-sources-direct`).
- Limites des communes : `web/static/communes-limites.json` et `web/static/communes.json` du dépôt.
