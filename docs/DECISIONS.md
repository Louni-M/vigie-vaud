# Vigie Vaud — décisions de conception

Décisions prises le 13 octobre 2026, avant le développement. Les sources ont été vérifiées le même jour : appels
`curl` avec un en-tête `Origin`, lecture de `Access-Control-Allow-Origin`. Ce document fait référence : une
décision qui change se modifie ici.

## Produit

- **Vigie Vaud** est un tableau de bord du canton de Vaud. Il reprend l'esprit de
  [World Monitor](https://github.com/koala73/worldmonitor), mais à l'échelle d'un canton. Chantiers Vaud (les
  permis de construire) en devient une couche parmi d'autres.
- **Public** : d'abord les habitants. Le ton est neutre et informatif : le site informe, il ne prend pas position.
  Un mode dense façon « salle de crise » viendra plus tard.
- **Périmètre** : Vaud seulement, sans architecture multi-cantons.
- **Non commercial** : ni publicité, ni abonnement, ni revente de données. Certaines sources en dépendent
  (Open-Meteo, résultats de votations).
- **Licence AGPL-3.0**. On s'inspire des idées de World Monitor (AGPL-3.0) sans en copier le code.
- **Langue** : le site est en français seulement.
- **Écrans** : conçu d'abord pour le bureau ; sur mobile, la carte passe en plein écran et la fiche en tiroir.
- **Pas d'IA dans le MVP**. Des résumés pourront venir plus tard, générés au scraping et non dans le navigateur.

## Interface

- **Couches** activables depuis un panneau : Permis, Hôtels de ville, Routes, Trains, Incidents, Météo, Presse…
- **Un marqueur « hôtel de ville » par commune**. Il est placé grâce à OpenStreetMap
  (`amenity=townhall`), position vérifiée une fois et versionnée par `pipeline/communes.py` ; à défaut, au centre
  de la commune.
- Un clic sur ce marqueur ouvre la **fiche commune**, organisée en onglets : Conseil, Permis, Presse, Radio,
  Météo. Elle remplace et étend `/commune/[slug]`.
- **Le Grand Conseil** a son propre marqueur, au Parlement vaudois (Cité, Lausanne).
- **Fil cantonal** en colonne latérale : les nouveautés de toutes les sources, filtrables par type et recadrées
  sur la zone visible de la carte.
- **État dans l'URL** : couches actives et commune ouverte, comme aujourd'hui.
- **Transparence** :
  - une page **Couverture** liste les 300 communes avec l'état de chaque source (API, scrapé, non couvert, en
    panne depuis…) ;
  - les communes non couvertes sont grisées sur la carte ;
  - chaque couche porte un **badge de fraîcheur** (« il y a 4 min · DGMR ») et l'attribution de sa source.
- Les autres choix restent ceux de Chantiers Vaud : Svelte 5, MapLibre, fond swisstopo, mesure d'audience
  GoatCounter et continuité visuelle.

## Architecture

- **Point de départ** : la branche `prototype/live-api`. L'étiquette `chantiers-hebergee` conserve le `main`
  actuel (la version qui héberge les données), puis une PR remplace `main` par `prototype/live-api`. Chaque jalon
  a ensuite sa propre branche et sa propre PR.
- **Trois voies d'accès aux données** :
  1. **Le navigateur en direct**, dès que la source le permet (CORS ouvert, pas de clé). C'est la voie par
     défaut.
  2. **Un cron GitHub Actions** (Python + uv, dans `pipeline/`, toutes les 30 min) pour les flux RSS et les
     scrapers. Il écrit du JSON dans un **dépôt séparé `vigie-vaud-donnees`**, publié sur ses propres GitHub
     Pages et lu par le site. L'historique git sert d'archive, et le site n'est pas reconstruit à chaque passage.
  3. **Un Worker Cloudflare** (offre gratuite), seulement en **phase 2**. Il relaie les API temps réel à clé ou
     sans CORS (DATEX II, GTFS-RT, SIRI-SX), avec un cache commun à tous les visiteurs.
- On passe à un vrai serveur seulement si des alertes ou une recherche plein texte deviennent nécessaires.
- **Schéma commun** : un schéma JSON partagé, dont on génère les types TypeScript du site.

## Données scrapées : règles

- On ne stocke que des **métadonnées et un lien** : titre, date, type, auteur·e élu·e, commune, URL source.
  Jamais de texte intégral, qu'il s'agisse de procès-verbaux ou d'articles. Les PDF sont lus pour en extraire les
  métadonnées, jamais republiés.
- **Politesse envers les sites** : respect de `robots.txt`, débit limité, User-Agent qui identifie le robot avec
  une adresse de contact.
- **Noms** : les élu·e·s sont nommé·e·s (mandat public) ; les noms de particuliers sont masqués
  (`web/src/lib/masquage.ts`).
- **Conservation** :
  - objets parlementaires : tout l'historique, avec rattrapage rétroactif quand le site source a des archives ;
  - presse : fenêtre glissante de 30 jours.
- **Rattachement à une commune** : par le nom de la commune dans le titre ou la description, d'après la liste
  officielle des communes et une liste d'exclusions pour les noms ambigus (Belmont, Mont-sur-…, Corcelles…).
  Sans rattachement, l'élément reste dans le fil cantonal seulement.

## Jalons

Chaque jalon est publiable seul. L'ordre suit les priorités : conseils, routes, trains, presse, météo, radios,
accidents.

| Jalon | Contenu |
|---|---|
| **J0 Socle** | Renommage, licence, registre des couches, fiche commune à onglets, hôtels de ville, dépôt de données et cron, page Couverture, badges de fraîcheur, permis migrés en couche |
| **J1 Conseils** | OpenParlData (Grand Conseil, conseil communal de Lausanne, séances d'Yverdon) ; section « Au Grand Conseil » dans la fiche de chaque commune mentionnée |
| **J2 Routes** | Restrictions de circulation DGMR en cours et à venir |
| **J3 Trains** | Panneau des perturbations CFF filtré sur Vaud ; gares sur la carte, départs et retards au clic |
| **J4 Presse et incidents** | Flux RSS via le cron ; couche « Incidents » tirée des communiqués de police et rattachée aux communes |
| **J5 Météo** | Mesures actuelles MétéoSuisse ; prévisions Open-Meteo dans la fiche ; pas d'alertes officielles (pas en données ouvertes), lien vers MétéoSuisse à la place |
| **J6 Radios** | Lecteur persistant, environ 8 stations choisies à la main, « Radios locales ici » par commune, raccourci vers le dernier journal RTS |

### Phase 2

- **Scrapers communaux** pour Yverdon (objets), Montreux, Nyon, Renens, Vevey, Pully, Morges et Gland.
  - Ils produisent ce qu'OpenParlData appelle *affairs* et *meetings* :
    - les **séances**, avec leur date et leur ordre du jour ;
    - les **objets** (interpellations, motions, postulats, préavis, questions), avec type, titre, auteur·e, date
      et statut ;
    - le lien vers le PDF.
  - Chaque scraper est testé sur des pages HTML enregistrées.
  - En production, un résultat vide ou un format inattendu ouvre une **issue GitHub** et passe la commune « en
    panne » sur la page Couverture.
  - Le format compatible avec OpenParlData permet de leur proposer ces scrapers (le contact est pris par Loulou).
- **Worker Cloudflare** :
  - bouchons et incidents autoroutiers (ASTRA DATEX II) ;
  - carte des retards du réseau (GTFS-RT).
  - Prérequis : un compte opentransportdata.swiss et l'acceptation des conditions de l'OFROU, à la charge de
    Loulou.
- **Accidentologie OFROU** : couche historique 2011–2025, filtrable par année, gravité et type.

### Backlog

- **Environnement** : niveaux du Léman et des rivières, danger d'incendie, pollen, avalanches.
- **Votations fédérales** : résultats par commune les dimanches de vote, via un relais. Licence à vérifier.
- **Feuille officielle suisse du commerce** : entreprises seulement, sans faillites ni poursuites de
  particuliers.
- **Un flux RSS par commune** généré par le cron, en remplacement des comptes et des alertes.
- **Résumés IA** et **mode dense**.
- **Nom de domaine** (par exemple `vigievaud.ch`), après J4, acheté par Loulou. En attendant, le site garde
  l'adresse GitHub Pages actuelle.

## Sources retenues

**Accès** :

- **Direct** : le navigateur appelle la source.
- **Cron** : le flux passe par le cron GitHub.
- **Worker** : la source passe par le Worker Cloudflare (phase 2).

| Domaine | Source | Accès | Remarques |
|---|---|---|---|
| Permis | `ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/537` | Direct | Existant |
| Parlement | `api.openparldata.ch/v1/` | Direct | CC BY 4.0, « Source: OpenParlData.ch ». Vaud : Grand Conseil (`body_key=VD`), Lausanne (`5586`), Yverdon (`5938`, séances seulement). Ni votes ni débats |
| Routes | `ogc.vd.ch/…/wmsVD/MapServer/596` (en cours), `/595` (à venir) | Direct | Restrictions de circulation DGMR |
| Routes (autoroutes) | ASTRA DATEX II, `api.opentransportdata.swiss/TDP/…` | Worker | SOAP, clé, conditions OFROU |
| Trains | `data.sbb.ch/api/explore/v2.1/catalog/datasets/rail-traffic-information/records` | Direct | Perturbations, filtre Vaud par mots-clés |
| Trains | `transport.opendata.ch/v1/stationboard` | Direct | Départs et retards par gare, cache court |
| Trains (réseau) | `api.opentransportdata.swiss/la/gtfs-rt`, `/la/siri-sx` | Worker | Clé, 2 à 5 requêtes/min |
| Météo | `data.geo.admin.ch/ch.meteoschweiz.messwerte-*-10min/…_fr.json` | Direct | GeoJSON EPSG:2056, « Source: MeteoSwiss » |
| Météo | `api.open-meteo.com/v1/forecast?models=meteoswiss_icon_ch1` | Direct | CC BY 4.0, non commercial |
| Presse | 24 heures (`24heures.ch/rss.html`), Le Temps (`letemps.ch/suisse/vaud.rss`) | Cron | CORS ouvert, mais passés par le cron pour l'archive de 30 jours |
| Presse | RTS Vaud (`rts.ch/info/regions/vaud/?format=rss/news`), 20 minutes (`partner-feeds.20min.ch/rss/20minutes/suisse-romande`), Le Courrier (`lecourrier.ch/feed/`) | Cron | Sans CORS |
| Officiel | vd.ch : communiqués (`/actualites/communiques-de-presse-de-letat-de-vaud/flux.rss`), Grand Conseil (`/gc/flux.rss`) | Cron | Sans CORS |
| Incidents | Police cantonale (`vd.ch/djes/polcant/flux.rss`) | Cron | Lieu dans le titre, rattachement par commune |
| Radios | `stream.srg-ssr.ch/srgssr/{la-1ere,couleur3,espace-2,option-musique}/mp3/128` ; `*.ice.infomaniak.ch` (LFM, Rouge FM, One FM, Radio Lac, Radio Chablais) | Direct | HTTPS obligatoire. Éviter les URL SRG `/m/…`, qui redirigent vers du HTTP |
| Radios (zones) | geo.admin.ch `ch.bakom.versorgungsgebiet-ukw` | Préparé une fois | Libellés possiblement antérieurs aux concessions 2025, à recouper avec l'annexe 1 de l'ORTV (RS 784.401) |
| Accidents (historique) | geo.admin.ch `ch.astra.unfaelle-personenschaeden_alle` | Direct | Annuel, 2011–2025 |

**Écartées** :

- **FAO Vaud** : payante, sans API.
- **La Région** : flux figé depuis juillet 2025.
- **Lausanne Cités** : flux vide.
- **La Côte** : aucun flux.
- **Keystone-ATS** : payant.
- **Google News** : conditions d'utilisation floues, une requête par commune.
- **Bluesky de la police VD** : inactif depuis août 2025.
- **Alertswiss** : endpoint non officiel.
- **radio-browser.info** : attribution régionale peu fiable.

**Introuvables au 13.10.2026** :

- alertes météo officielles en données ouvertes (annoncées par MétéoSuisse pour fin 2026 au plus tôt) ;
- chantiers de la Ville de Lausanne ;
- API de qualité de l'air vaudoise ;
- journal régional vaudois en podcast.

## Actions de Loulou

- Contacter OpenParlData au sujet des scrapers communaux.
- Créer le compte opentransportdata.swiss et accepter les conditions OFROU (phase 2).
- Acheter le nom de domaine (après J4).
