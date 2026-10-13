# Feuille de route (provisoire)

> Ce fichier est temporaire : il garde la planification jusqu'à sa migration vers GitHub, avec un milestone par
> jalon et une issue par élément. Il sera supprimé une fois cette migration faite. Le vocabulaire est défini dans
> `CONTEXT.md`, les décisions dans `docs/adr/` et les sources dans `docs/sources.md`.

## Point de départ

La branche `prototype/live-api`. L'étiquette `chantiers-hebergee` conserve le `main` actuel (la version qui héberge
les données), puis une PR remplace `main` par `prototype/live-api`. Chaque jalon a ensuite sa propre branche et sa
propre PR.

## Interface visée (J0)

- **Écrans** : conçu d'abord pour le bureau ; sur mobile, la carte passe en plein écran et la fiche en tiroir.
- **Couches** activables depuis un panneau : Permis, Hôtels de ville, Routes, Trains, Incidents, Météo, Presse…
- **Un marqueur « hôtel de ville » par commune** (position : voir `docs/sources.md`).
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

## Jalons

Chaque jalon est publiable seul. L'ordre suit les priorités : conseils, routes, trains, presse, météo, radios,
accidents.

| Jalon | Contenu |
|---|---|
| **J0 Socle** | Renommage, licence, registre des couches, fiche commune à onglets (seulement ceux des couches présentes), hôtels de ville, dépôt de données et cron (qui surveille les sources pour la Couverture), page Couverture, badges de fraîcheur, permis migrés en couche, suppression du code de la version hébergée ; à la fin, dépôt rendu public sous le nom `vigie-vaud` et GitHub Pages activé. Décisions : carte [#1](https://github.com/Louni-M/CyberSwissNews/issues/1) |
| **J1 Conseils** | OpenParlData (Grand Conseil, conseil communal de Lausanne, séances d'Yverdon) ; section « Au Grand Conseil » dans la fiche de chaque commune mentionnée ; fil cantonal |
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
  l'adresse GitHub Pages ouverte à la fin de J0.

## Actions de Loulou

- Contacter OpenParlData au sujet des scrapers communaux.
- Créer le compte opentransportdata.swiss et accepter les conditions OFROU (phase 2).
- Acheter le nom de domaine (après J4).
