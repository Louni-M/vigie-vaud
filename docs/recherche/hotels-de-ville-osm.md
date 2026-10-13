# Hôtels de ville dans OpenStreetMap : couverture vaudoise

Recherche pour l'issue #4 (carte #1, « Règles de position des hôtels de ville »). Mesure du 13 octobre 2026.

**Question.** Pour les 300 communes de `web/static/communes.json`, combien ont exactement un `amenity=townhall`
dans leur polygone, combien en ont plusieurs (et lesquels), combien n'en ont aucun ? Comment les communes
fusionnées sont-elles représentées ? Quelle requête Overpass reproduit le comptage ?

## En bref

| Objets `amenity=townhall` par commune | Communes | Habitants |
|---|---:|---:|
| Exactement un | 96 | |
| Plusieurs (toujours deux) | 6 | |
| Au moins un (sous-total) | 102 | 578 744 (67,7 %) |
| Aucun | 198 | 276 362 (32,3 %) |
| **Total** | **300** | **855 106** |

- OSM compte **108 objets** `amenity=townhall` dans le canton (45 nœuds, 58 chemins, 5 relations). Tous tombent
  dans un polygone communal : aucun n'est hors canton ni dans un lac.
- **Deux communes sur trois n'ont aucun `townhall`.** Ce sont surtout des petites communes (132 des 198 ont
  moins de 1000 habitants), mais aussi Pully, Gland, La Tour-de-Peilz, Payerne et Crissier.
- Un seul `townhall` ne garantit pas une bonne position : 21 des 96 n'ont **pas de nom**, un est une
  **grande salle** (Froideville) et un est posé sur une **église** (Le Vaud).
- `townhall:type` est rare (14 objets sur 108) et ne distingue pas l'administration d'une salle. Il ne peut donc
  pas départager les doublons.
- Les doublons s'expliquent par **deux anciennes administrations après une fusion** (Blonay - Saint-Légier,
  Oron) ou par **une salle ou un bâtiment annexe** marqué `townhall` (Lausanne, Morges, Ollon, Prilly).
- **Repli possible** : 14 communes sans `townhall` ont un `office=government` nommé « Administration communale »
  ou équivalent. `building=townhall` n'est utilisé nulle part dans le canton.

## Méthode

1. **Communes** : `web/static/communes.json` (300 communes) et `web/static/communes-limites.json` (polygones WGS84
   simplifiés à 10 m), tels que versionnés sur `prototype/live-api` (commit `8f2158a`). Ces fichiers sont produits
   par `pipeline/communes.py` à partir de swissBOUNDARIES3D (couche `tlm_hoheitsgebiet`, `kantonsnummer == 22`,
   `objektart == "Gemeindegebiet"`, regroupée par `bfs_nummer`). Les habitants sont le champ `einwohnerzahl` de
   cette source.
2. **Points OSM** : une requête Overpass sur la zone administrative `ISO3166-2=CH-VD` (voir plus bas). Les chemins
   et les relations sont réduits à leur centre (`out center`). Base OSM : `2026-10-13T19:40:50Z`
   (`osm3s.timestamp_osm_base` de la réponse, servie par `overpass-api.de`).
3. **Croisement** : un test point-dans-polygone (Shapely, `STRtree.query(predicate="within")`) sur les
   polygones simplifiés. Aucun point n'est tombé hors polygone ; la simplification n'a donc pas d'effet ici.
4. **Fusions** : liste officielle des mutations de l'OFS (API de l'*Historisiertes Gemeindeverzeichnis*,
   `https://www.agvchapp.bfs.admin.ch/api/communes/mutations?startPeriod=01-01-2000&endPeriod=13-10-2026`).
   Une fusion est une mutation où plusieurs communes initiales aboutissent à une commune vaudoise actuelle.
5. **Repli** : une seconde requête Overpass pour `building=townhall`, `office=government`,
   `disused:amenity=townhall` et `was:amenity=townhall` (base `2026-10-13T19:42:51Z`).

Les deux requêtes ont d'abord reçu des réponses 504 (« The server is probably too busy ») ; elles ont abouti au
deuxième essai, une minute plus tard. Il faut donc prévoir des nouvelles tentatives espacées si le pipeline
interroge Overpass.

## Requêtes Overpass reproductibles

Comptage principal (à envoyer en POST sur `https://overpass-api.de/api/interpreter`) :

```
[out:json][timeout:120];
area["ISO3166-2"="CH-VD"]["boundary"="administrative"]->.vd;
nwr["amenity"="townhall"](area.vd);
out tags center;
```

La réponse compte 108 éléments. Le rattachement à une commune se fait ensuite localement avec les polygones de
`communes-limites.json` (la zone `area.vd` ne sert qu'à borner la requête).

Repli (tags voisins) :

```
[out:json][timeout:120];
area["ISO3166-2"="CH-VD"]["boundary"="administrative"]->.vd;
(
  nwr["building"="townhall"](area.vd);
  nwr["office"="government"](area.vd);
  nwr["disused:amenity"="townhall"](area.vd);
  nwr["was:amenity"="townhall"](area.vd);
);
out tags center;
```

Exemple avec `curl` :

```sh
curl -A "vigie-vaud/0.1 (projet citoyen non commercial)" \
  --data-urlencode "data@requete.overpassql" https://overpass-api.de/api/interpreter -o townhalls.json
```

## Ce que dit le wiki OSM

- `amenity=townhall` désigne un hôtel de ville, siège fréquent de l'exécutif, mais aussi parfois un simple lieu
  de réunion communautaire. Le wiki précise qu'un `townhall` n'a pas forcément de fonction administrative
  ([Tag:amenity=townhall](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dtownhall)). Les « grandes salles »
  vaudoises ainsi marquées ne sont donc pas des erreurs au sens d'OSM, mais elles ne conviennent pas à notre
  marqueur.
- `townhall:type` décrit le type d'hôtel de ville ; ses valeurs les plus courantes (`city`, `town`,
  `municipality`, `village`) traduisent le niveau de la collectivité, pas la nature du bâtiment
  ([Key:townhall:type](https://wiki.openstreetmap.org/wiki/Key:townhall:type)). Seule la pratique française
  (`main` contre annexes) servirait à départager les doublons, et elle n'est pas utilisée en Suisse.

## Détail : exactement un `townhall` (96 communes)

Les noms se répartissent ainsi :

| Nom | Communes |
|---|---:|
| « Administration communale » (toutes casses et variantes « … de X ») | 41 |
| « Hôtel de Ville » (avec variantes) | 11 |
| « Maison de Commune / de Ville » (avec variantes) | 9 |
| Autres noms administratifs (« Administration générale », « Mairie », « Greffe municipale… », « Secrétariat municipal », « Municipalité de… », « Commune de… », « Ville de Cossonay », « Le Château » à Lutry, « Eclépens ») | 13 |
| **Sans nom** | **21** |
| « Grande Salle » (Froideville) | 1 |

`townhall:type` n'est présent que sur 13 de ces 96 objets (`municipality` 6, `village` 6, `city` 1). Tévenon
est marquée `city` alors que c'est un village : la valeur n'est pas fiable.

On peut retenir comme **position plausible** les 74 objets nommés comme une administration. Les 21 sans nom
sont probablement justes pour la plupart, mais rien ne permet de le vérifier sans aller voir. Il en va de même
pour la grande salle de Froideville.

## Détail : plusieurs `townhall` (6 communes)

| Commune | Objets OSM | Lecture |
|---|---|---|
| Blonay - Saint-Légier | `node/6040627615` « Administration communale » (Blonay, Route du Village) ; `way/41729738` « Siege Communal » (Saint-Légier-La Chiésaz, Route des Deux-Villages) | Fusion de 2022 : les deux anciennes administrations |
| Oron | `node/8569705893` « Administration communale » (Oron-la-Ville, Le Bourg, `townhall:type=village`) ; `way/210083658` « Administration communale » (Palézieux-Village, Grand-Rue) | Fusions de 2012 et 2022 : deux sites administratifs |
| Lausanne | `way/44386403` « Hôtel de Ville » (Place de la Palud, `building=government`) ; `node/12558458319` « Préfecture Lausanne » | La préfecture est cantonale : marquage erroné |
| Morges | `way/197526213` « Hôtel de Ville » ; `way/300130278` « Bâtiment administratif » | Hôtel de ville et bâtiment annexe |
| Ollon | `way/97020125` « Administration communale » (Place du Cotterd) ; `relation/3359350` « Grande Salle » | Salle communale |
| Prilly | `way/220407133` « Administration communale » (Route de Cossonay) ; `node/1668077949` « Grande salle de Prilly » | Salle communale |

Aucun de ces 12 objets n'a de `townhall:type`, sauf celui d'Oron-la-Ville (`village`). Une règle fondée sur le
nom suffirait pour les 4 derniers cas : écarter « Préfecture » et « Grande salle », préférer « Hôtel de Ville »
à « Bâtiment administratif ». Pour les deux communes fusionnées, il faut choisir le siège officiel, ce qu'OSM ne
dit pas.

## Communes fusionnées

**Dans nos données** : une commune fusionnée n'a qu'un numéro OFS et qu'un polygone. swissBOUNDARIES3D décrit
déjà le territoire actuel, et `pipeline/communes.py` regroupe les parties d'une même commune (`dissolve` par
`bfs_nummer` et `name`), ce qui donne 6 communes en plusieurs morceaux. Les anciennes communes n'y existent plus.

**Dans OSM** : rien ne marque une commune comme « fusionnée ». Les anciennes maisons de commune restent
cartographiées comme `amenity=townhall` lorsqu'elles servent encore (Blonay - Saint-Légier, Oron), avec dans
`addr:city` le nom de l'ancienne commune ou de la localité.

**Comptage** : 26 communes vaudoises actuelles sont issues d'au moins une fusion depuis 2000 (liste OFS). Leur
couverture n'est pas meilleure que la moyenne :

| `townhall` | Communes fusionnées |
|---|---|
| Aucun (13) | Assens, Avenches, Cudrefin, Donneloye, Echichens, Hautemorges, Jorat-Menthue, Jorat-Mézières, Lucens, Montanaire, Rovray, Valbroye, Villarzel |
| Un (11) | Aubonne, Bourg-en-Lavaux, Champvent, Chavornay, Goumoëns (sans nom, à Goumoens-la-Ville), Maracon, Montilliez, Servion, Tévenon, Vully-les-Lacs (sans nom), Yverdon-les-Bains |
| Deux (2) | Blonay - Saint-Légier, Oron |

Les fusions d'avant 2000 (par exemple Arzier-Le Muids) ne figurent pas dans cette liste.

## Détail : aucun `townhall` (198 communes)

Les plus peuplées : Pully (19 538 hab.), Gland (13 987), La Tour-de-Peilz (12 812), Payerne (10 758), Crissier
(10 676), Chavannes-près-Renens (9774), Echallens (6719), Rolle (6540), Saint-Prex (5865), Préverenges (5260),
Sainte-Croix (5139), Avenches (4875), Le Chenit (4753), Lucens (4736), Hautemorges (4383).

### Repli par `office=government` (20 communes concernées)

Aucun objet `building=townhall`, `disused:amenity=townhall` ni `was:amenity=townhall` dans le canton. En revanche,
20 des 198 communes ont au moins un `office=government` :

- **Nom d'administration communale (14)** : Belmont-sur-Lausanne (`way/108492899`), Bremblens (`way/118241933`),
  Chavannes-près-Renens (`node/4908695776` « Hôtel de Ville de Chavannes-près-Renens »), Coinsins
  (`node/9602589470`), Corcelles-près-Payerne (`node/12680444450`), Echallens (`node/9812596697`), Etagnières
  (`node/14028096514`), Hautemorges (`node/5890000586`), La Tour-de-Peilz (`node/4250011490`),
  Oulens-sous-Echallens (`node/4460992958` « Bâtiment communal »), Préverenges (`node/7131426167`),
  Romanel-sur-Morges (`node/5313776913` « Administration générale »), Veytaux (`node/8408103852`),
  Villars-le-Terroir (`node/12073285566`).
- **Ambigus (4)** : Avenches (« services extérieurs de la commune »), Pully (« Office de la population »), Gland
  (`way/288393301`, sans nom), Sainte-Croix (`node/12164929230`, sans nom).
- **Faux amis (2)** : Crissier (un centre culturel marqué `office=government`), Saint-Prex (protection civile du
  district).

Ce repli porterait la couverture plausible de 102 à 116 communes. `government=*` n'aide pas à filtrer : la
valeur est absente sur 51 des 94 objets `office=government` du canton, et les autres sont hétérogènes (`administrative`, `yes`,
`greffe_communal`, `Administration_communale_et_greffe`…).

<details>
<summary>Liste complète des 198 communes sans <code>amenity=townhall</code></summary>

Aclens, Agiez, Allaman, Arnex-sur-Nyon, Arnex-sur-Orbe, Arzier-Le Muids, Assens, Avenches, Ballaigues, Ballens,
Bassins, Begnins, Belmont-sur-Lausanne, Bercher, Berolle, Bettens, Bière, Bioley-Magnoux, Bofflens, Bonvillars,
Borex, Bottens, Bougy-Villars, Boulens, Bournens, Bremblens, Bretigny-sur-Morrens, Bretonnières, Buchillon,
Bullet, Bursinel, Bursins, Burtigny, Bussy-sur-Moudon, Chamblon, Champagne, Champtauroz, Chavannes-de-Bogis,
Chavannes-des-Bois, Chavannes-le-Chêne, Chavannes-le-Veyron, Chavannes-près-Renens, Chavannes-sur-Moudon,
Chêne-Pâquier, Cheseaux-Noréaz, Chéserex, Chessel, Clarmont, Coinsins, Concise, Corbeyrier, Corcelles-le-Jorat,
Corcelles-près-Concise, Corcelles-près-Payerne, Crans (VD), Crassier, Crissier, Cronay, Cudrefin, Curtilles,
Daillens, Démoret, Denens, Dizy, Dompierre (VD), Donneloye, Duillier, Dully, Echallens, Echichens, Ependes (VD),
Essertines-sur-Rolle, Essertines-sur-Yverdon, Etagnières, Etoy, Eysins, Féchy, Ferreyres, Fey, Fiez,
Fontaines-sur-Grandson, Gingins, Gland, Gollion, Grandevent, Grens, Hautemorges, Henniez, Hermenches,
Jorat-Menthue, Jorat-Mézières, Jouxtens-Mézery, Juriens, L'Abbaye, L'Abergement, La Chaux (Cossonay), La Praz,
La Tour-de-Peilz, Lavey-Morcles, Le Chenit, Le Lieu, Les Clées, Lignerolle, Longirod, Lucens, Luins, Lully (VD),
Lussery-Villars, Lussy-sur-Morges, Marchissy, Mathod, Mauborget, Mauraz, Missy, Moiry, Mollens (VD), Molondin,
Mont-la-Ville, Mont-sur-Rolle, Montanaire, Montcherand, Montricher, Morrens (VD), Mutrux, Novalles, Noville,
Ogens, Onnens (VD), Oppens, Orges, Ormont-Dessus, Orny, Orzens, Oulens-sous-Echallens, Pailly, Payerne, Penthaz,
Penthéréaz, Perroy, Poliez-Pittet, Pompaples, Premier, Préverenges, Provence, Pully, Rances, Roche (VD), Rolle,
Romainmôtier-Envy, Romanel-sur-Lausanne, Romanel-sur-Morges, Ropraz, Rossenges, Rossinière, Rovray, Rueyres,
Saint-Barthélemy (VD), Saint-George, Saint-Livres, Saint-Oyens, Saint-Prex, Sainte-Croix, Saubraz, Senarclens,
Sergey, Signy-Avenex, Suchy, Sullens, Suscévaz, Syens, Tannay, Tartegnin, Tolochenaz, Treycovagnes,
Treytorrens (Payerne), Ursins, Valbroye, Valeyres-sous-Montagny, Valeyres-sous-Rances, Valeyres-sous-Ursins,
Vaulion, Vaux-sur-Morges, Veytaux, Villars-Epeney, Villars-le-Comte, Villars-le-Terroir, Villars-Sainte-Croix,
Villars-sous-Yens, Villarzel, Vinzel, Vuarrens, Vucherens, Vugelles-La Mothe, Vuiteboeuf, Vulliens, Vullierens,
Yens, Yvorne.

</details>

## Cas problématiques à vérifier

| Commune | Objet OSM | Problème |
|---|---|---|
| Lausanne | `node/12558458319` | Préfecture (cantonale) marquée `townhall` en plus de l'Hôtel de Ville |
| Morges | `way/300130278` | « Bâtiment administratif » en plus de l'Hôtel de Ville |
| Ollon | `relation/3359350` | « Grande Salle » marquée `townhall` |
| Prilly | `node/1668077949` | « Grande salle de Prilly » marquée `townhall` |
| Froideville | `node/2327805018` | Seul `townhall` de la commune, mais c'est une « Grande Salle » |
| Le Vaud | `way/534662772` | `townhall` sans nom sur un bâtiment `building=church` (avec `religion=christian`) |
| Blonay - Saint-Légier | `node/6040627615`, `way/41729738` | Deux sièges hérités de la fusion de 2022 ; OSM ne dit pas lequel est le siège |
| Oron | `node/8569705893`, `way/210083658` | Deux administrations (Oron-la-Ville, Palézieux-Village) |
| Tévenon | `way/308732930` | `townhall:type=city` pour un village : la valeur n'est pas fiable |
| 21 communes | — | `townhall` sans nom, impossible à vérifier sans contrôle visuel : Aigle, Boussens, Echandens, Founex, Genolier, Goumoëns, Jongny, Le Vaud, Lonay, Lovatens, Mex (VD), Mies, Montagny-près-Yverdon, Penthalaz, Puidoux, Rougemont, Trey, Trélex, Vallorbe, Villeneuve (VD), Vully-les-Lacs |
| Crissier | `node/2969052922` | `office=government` sur un centre culturel : à exclure d'un repli `office=government` |

## Ce que cela implique pour le ticket « Règles de position » (non décidé)

Pistes tirées des mesures, à trancher dans le ticket de conception :

- OSM seul ne couvre qu'une commune sur trois. Le repli sur le centre de la commune prévu par `docs/sources.md`
  servira donc pour la majorité des communes, à moins d'élargir aux `office=government` (+14) ou de saisir les
  positions à la main.
- Une règle sur le nom (préférer « Hôtel de Ville » ou « Administration communale », écarter « Grande salle » et
  « Préfecture ») règle 4 des 6 doublons et le cas de Froideville. `townhall:type` n'apporte rien.
- Les communes fusionnées avec deux sièges (Blonay - Saint-Légier, Oron) demandent un choix explicite, à
  versionner avec la position.
- La vérification unique prévue par `docs/sources.md` porte au minimum sur les 21 objets sans nom et sur les cas
  du tableau ci-dessus.

## Sources

- Overpass API, `https://overpass-api.de/api/interpreter`, bases OSM `2026-10-13T19:40:50Z` et
  `2026-10-13T19:42:51Z`. Données © les contributeurs d'OpenStreetMap, ODbL.
- Wiki OSM : [Tag:amenity=townhall](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dtownhall),
  [Key:townhall:type](https://wiki.openstreetmap.org/wiki/Key:townhall:type) (lus le 13 octobre 2026).
- OFS, répertoire historisé des communes, API des mutations :
  `https://www.agvchapp.bfs.admin.ch/api/communes/mutations?startPeriod=01-01-2000&endPeriod=13-10-2026`.
- swisstopo, swissBOUNDARIES3D, via `pipeline/communes.py` et `web/static/communes*.json` (`prototype/live-api`,
  commit `8f2158a`).
