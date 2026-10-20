# Sites des communes vaudoises : plateformes et conseils

Recherche pour l'issue #118 (carte #117, J3 Conseils communaux spécifié). Mesure du 20 octobre 2026.

**Question.** Sur quelles plateformes reposent les sites des 300 communes vaudoises, et lesquelles ont un conseil
communal ou un conseil général ? Pour chaque commune : l'URL du site officiel, la plateforme ou le prestataire,
l'URL de la page du conseil si elle se trouve facilement, et ce qu'en dit `robots.txt`.

Le tableau commune par commune est [`sites-communaux.csv`](sites-communaux.csv) (300 lignes, une par n° OFS) ; il
est produit par [`sites-communaux.py`](sites-communaux.py), qui sert aussi à refaire le recensement.

## En bref

- **La moitié des communes (149) sont sur une plateforme communale**, c'est-à-dire un produit vendu à plusieurs
  communes avec la même structure de pages. Elles ne pèsent que **36 % des habitants** : ce sont surtout des
  petites communes. Sept plateformes en couvrent 146 :
  **i-web** (44 communes, 93 219 hab.), **Quicksite** d'eAdmin Solutions (38, 87 806 hab.), **WebForge** (21,
  20 538 hab.), **COMMUNEapp WEB** de Commune Agence (18, 15 907 hab.), **imedia Communes** (14, 65 266 hab.),
  **OIOI web** d'OFISA (6, 7 048 hab.) et **Webcommunes** de WNG (5, 15 660 hab.). Hekl@ (Designis) en ajoute 3.
- **L'autre moitié est faite sur mesure** : 148 sites (49,3 % des communes, 63,7 % des habitants) sur un CMS
  générique avec un thème propre (122, dont **79 WordPress**, 22 Joomla et 9 TYPO3), du code propre (11) ou un
  constructeur de site (14 : Wix, Infomaniak Site Creator…). Les dix plus grandes villes sont toutes sur mesure,
  sauf Ecublens (imedia) : Lausanne (Magnolia), Yverdon-les-Bains, Montreux et Gland (TYPO3), Nyon et Renens (Nuxt), Vevey
  (Drupal), Pully (Umbraco), Morges (Symfony). Aucun prestataire ne domine le sur-mesure : le plus gros en a 4.
- **164 conseils communaux et 136 conseils généraux** (annuaire de l'UCV, une correction). Les conseils communaux
  représentent 795 296 habitants (93 %), les conseils généraux 59 810. Aucun conseil général au-delà de
  1 000 habitants, comme le veut la loi ; 23 communes de 1 000 habitants ou moins ont choisi un conseil communal.
- **Page du conseil trouvée depuis la page d'accueil pour 261 communes.** Aucun `robots.txt` lisible n'interdit la
  page du conseil à notre robot, ni le site entier. 71 sites demandent `Crawl-delay: 10` (surtout ceux hébergés
  chez Infomaniak).
- **i-web coupe l'accès** : après une rafale de requêtes vers plusieurs de ses communes, toute sa plage
  `195.65.10.0/24` (RIPE : IWB-NET, Innovative Web AG) a refusé nos connexions TCP pendant une demi-heure environ.
  Un dernier passage, un site à la fois et 5 secondes entre deux requêtes au même serveur, a lu les 44 communes
  i-web sans incident. Le débit doit se régler par plateforme, pas par commune.

## Synthèse par plateforme

« Plateforme » désigne le produit communal quand il y en a un, sinon le CMS générique, sinon le type de site.
Habitants : population de swissBOUNDARIES3D (`web/static/communes.json`, 855 106 au total).

| Rang | Plateforme | Type | Communes | Habitants | Part des habitants | Conseils communaux / généraux | Page du conseil trouvée |
|---:|---|---|---:|---:|---:|---|---:|
| 1 | WordPress | CMS générique | 79 | 115 126 | 13,5 % | 36 / 43 | 75 |
| 2 | i-web | plateforme communale | 44 | 93 219 | 10,9 % | 30 / 14 | 38 |
| 3 | Quicksite | plateforme communale | 38 | 87 806 | 10,3 % | 26 / 12 | 37 |
| 4 | Joomla | CMS générique | 22 | 23 241 | 2,7 % | 6 / 16 | 20 |
| 5 | WebForge | plateforme communale | 21 | 20 538 | 2,4 % | 10 / 11 | 18 |
| 6 | COMMUNEapp WEB | plateforme communale | 18 | 15 907 | 1,9 % | 8 / 10 | 13 |
| 7 | imedia Communes | plateforme communale | 14 | 65 266 | 7,6 % | 12 / 2 | 14 |
| 8 | TYPO3 | CMS générique | 9 | 105 452 | 12,3 % | 6 / 3 | 9 |
| 9 | sur mesure (code propre, sans CMS reconnu) | code propre | 7 | 29 684 | 3,5 % | 5 / 2 | 6 |
| 10 | OIOI web | plateforme communale | 6 | 7 048 | 0,8 % | 5 / 1 | 1 |
| 11 | Webcommunes | plateforme communale | 5 | 15 660 | 1,8 % | 4 / 1 | 5 |
| 12 | Wix | constructeur de site | 5 | 2 083 | 0,2 % | 1 / 4 | 3 |
| 13 | Infomaniak Site Creator | constructeur de site | 5 | 2 021 | 0,2 % | 0 / 5 | 3 |
| 14 | Hekl@ | plateforme communale | 3 | 2 968 | 0,3 % | 2 / 1 | 3 |
| 15 | injoignable | — | 3 | 2 228 | 0,3 % | 2 / 1 | 0 |
| 16 | Nuxt | code propre | 2 | 44 892 | 5,2 % | 2 / 0 | 1 |
| 17 | Drupal | CMS générique | 2 | 26 788 | 3,1 % | 2 / 0 | 2 |
| 18 | Umbraco | CMS générique | 2 | 23 453 | 2,7 % | 2 / 0 | 2 |
| 19 | October CMS | CMS générique | 2 | 1 822 | 0,2 % | 1 / 1 | 2 |
| 20 | Magnolia | CMS générique | 1 | 144 873 | 16,9 % | 1 / 0 | 0 |
| — | 12 autres (une commune chacune) | | 12 | 25 031 | 2,9 % | 3 / 9 | 9 |

Les douze autres : Symfony (Morges), Hostpoint, Obtic City2Net, Yabrab, Google Sites, Weebly, Odoo, Lochness CMS,
Gatsby, Craft CMS, Mobirise, et un site non identifié (Trey, code écrit par un webmaster).

| Type de site | Communes | Part | Habitants | Part |
|---|---:|---:|---:|---:|
| Plateforme communale | 149 | 49,7 % | 308 412 | 36,1 % |
| CMS générique (thème propre) | 122 | 40,7 % | 444 127 | 51,9 % |
| Code propre | 11 | 3,7 % | 92 731 | 10,8 % |
| Constructeur de site | 14 | 4,7 % | 7 290 | 0,9 % |
| Non identifié | 1 | 0,3 % | 318 | 0,0 % |
| Injoignable | 3 | 1,0 % | 2 228 | 0,3 % |
| **Sur mesure** (CMS générique, code propre, constructeur, non identifié) | **148** | **49,3 %** | **544 466** | **63,7 %** |

## Les plateformes communales

Pour chacune : qui la fait, comment on la reconnaît (motif cherché par le script), à quoi ressemble l'adresse de la
page du conseil, et ce que dit son `robots.txt`.

| Plateforme | Éditeur | Empreinte | Page du conseil (exemples) | `robots.txt` |
|---|---|---|---|---|
| i-web | Innovative Web AG, Wilen b. Wollerau (SZ) | `stats.i-web.ch`, classes `icms-…`, chemins `/_rtr/`, `/_doc/` ; serveurs `195.65.10.20-27` (IWB-NET) et `164.128.171.231` (partagé avec OIOI web) | `/conseil`, `/conseil-general`, `/conseilcommunal` (choisi par chaque commune) | absent (404) ou vide |
| Quicksite | eAdmin Solutions SA, Bussigny (ex-Quicksite SA ; `quicksite.ch` redirige vers `eadmin-solutions.ch`) | `<meta name="generator" content="CMS - Quicksite www.quicksite.ch">`, cookie `lngStatQSSession` | `/N387/conseil-communal.html` (identifiant de nœud + slug) | identique partout : interdit `/qsPortal/Admin.asp`, `/Booking/`, `/DataForms/`… et tout à VoilaBot et libwww-perl |
| WebForge | WebForge, petite équipe lausannoise | `<meta name='generator' content='WebForge 312'>`, `application-name=webforge`, lien « Propulsé par le CMS WebForge » ; chaque page a une version Markdown (`<link rel='alternate' … .md>`) | `/conseil-general-fr1182.html` | sans restriction (souvent juste le `Sitemap`) |
| COMMUNEapp WEB | Commune Agence (marque COMMUNEapp ; « plus de 40 communes romandes », dont une vingtaine aussi pour le site) | scripts sous `/front/agencedudev/`, cookie `csrf_cookie_name` | `/Vie-politique-et-reglements` (ancres `#_8`) | sans restriction |
| imedia Communes | imedia.ch sàrl, Lausanne (offre « Communes », démo smartcommune.ch) ; Joomla | gabarits Joomla `orion`, `tx_next`, `admairiev2` | `/officiel/autorites/conseil-communal.html` | règles Joomla standard ; 6 sites interdisent GPTBot et OAI-SearchBot |
| OIOI web | OFISA Informatique (application « OIOI web », `ch.OI.OFISA1`) | application React servie par Express, images sur `web-prod.o-i.ch` | `/conseil-general` (menu chargé en JavaScript, rarement visible dans le HTML) | absent : `/robots.txt` rend la page 404 de l'application |
| Webcommunes | WNG agence digitale, Lausanne ; TYPO3 | mention « Webcommunes - un produit WNG agence digitale » en pied de page | `/officiel/conseil-communal` | sans restriction |
| Hekl@ | Designis | « site internet réalisé par Designis propulsé avec Hekl@ » | `/conseil.php` | `Crawl-delay: 10` |

WNG fait aussi le site TYPO3 de quatre villes hors Webcommunes (Le Mont-sur-Lausanne, Prilly, Montreux,
Yverdon-les-Bains) ; Prilly et Yverdon chargent le même paquet TYPO3 (`/_assets/7e6a5725…/`). Un scraper
Webcommunes pourrait donc en couvrir davantage, à vérifier.

## Les sites sur mesure

- **WordPress** est le premier « système » vaudois (79 communes), mais chaque site a son thème : Divi, Elementor,
  Astra, Enfold, thèmes enfants nommés d'après la commune… Les prestataires sont dispersés : troisdeuxun (Morges)
  et Cobalt IT ont 3 communes chacun, bvisible 2, les autres une.
- **Joomla** (22) : Nash design (3, YOOtheme), WebPixel (3), Artisan du Web (2), Graphi-Cité (2).
- **TYPO3** (9) : WNG (4 villes, voir plus haut), Mediaterre (Molondin, Cheseaux-Noréaz), Lutry, Gland,
  Chêne-Pâquier.
- **Code propre** (11) : Renens et Nyon (Nuxt ; Renens développé par iomedia, qui fait aussi Morges en Symfony et
  propose une « solution communes »), Romanel-sur-Morges (Gatsby), La Tour-de-Peilz (Equateur), Bourg-en-Lavaux
  (Hawaii Interactive), Cheseaux-sur-Lausanne (Boomerang), Prangins, Fey, Saint-George et Chigny (LemanSites).
- **Constructeurs** : 14 petites communes (moins de 2 000 habitants), dont 12 à conseil général.

La colonne `prestataire` du CSV donne l'agence citée en pied de page (« réalisé par… », « powered by… ») quand
le script l'a trouvée : 214 communes sur 300.

## Conseils communaux et généraux

Source : l'[annuaire des communes de l'UCV](https://www.ucv.ch/annuaire/recherche-par-localite), dont chaque fiche
donne « Conseil Communal : n » ou « Conseil Général : n » (nombre de membres). Je n'ai pas trouvé de liste
complète publiée par le canton.
L'UCV est déjà la source des hôtels de ville (`docs/sources.md`).

| Conseil | Communes | Habitants |
|---|---:|---:|
| Conseil communal | 164 | 795 296 (93,0 %) |
| Conseil général | 136 | 59 810 (7,0 %) |

Contrôles :

- **La loi est respectée.** La loi sur les communes (art. 1a LC, RSV 175.11) prévoit un conseil général jusqu'à
  1 000 habitants et un conseil communal au-delà, une petite commune pouvant choisir le conseil communal. Aucune
  commune de plus de 1 000 habitants n'a de conseil général ; 23 communes de 1 000 habitants ou moins ont un
  conseil communal (Montricher, Grandcour, Rougemont, Le Lieu, Bogis-Bossey…).
- **Ce que disent les sites.** Le lien vers la page du conseil nomme son type sur 261 sites : 259 concordent avec
  l'UCV. Corrigé : **Champvent**, que l'UCV donne « Conseil Communal : 69 » alors que son site ne parle que du
  Conseil général (trois mentions, aucune du conseil communal) ; on retient le conseil général. Laissés à l'UCV :
  **Pailly** et **Tartegnin** (COMMUNEapp WEB), dont le menu dit « Documents du conseil communal » ; c'est le
  libellé du gabarit, et le site de Tartegnin écrit lui-même « Conseil général : 40 membres ». Pailly reste à
  vérifier.
- Trois fiches UCV ne donnent pas le nombre de membres (Rivaz, Arnex-sur-Nyon, Grens).

## `robots.txt`

| État | Sites |
|---|---:|
| Sans restriction (aucune ligne `Disallow` pour nous) | 153 |
| Restrictions partielles (administration, recherche, agents nommés) | 112 |
| Absent (404, ou page HTML servie à la place) | 34 |
| Injoignable | 1 |

- **Aucun site n'interdit la page de son conseil** à notre User-Agent, ni sa racine (261 pages testées avec
  `urllib.robotparser`).
- Les interdictions totales visent des **robots nommés** : VoilaBot et libwww-perl sur tous les Quicksite, GPTBot
  et OAI-SearchBot sur 6 sites imedia, une vingtaine de robots d'IA (ClaudeBot, GPTBot, CCBot…) à Nyon et Renens.
- **`Crawl-delay: 10`** sur 71 sites, presque tous hébergés chez Infomaniak (WordPress, Site Creator, Hekl@) : un
  robot qui le respecte lit au plus 6 pages par minute et par site.

## Surprises

1. **i-web bloque au niveau du réseau.** Le premier passage lisait 8 sites à la fois, une requête par seconde et par
   *nom d'hôte* : une trentaine de communes i-web hébergées sur les mêmes serveurs ont reçu chacune deux requêtes
   en quelques minutes. Toute la plage `195.65.10.0/24` a ensuite refusé nos connexions (délai TCP dépassé, même
   pour les sites déjà lus) pendant une demi-heure environ (coupure constatée de 19 h 05 à 19 h 32 UTC, accès
   rétabli à 19 h 38). Le script limite désormais le débit **par réseau /24** ; le dernier passage, un site à la
   fois avec 5 secondes entre deux requêtes à la même adresse, est passé sans refus.
   Pour le scraper : le débit se règle par plateforme, pas par commune.
2. **Les plateformes servent les petites communes, le sur-mesure les grandes.** 50 % des communes mais 36 % des
   habitants sur plateforme ; les grandes villes ont chacune leur site.
3. **Lausanne** (déjà couverte par OpenParlData, comme Yverdon) : le HTML de sa page d'accueil n'a aucun lien vers
   le conseil communal.
4. **Deux sites absents** : `www.mauraz.ch` et `www.saint-saphorin.ch`, donnés par l'UCV, répondent « web host not
   found » chez Infomaniak (HTTP 503) ; sans `www`, aucune réponse. Eysins (`www.eysins.ch`) n'a pas répondu non
   plus. Assens et Payerne servent un certificat TLS invalide (nom d'hôte, chaîne incomplète) ; leur page a été lue
   sans vérification, et c'est noté dans la colonne `tls_invalide`.
5. **Fusions au 1er janvier 2027** ([communiqué de l'État de Vaud du 2 février 2026](https://www.vd.ch/typo3temp/assets/pdfs/elections-communales-2026-letat-de-vaud-mobilise-les-electrices-et-electeurs-pour-le-scrutin-du-8-mars.pdf)) :
   L'Abbaye, Le Chenit et Le Lieu (WordPress, WordPress, i-web) ; Lucens et Curtilles (Quicksite, imedia) ; Gimel,
   Saubraz et Saint-Oyens (WebForge, WordPress, WebForge) ; Mathod et Suscévaz (WordPress, WebForge). Ces dix
   sites vont changer : les nouvelles communes auront un site et un conseil à elles.
6. **WebForge publie chaque page en Markdown** (`… .md` annoncé dans `<head>`), ce qui pourrait simplifier un
   scraper.

## Méthode

1. **Communes et sites** : l'[annuaire de l'UCV](https://www.ucv.ch/annuaire/recherche-par-localite), 300 fiches
   (une par commune, avec n° OFS), lues le 20 octobre 2026. Chaque fiche donne le site officiel et le type de
   conseil. Les 17 sites déjà notés dans `pipeline/hotels-de-ville.csv` concordent. Un seul site redirige vers un
   autre domaine (Signy-Avenex vers `signy.ch`).
2. **Empreinte** : pour chaque site, `robots.txt` puis la page d'accueil (deux requêtes), User-Agent
   `VigieVaud-recherche/0.1 (+https://github.com/Louni-M/vigie-vaud)`, au plus une requête par seconde et par hôte,
   8 hôtes à la fois. Les sites en échec ou mal décodés (en-tête `content-encoding` en minuscules, non reconnu au
   premier passage) ont été relus, les sites i-web dans un troisième passage plus lent (voir « Surprises »).
   Environ 1 300 requêtes en tout, UCV comprise. Le script cherche, par ordre de priorité : les motifs propres aux
   plateformes communales, puis ceux des CMS et constructeurs (balise `generator`, chemins `/wp-content/`,
   `/templates/…/`, `/typo3conf/`, en-têtes `X-Powered-By`, cookies), puis l'agence citée en pied de page. Les
   motifs sont dans `PLATEFORMES` et `CMS` en tête de l'analyse du script.
3. **Éditeurs** : identifiés par les mentions de pied de page, puis vérifiés sur leur site (`eadmin-solutions.ch`,
   `webforge.ch`, `communeagence.ch`, `imedia.ch`) et, pour les adresses IP, par `whois` (RIPE).
4. **Page du conseil** : le meilleur lien de la page d'accueil dont le texte est « Conseil communal » ou « Conseil
   général » (ou le contient, ou dont l'URL contient `conseil-communal` / `conseil-general`). La page elle-même n'a
   pas été ouverte, et aucun procès-verbal n'a été lu (issue #119).
5. **`robots.txt`** : lu avec `urllib.robotparser` ; on teste la racine et la page du conseil pour notre User-Agent.
6. **Habitants** : `web/static/communes.json` (swissBOUNDARIES3D, champ `einwohnerzahl`, chiffres de la statistique
   de la population de l'OFS).

Pour refaire le recensement (le cache des réponses brutes reste hors du dépôt) :

```
python3 docs/recherche/sites-communaux.py collecte --cache /tmp/sites-communaux
python3 docs/recherche/sites-communaux.py collecte --cache /tmp/sites-communaux --relancer --paralleles 1 --delai 5
python3 docs/recherche/sites-communaux.py analyse  --cache /tmp/sites-communaux > docs/recherche/sites-communaux.csv
```

## Colonnes du CSV

`ofs`, `commune`, `habitants` ; `conseil` (retenu), `membres` et `conseil_ucv` (annuaire UCV), `conseil_selon_site`
(type nommé par le lien de la page d'accueil) ; `site` (UCV), `url_finale` (après redirections), `ip` ;
`plateforme`, `type` (plateforme communale, CMS générique, code propre, constructeur de site, non identifié,
injoignable), `cms`, `prestataire`, `indices` (le motif qui a décidé) ; `page_conseil` ; `robots` (sans restriction,
restrictions, interdit tout, absent, injoignable), `robots_page_conseil` (autorisée, interdite), `crawl_delay` ;
`tls_invalide` ; `date` de la mesure.

## Limites

- **Une page par site** : la page du conseil n'est trouvée que si la page d'accueil y mène par un lien en HTML. Elle
  manque pour 39 communes, surtout quand le menu est chargé en JavaScript (OIOI web, Lausanne) ou que le site est
  injoignable. Le lien retenu peut viser une page voisine (agenda d'une séance, liste des membres, préavis).
- **L'empreinte voit le moteur, pas toujours l'agence.** Un site WordPress sans mention en pied de page reste sans
  prestataire ; deux sites du même prestataire sur WordPress peuvent n'avoir rien en commun.
- **Type de conseil** : l'annuaire de l'UCV n'est pas une source de l'État ; une erreur y a été trouvée
  (Champvent), d'autres sont possibles là où le site ne nomme pas son conseil (39 communes). Le texte de la LC
  consulté est la version consolidée au 1er janvier 2007 publiée sur LexFind ; l'article 1a n'a pas été revérifié
  dans la version en vigueur.
- **Mesure datée** : les sites changent (refontes, fusions de 2027). Le script permet de refaire la mesure.

## Sources

- Union des communes vaudoises, [annuaire des communes](https://www.ucv.ch/annuaire/recherche-par-localite), fiches
  par commune (site, type et taille du conseil, n° OFS), consulté le 20 octobre 2026.
- Les 300 sites communaux (`robots.txt` et page d'accueil), lus le 20 octobre 2026 ; liste dans le CSV.
- [Loi sur les communes (LC, RSV 175.11)](https://www.lexfind.ch/tolv/118052/fr), art. 1a.
- État de Vaud, [communiqué du 2 février 2026 sur les élections communales](https://www.vd.ch/typo3temp/assets/pdfs/elections-communales-2026-letat-de-vaud-mobilise-les-electrices-et-electeurs-pour-le-scrutin-du-8-mars.pdf)
  (fusions au 1er janvier 2027).
- Éditeurs : [eAdmin Solutions SA](https://www.eadmin-solutions.ch/) (cible de `quicksite.ch`),
  [WebForge](https://www.webforge.ch), [Commune Agence / COMMUNEapp](https://www.communeagence.ch),
  [imedia.ch](https://www.imedia.ch).
- RIPE (`whois`) : `195.65.10.0/24` IWB-NET (Innovative Web AG) ; plages Infomaniak (INFOMANIAK-HOSTING,
  INFOMANIAK-NETWORK).
- `web/static/communes.json` (habitants, swissBOUNDARIES3D) et `pipeline/hotels-de-ville.csv` (contrôle des URL).
