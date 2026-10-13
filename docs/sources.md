# Sources de données

Inventaire des sources de Vigie Vaud : celles qu'on utilise, celles qu'on a écartées et celles qu'on n'a pas
trouvées. Les voies d'accès sont définies dans `CONTEXT.md` et justifiées par l'ADR-0004.

Vérification du 13 octobre 2026 : appels `curl` avec un en-tête `Origin`, lecture de
`Access-Control-Allow-Origin`. Une source qui change se modifie ici.

## Sources retenues

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
| Hôtels de ville | OpenStreetMap `amenity=townhall` | Préparé une fois | Position vérifiée une fois et versionnée par `pipeline/communes.py` ; à défaut, centre de la commune |
| Accidents (historique) | geo.admin.ch `ch.astra.unfaelle-personenschaeden_alle` | Direct | Annuel, 2011–2025 |

## Sources écartées

- **FAO Vaud** : payante, sans API.
- **La Région** : flux figé depuis juillet 2025.
- **Lausanne Cités** : flux vide.
- **La Côte** : aucun flux.
- **Keystone-ATS** : payant.
- **Google News** : conditions d'utilisation floues, une requête par commune.
- **Bluesky de la police VD** : inactif depuis août 2025.
- **Alertswiss** : endpoint non officiel.
- **radio-browser.info** : attribution régionale peu fiable.

## Introuvables au 13 octobre 2026

- alertes météo officielles en données ouvertes (annoncées par MétéoSuisse pour fin 2026 au plus tôt) ;
- chantiers de la Ville de Lausanne ;
- API de qualité de l'air vaudoise ;
- journal régional vaudois en podcast.
