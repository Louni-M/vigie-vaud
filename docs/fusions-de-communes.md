# Fusion de communes : liste de contrôle

Pour la personne qui tient le projet, à chaque 1er janvier où des communes vaudoises fusionnent. Les étapes sont dans
l'ordre ; chacune dit ce qui la débloque. Les données de référence (limites des communes, hôtels de ville, lacs) sont
des sources **Préparées** : rien ne les met à jour seul.

## Fusions connues au 1er janvier 2027

Quatre fusions, d'après la page du Canton
[« Fusions au 1er janvier 2027 »](https://www.vd.ch/territoire-et-construction/cadastre-et-geoinformation/geodonnees/fusions-de-communes/fusions-au-1er-janvier-2027)
(consultée le 13 novembre 2026). Le nom de chaque nouvelle commune vient de l'article 2 de la convention de fusion,
cité dans l'exposé des motifs et projet de décret du Conseil d'État au Grand Conseil. Les n° OFS sont ceux
d'aujourd'hui (`web/static/communes.json`) ; ceux des nouvelles communes ne sont pas encore publiés (étape 2).

| Nouvelle commune | Communes qui fusionnent (n° OFS actuel) | Source du nom |
|---|---|---|
| La Vallée de Joux | L'Abbaye (5871), Le Chenit (5872), Le Lieu (5873) | [24_LEG_213](https://www.vd.ch/fileadmin/user_upload/organisation/gc/fichiers_pdf/2022-2027/24_LEG_213_TexteCE.pdf), mars 2025 |
| Lucens | Lucens (5675), Curtilles (5669) | [25_LEG_103](https://www.vd.ch/fileadmin/user_upload/organisation/gc/fichiers_pdf/2022-2027/25_LEG_103_TexteCE.pdf), juillet 2025 |
| Mathod-Suscévaz | Mathod (5919), Suscévaz (5930) | [25_LEG_172](https://www.vd.ch/fileadmin/user_upload/organisation/gc/fichiers_pdf/2022-2027/25_LEG_172_TexteCE.pdf), octobre 2025 |
| Gimel | Gimel (5428), Saint-Oyens (5436), Saubraz (5437) | [25_LEG_173](https://www.vd.ch/fileadmin/user_upload/organisation/gc/fichiers_pdf/2022-2027/25_LEG_173_TexteCE.pdf), octobre 2025 |

Dix communes en font quatre : le canton passe de 300 à **294 communes**. Les chiffres de la presse (297, 294) ne
concordent pas : seul le décompte ci-dessus fait foi.

Déjà prévu dans le code : `pipeline/preparation_sources.py` (`NON_DECLAREES`) ne déclare ni Le Lieu (i-web) ni
Lucens (Quicksite), qui disparaissent (ADR 0010). Aucune source de `sources.json` ne cite aujourd'hui l'un des dix
n° OFS ci-dessus.

## 1. Savoir quand les éditions 2027 sont publiées

**Limites des communes (swissBOUNDARIES3D, swisstopo).** L'édition `AAAA-01` donne l'état au 1er janvier : « L'état
des données swissBOUNDARIES3D 2026 est le 1er janvier 2026 » ([note de mise à jour 2026](https://www.swisstopo.admin.ch/dam/fr/sd-web/GatZCn3GD5L7/swissBOUNDARIES3D_Release2026-FR.pdf)).
Le catalogue STAC de swisstopo liste les éditions parues :

```bash
curl -s "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissboundaries3d/items?limit=100" \
  | python -c "import json,sys; [print(f['id'], f['properties']['created']) for f in json.load(sys.stdin)['features']]"
```

Les fusions de 2027 sont dedans quand `swissboundaries3d_2027-01` apparaît. Jusqu'ici, l'édition de janvier est
parue mi-décembre de l'année d'avant (`2024-01` le 19 décembre 2023, `2025-01` le 18 décembre 2024, `2026-01` le
17 décembre 2025) : c'est un constat, pas un engagement. Des éditions intermédiaires existent (`2025-04`, `2022-05`) ;
on lit toujours celle de janvier.

**Lacs (swissTLMRegio, swisstopo).** Même catalogue, collection `ch.swisstopo.swisstlmregio`. Elle paraît à
l'automne (`swisstlmregio_2026` le 23 septembre 2026) et les lacs ne changent pas avec une fusion : on garde
l'édition en place, sans attendre `swisstlmregio_2027`.

**Répertoire historisé des communes (OFS).** Les anciennes communes viennent de l'[Application des communes
suisses](https://www.agvchapp.bfs.admin.ch). Son service des mutations refuse une date future (« La date
'EndPeriod' ne doit pas être dans le futur », constaté le 13 novembre 2026) : les fusions de 2027 et les n° OFS des
nouvelles communes ne s'y lisent qu'**à partir du 1er janvier 2027**.

```bash
curl -s "https://www.agvchapp.bfs.admin.ch/api/communes/mutations?startPeriod=01-01-2027&endPeriod=$(date +%d-%m-%Y)"
```

**Registres du Canton.** La même page du Canton annonce les limites administratives cantonales pour le 11 janvier
2027, et le registre des bâtiments (RCBat, RegBL) pour le 19 février 2027, en coordination avec l'OFS. Le
répertoire des adresses de bâtiments, d'où l'outil d'initialisation tire les hôtels de ville, est apparié sur le n°
OFS : il peut ne connaître les nouvelles communes qu'après cette date (étape 4).

## 2. Changer l'année des données de référence

Le 1er janvier 2027 ou après, et une fois `swissboundaries3d_2027-01` paru : dans `pipeline/reference.py`, passer
`ANNEE` à `2027`. Cette ligne change l'édition des limites lue par `communes.py` et l'édition des hôtels de ville
écrite dans `web/src/lib/millesimes.json` (badge de fraîcheur). Ne pas toucher à `EDITION_LACS` (étape 1).

Le cache (`data/cache/`) est rangé par édition : les limites de 2026 n'y sont pas relues. Celui de l'outil
d'initialisation garde en revanche l'annuaire de l'UCV et le répertoire des adresses sans édition : vider
`data/cache/hotels-de-ville/ucv/` et `data/cache/hotels-de-ville/adresses.csv.zip` avant l'étape 4.

Relever dans le répertoire de l'OFS (étape 1) le n° OFS de chaque nouvelle commune. Lucens et Gimel gardent leur
nom : rien ne dit encore s'ils gardent leur numéro.

## 3. Liste des communes

```bash
cd pipeline && uv run python communes.py
```

Attendus : 294 communes écrites ; un avertissement « n'est plus une commune, ligne ignorée » pour chaque commune
disparue de `hotels-de-ville.csv`, et « absente de hotels-de-ville.csv, hôtel de ville en repli » pour chaque
nouveau n° OFS. Le répertoire de l'OFS étant lu jusqu'au jour même, la préparation lancée avant le 1er janvier ne
verrait pas les anciennes communes de 2027.

Dans `web/static/communes.json`, vérifier les slugs (`la-vallee-de-joux`, `mathod-suscevaz`, `lucens`, `gimel`) et
les `anciens` qui serviront au Rattachement : Curtilles pour Lucens ; L'Abbaye, Le Chenit et Le Lieu pour La Vallée
de Joux ; Mathod et Suscévaz pour Mathod-Suscévaz ; Saint-Oyens et Saubraz pour Gimel, tous en « Ancienne commune »
de 2027. Une commune qui garde son nom (Lucens, Gimel) n'apparaît pas dans ses propres `anciens`.

## 4. Hôtels de ville

```bash
cd pipeline && uv run python hotels_de_ville.py
```

L'outil réécrit `hotels-de-ville.csv` et `hotels-de-ville-a-revoir.csv` pour les communes actuelles ; les lignes
`manuel` ne bougent jamais. Avant de le lancer :

- La ligne `manuel` de Gimel est sous le n° 5428. Si Gimel reçoit un nouveau numéro, la recopier sous celui-ci après
  avoir vérifié sur le site de la commune que l'administration est toujours Place de l'Union 4.
- Si le répertoire des adresses ne connaît pas encore les nouveaux n° OFS (étape 1, 19 février 2027), les nouvelles
  communes passent en repli et leur position est **approximative**. On peut attendre, ou écrire une ligne `manuel`
  d'après le site de la commune.

Puis relancer `communes.py` (étape 3) : plus aucun avertissement de repli ne doit concerner les quatre communes.

## 5. Sources et Couverture

- `sources.json` : la construction du site échoue si une source cite un n° OFS qui n'est plus une commune actuelle.
  Aucune n'en cite aujourd'hui (voir plus haut) ; le vérifier de nouveau, OpenParlData comprise.
- `pipeline/preparation_sources.py`, `NON_DECLAREES` : retirer Le Lieu (5873) dès qu'il n'est plus une commune,
  et Lucens (5675) seulement si la nouvelle commune reçoit un autre numéro. Mettre à jour le commentaire de
  `pipeline/tests/test_declarations_sources.py` (`LE_LIEU`).
- Mesurer le site des deux nouvelles communes qui succèdent à une commune scrapée, La Vallée de Joux et Lucens, puis
  les déclarer couvertes ou non couvertes avec leur raison (ADR 0010) :

  ```bash
  cd pipeline && uv run python preparation_sources.py i-web --recensement sites.csv
  cd pipeline && uv run python preparation_sources.py quicksite --recensement sites.csv
  ```

  (`sites.csv` : le recensement, une ligne par commune candidate avec son nouveau n° OFS.) La plateforme du site
  de la nouvelle commune peut différer de celle de l'ancienne.
- Tests liés aux données de production, à remettre à 294 communes : `web/src/lib/couverture.test.ts`
  (`toHaveLength(300)`, `300 - 2 - 46`, « sur 300 ») ; relancer aussi `test_declarations_sources.py`,
  `test_rattachement.py`, `test_rattachement_conseils.py` et `test_jeu_annote_rattachement.py`, qui lisent
  `communes.json`.

```bash
cd pipeline && uv run pytest
cd web && pnpm test && pnpm build
```

## 6. Rattrapage

Le Rattachement par le nom se recalcule en relançant le rattrapage (`pipeline/rattachement.py`) : un Objet du Grand
Conseil qui nomme Curtilles ou Saubraz mène alors à Lucens ou à Gimel. Une fois la PR fusionnée, depuis le dépôt de
données, lancer le workflow « Cron » avec la case `rattrapage` cochée, puis, pour chaque nouvelle commune déclarée
scrapée, avec `rattrapage_cible` rempli de son n° OFS. Les précautions de la README (un rattrapage à la fois, hors
d'un passage) s'appliquent.

## 7. Vérifications sur le site

- `/commune/la-vallee-de-joux` et `/commune/mathod-suscevaz` ouvrent la fiche commune, avec « Anciennes communes : … »
  dans l'en-tête.
- `/commune/le-lieu`, `/commune/curtilles`, `/commune/saubraz` mènent à la nouvelle commune (« Le Lieu fait partie
  de La Vallée de Joux depuis 2027 »).
- La Recherche propose « Curtilles → Lucens » et « Suscévaz → Mathod-Suscévaz ».
- Le marqueur Hôtel de ville de chaque nouvelle commune est en terre ferme, sur son administration ou signalé comme
  approximatif.
- La page `/couverture` liste 294 communes ; l'onglet Conseil de La Vallée de Joux et de Lucens suit leur
  déclaration (étape 5).
- Le badge de fraîcheur des limites et des hôtels de ville indique « édition 2027 ».
