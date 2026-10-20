# Ce que publient les conseils, plateforme par plateforme

Recherche pour l'issue #119 (carte #117, J3 Conseils communaux spécifié). Mesure du 20 octobre 2026, qui fait suite
au recensement des sites communaux (#118, branche `research/sites-communaux`, `docs/recherche/sites-communaux.md`).

**Question.** Pour chaque plateforme communale qui couvre au moins quelques communes, et pour les villes à parlement
sur un site fait sur mesure (hors Lausanne et Yverdon, déjà couvertes par OpenParlData) : que publient les conseils
(Séances, Objets), sous quelle forme, avec quelle profondeur d'archive et quelle fraîcheur ? Et qu'en tirerait un
scraper déterministe, sans IA (ADR-0003) ?

Fichiers :

- [`publications-conseils.csv`](publications-conseils.csv) : une ligne par commune mesurée (échantillon lu à la
  main et balayage automatique des pages du conseil), avec les comptages et le niveau estimé ;
- [`publications-conseils.py`](publications-conseils.py) : le robot de mesure (une requête à la fois, 5 s par
  plateforme et par /24, `robots.txt`, cache hors dépôt) et le classement automatique.

## En bref

- **Presque tous les conseils publient de quoi dater leurs Séances ; peu publient leurs Objets.** Sur
  les 149 communes des huit plateformes et les 9 villes sur mesure (158 communes, 477 197 habitants, 56 % du
  canton), un scraper déterministe tirerait, d'après le balayage : **Objets complets** pour 17 communes
  (233 578 habitants), **Séances et préavis** pour 80 (165 162), **Séances seules** pour 40 (56 488), **préavis
  seuls** pour 7 (9 938), **rien** pour 14 (12 031). Le niveau « Objets complets » est presque réservé aux villes
  (8 sur 9) et à 9 communes de 3 800 à 12 500 habitants.
- **i-web est la meilleure plateforme à scraper, Quicksite la plus rentable.** i-web met ses listes en JSON dans
  le HTML (`data-entities`), avec des identifiants stables ; 26 de ses 29 communes donnent au moins leurs Séances.
  Quicksite (38 communes, 87 806 habitants) donne Séances et préavis dans 27 communes, mais demande trois variantes
  (bibliothèque de l'ancienne génération, recherche `coreapi` de la nouvelle, module « Conseil communal »), cette
  dernière partagée avec **Montreux et Vevey**.
- **Correction du recensement** : 15 des 44 communes « i-web » sont sur **OIOI web** (le motif `i-web\.ch`
  attrape `oioi-web.ch`). i-web : 29 communes, 76 573 habitants ; OIOI web : 21 communes, 23 694 habitants.
- **WebForge, OIOI web, COMMUNEapp et imedia sont des pages rédigées à la main** : la structure tient aux
  habitudes du secrétariat, pas au produit. Un scraper par plateforme y lit des titres et des liens ; il casse dès
  que la commune change sa mise en page. Le Markdown de WebForge ne contient pas les liens vers les PDF.
- **Pas besoin d'IA pour les métadonnées** : numéros, titres et dates sont dans le HTML ou le nom du fichier ; 11
  PDF sur 12 testés ont une couche texte (un extrait de PV signé et scanné n'en a pas). Les **statuts** manquent
  presque partout : seuls Renens, Gland, Chavannes-près-Renens, La Tour-de-Peilz et, en texte libre, Pully et
  Saint-Sulpice les donnent ;
  i-web a un champ statut mais ne le tient pas à jour.
- **Les particuliers sont rares dans les titres** (8 repérés dans 4 communes : succession, legs, opposants à un
  plan, acheteur d'une parcelle), mais les élu·e·s y sont souvent nommé·e·s sans « conseiller » devant
  (« (Rapp. M. X) », « Interpellation C. X », noms dans les noms de fichiers) : le masquage par civilité les
  masquerait sans liste d'élu·e·s.
- **Archives** : médiane des premières séances en ligne vers 2020-2021, mais Montreux depuis 2006, Morges et
  Ecublens depuis 2004-2007, Blonay - Saint-Légier depuis 2011. WebForge n'a souvent que la législature en cours.
- **Robot poli, aucun blocage** : 750 requêtes en 70 minutes, une à la fois, 5 s au moins par plateforme et par /24.
  Points d'attention : `robots.txt` Joomla d'imedia qui interdit les PDF, `robots.txt` de Vevey sensible à la casse,
  `Crawl-delay: 10` sur Nyon, Renens, Morges, Prilly et Hekl@, robots d'IA bannis nommément à Nyon et Renens,
  mentions légales qui soumettent toute reproduction à autorisation (Nyon interdit même le stockage « dans un
  système de recherche et d'extraction de données »).

## Correction du recensement : 15 communes « i-web » sont sur OIOI web

Le motif qui reconnaît i-web dans `sites-communaux.py` (`i-web\.ch`) attrape aussi `oioi-web.ch`, que les sites
OIOI web citent dans leur feuille de style et leurs liens vers l'application mobile. Les 15 communes « i-web » du
serveur `164.128.171.231` (Vully-les-Lacs, Arzier-Le Muids, Chéserex, Veytaux, Lavey-Morcles, Rennaz,
Bretigny-sur-Morrens, Rougemont, Denens, Saint-Livres, Buchillon, Coinsins, Bougy-Villars, Rossinière, Missy) sont en
réalité des sites OIOI web : même serveur que les 6 OIOI web reconnus, mêmes pages de texte libre, mêmes PDF sous
`/uploads/<empreinte>/documents/`, aucune trace du HTML d'i-web (`icms-`, `data-entities`, `/_rtr/`). Après
correction :

| Plateforme | Communes | Habitants | Conseils communaux / généraux |
|---|---:|---:|---|
| i-web | 29 (et non 44) | 76 573 | 21 / 8 |
| OIOI web | 21 (et non 6) | 23 694 | 14 / 7 |

Le reste du recensement est inchangé. Le robot de ce document compte i-web et OIOI web comme **une seule
plateforme** pour le débit, par prudence : i-web a coupé tout son /24 lors du recensement, et l'on ne sait pas qui
exploite `164.128.171.231` (adresse Swisscom).

## Les niveaux

Ce qu'un scraper **déterministe** (expressions régulières et structure HTML, pas d'IA, ADR-0003) peut tirer d'une
commune, sans lire le contenu des PDF :

- **Objets complets** : les Séances, et des Objets de plusieurs types (préavis, motions, postulats,
  interpellations…), chacun avec au moins un numéro ou un titre stable, une date, et souvent un auteur·e et un
  statut ; c'est le niveau des *affairs* d'OpenParlData (ADR-0010).
- **Séances et préavis** : les Séances (date, ordre du jour, procès-verbal) et les préavis municipaux (numéro,
  titre, document) ; motions, postulats et interpellations absents ou réduits à des documents sans structure.
- **Séances seules** : des dates de séance, avec ou sans ordre du jour et procès-verbal en PDF.
- **Rien** : pas de page du conseil, ou des documents qu'on ne peut rattacher à une séance ni à un objet sans lire
  le PDF (recueil annuel compilé, liste de fichiers sans date).

## Synthèse par plateforme

Niveau par commune : constaté à la main sur l'échantillon (25 communes des plateformes, 9 villes), estimé
automatiquement ailleurs à partir de la page du conseil et de 2 à 6 sous-pages (voir « Méthode » ; marge d'erreur
réelle, surtout entre « Séances seules » et « Séances et préavis »). Communes (habitants).

| Plateforme | Objets complets | Séances et préavis | Séances seules | Préavis seuls | rien | Total |
|---|---:|---:|---:|---:|---:|---:|
| i-web | 1 (12 464) | 15 (39 506) | 10 (18 374) | 3 (6 229) | — | 29 (76 573) |
| Quicksite | 2 (19 973) | 25 (49 762) | 8 (13 772) | 1 (1 196) | 2 (3 103) | 38 (87 806) |
| WebForge | — | 10 (13 133) | 5 (3 626) | — | 6 (3 779) | 21 (20 538) |
| COMMUNEapp WEB | — | 12 (12 093) | 3 (1 907) | 1 (515) | 2 (1 392) | 18 (15 907) |
| imedia Communes | 4 (36 103) | 6 (25 393) | 1 (527) | — | 3 (3 243) | 14 (65 266) |
| OIOI web | — | 8 (9 409) | 10 (11 773) | 2 (1 998) | 1 (514) | 21 (23 694) |
| Webcommunes | 2 (9 011) | 2 (2 328) | 1 (4 321) | — | — | 5 (15 660) |
| Hekl@ | — | 1 (780) | 2 (2 188) | — | — | 3 (2 968) |
| Villes sur mesure (9) | 8 (156 027) | 1 (12 758) | — | — | — | 9 (168 785) |
| **Total** | **17 (233 578)** | **80 (165 162)** | **40 (56 488)** | **7 (9 938)** | **14 (12 031)** | **158 (477 197)** |

En cumulé : au moins « Séances et préavis » pour **97 communes et 398 740 habitants**, au moins « Séances seules »
pour **137 communes et 455 228 habitants**. Avec Lausanne et Yverdon (OpenParlData, 175 165 habitants), cela fait
630 393 habitants sur 855 106 (74 %) avec au moins des Séances. Les conseils généraux (52 communes mesurées) ne
dépassent jamais « Séances et préavis » : 25 l'atteignent.

Ce que la plateforme permet et ce qu'il en coûte :

| Plateforme | Voie d'accès la plus propre | Plafond | Un scraper pour toutes les communes ? | URL stables |
|---|---|---|---|---|
| i-web | JSON de l'attribut `data-entities` | Objets complets (module Objets, 1 commune) ; sinon Séances et préavis | oui : modules standard, seuls les chemins changent (`/seances`, `/sitzung`, `/preavis`…) | oui (`/_rte/anlass/<id>`, `/_rte/information/<id>`) |
| Quicksite | fragment HTML de `/coreapi/elasticsearch/…/search` ; bibliothèque `/documents` ; module `/conseilcommunal/public/` | Objets complets (ancienne bibliothèque typée, module Conseil) | trois variantes | oui (nœuds `N<id>`, `download.asp?d=`) |
| WebForge | HTML (le `.md` perd les liens) | Séances et préavis | non : titres et texte libres | ID de page dans l'URL (`-fr1181.html`), fichiers horodatés |
| COMMUNEapp WEB | HTML d'une seule page | Séances et préavis | oui pour lire les liens, non pour les interpréter | ancres `#_n` ; PDF à empreinte md5 |
| imedia Communes | HTML Joomla | Objets complets (4 communes) | non : arborescence et rédaction propres à chaque commune | articles Joomla ; PDF sous `/images/` (souvent interdit) |
| OIOI web | HTML | Séances et préavis | non : texte libre | slugs de page ; PDF horodatés |
| Webcommunes | HTML TYPO3 | Objets complets | oui : même arborescence et mêmes chemins de PDF | chemins `/fileadmin/…` parlants |
| Hekl@ | HTML | Séances seules (PV) | 3 communes : sans intérêt | — |

## Plateformes une à une

Pour chaque plateforme : l'échantillon lu à la main (2 ou 3 communes de tailles et de conseils différents), puis ce
qu'en dit le balayage de toutes ses communes. « PV » : procès-verbal ; « OdJ » : ordre du jour.

### i-web (Innovative Web AG) — 29 communes, 76 573 habitants

Échantillon : Blonay - Saint-Légier (12 464 hab., conseil communal), Préverenges (5 260, communal), Allaman (430,
général), Lovatens (146, général).

- **Forme.** Le HTML est rendu côté serveur, mais les listes ne sont pas des balises : chaque tableau porte ses
  lignes en JSON dans un attribut `data-entities` (`<table id="icmsTablePastSitzungen" data-entities="{…}">`). C'est
  la voie d'accès la plus propre de toutes les plateformes : un `json.loads` par tableau, sans analyse de mise en
  page. Les identifiants sont stables et typés : `/_rte/anlass/<id>` (séance, redirigée vers `/seances/<id>` ou
  `/sitzung/<id>`), `/_rte/information/<id>` (Objet), `/_rte/publikation/<id>` (recueil de documents),
  `/_doc/<id>` (fichier, redirigé vers `/_docn/<id>/<nom d'origine>.pdf`). Chaque séance offre aussi une archive Zip
  de ses documents (`/seances/zip/<id>`), qu'il n'y a pas lieu d'utiliser.
- **Trois usages du même produit.** i-web vend un module « Séances » (`Sitzungen`) et un module « Objets politiques »
  (`Geschäfte`) ; les communes les activent ou non.
  - *Module Objets* (Blonay - Saint-Légier) : 299 Objets de 2023 à 2026 (Communication 135, Préavis 102,
    Interpellation 49, Postulat 8, Motion 3, Pétition 2), chacun avec numéro (`2026-PM-23`, `2026-IN-17`), catégorie,
    date, et une fiche qui donne statut, auteur·e·s avec leur rôle, autorité et documents. Les points de l'OdJ de
    chaque séance renvoient aux Objets. Mais le **statut n'est pas tenu** : un préavis voté, avec son extrait de
    décision en ligne, est encore « Déposé ».
  - *Module Séances seul* (Préverenges, Allaman) : 81 séances passées depuis 2015 à Préverenges, 66 depuis 2011 à
    Allaman, chacune avec ses documents (OdJ, préavis, décision, PV, interpellation) ; l'OdJ est parfois en texte
    dans la description de la séance (Allaman). Les préavis forment une liste de documents (116 à Préverenges depuis
    2016, « Préavis municipal 2016 - 02/16 - titre » ; un recueil par année à Allaman).
  - *Pages simples* (Lovatens) : seules les séances à venir restent en ligne ; les PV sont des fichiers dans un
    recueil (« PV 2 décembre 2025 »).
- **Fraîcheur.** Séances à venir annoncées jusqu'en juin 2027 ; derniers documents de septembre-octobre 2026.
- **Particuliers.** Aucun nom de particulier vu dans les titres de l'échantillon ; une pétition cite un n° CAMAC et
  une adresse de parcelle. Les interpellations nomment leurs auteur·e·s élu·e·s.

**Balayage (29 communes).** Le module Séances est en service dans au moins 19 communes (tableau
`icmsTablePastSitzungen` non vide, jusqu'à 144 séances passées à Villeneuve et Château-d'Oex), le module Objets dans
une seule. Les préavis sont le plus souvent des **recueils annuels** (`/_rte/publikation/<id>`, « Préavis 2023 »)
qu'il faut ouvrir un par un : le balayage ne les a pas ouverts, d'où 3 communes classées « préavis seuls »
(Sainte-Croix, Dully, Lussery-Villars) dont les PV sont sans doute dans des recueils du même genre (vérifié à
Sainte-Croix seulement, qui a une page « Procès-verbaux »). Résultat : 1 Objets
complets, 15 Séances et préavis, 10 Séances seules, 3 préavis seuls. Première séance en ligne : médiane 2020, la
plus ancienne en 2009 (Le Lieu) ; 22 communes sur 24 datées ont une séance ou un document depuis septembre 2026.

### Quicksite (eAdmin Solutions) — 38 communes, 87 806 habitants

Échantillon : Aigle (11 752, communal), Founex (3 763, communal), Ropraz (530, général). En plus : Montreux et Vevey,
qui utilisent le module « Conseil communal » de Quicksite sur un site à part (voir les villes).

- **Deux générations.**
  - *Ancienne* (thème « Powered by quicksite v 5.5.3 », Aigle) : une bibliothèque de documents rendue côté serveur
    (`/documents`, 20 par page, `?Page_0=<n>`), filtrable par type : Préavis 183, Annexes 117, Ordre du jour 70,
    Décision 178, PV 72, Rapport de commission 212, Motion / Postulat / Interpellation 136, depuis 2015-2017 (50
    pages, un millier de documents). Chaque document a un titre, un type, un numéro d'Objet (`2026-12`,
    `i-2017-01` pour une interpellation), une description et la date de mise en ligne à la seconde. Les dates des
    séances à venir sont une page de texte libre.
  - *Nouvelle* (thème eAdmin de 2023, Founex, Ropraz) : la page est vide ; la liste est chargée par le navigateur
    depuis `/coreapi/elasticsearch/projects/<projet>/<vue>/search?…`, qui rend un **fragment HTML** paginé
    (`&page=<n>`, taille de page réglable). Les paramètres sont les attributs `data-elasticsearch-*` de la page. À
    Founex (vue `documentconseildates`) : 396 documents **groupés par Séance** (« Séance du 28 septembre 2026 » : OdJ,
    PV, préavis « Objet n° 001: titre », postulat, réponse, avis au pilier public, décisions), depuis 2016. À Ropraz
    (vue `documentconseil`) : 94 documents filtrés en Décisions 46, Préavis 24, PV 23, depuis 2017 ; pas d'OdJ, et
    les préavis sont datés d'une fausse séance (« Séance du 1 janvier 2025 »).
- **Fichiers.** `/qsPortal/Home.asp?N=<id>&DocAction=Download` (ancienne) ou `/n<id>` (nouvelle), identifiants de
  nœud stables ; le nom d'origine est dans `Content-Disposition`
  (`19.10.2026_11_22_19_Ordre_du_jour_seance_n_3_du_jeudi_29_octobre_2026.pdf`).
- **Fraîcheur.** Aigle : documents mis en ligne le 19 octobre 2026, la veille de la mesure ; Founex : séance du
  28 septembre 2026 ; Ropraz : dernier document d'avril 2026.
- **Particuliers.** À Founex, le titre d'un préavis de la nouvelle législature donne le prénom et le nom complet
  d'une particulière (succession répudiée), avec civilité. À Aigle, les interpellations nomment leur auteur·e élu·e
  par l'initiale et le nom.
- **Mentions légales.** Liens « trad(Impressum) » et « trad(Mentions légales) » vides (`#`) dans le gabarit 2023 ;
  « All rights reserved » dans l'ancien.

**Balayage (38 communes).** La nouvelle génération et sa recherche `coreapi` ont été rencontrées dans 26 communes
(32 requêtes `coreapi`), la bibliothèque de l'ancienne génération à Aigle, et le **module Conseil** à Ollon
(`/conseilcommunal/public/documents/recherche/` : 567 documents typés — préavis `2026/15`, interpellations, motions,
postulats, PV, rapports — datés à la séance du 8 octobre 2026). Résultat : 2 Objets complets (Aigle, Ollon),
25 Séances et préavis, 8 Séances seules, 1 préavis seuls, 2 rien (Gryon, sans page du conseil trouvée ; Perroy,
dont la liste n'a pas été chargée). Bex publie interpellations, motions et postulats sur une page séparée, mais sa
liste de préavis est chargée autrement et n'a pas été lue. Première séance en ligne : médiane 2021, la plus ancienne
en 2005 (Duillier) ; 23 communes sur 35 datées ont un document depuis septembre 2026.

### WebForge — 21 communes, 20 538 habitants

Échantillon : Jorat-Mézières (3 189, communal), Penthaz (1 945, communal), Bournens (531, général).

- **Forme.** Pages éditoriales rédigées par la commune, sans module de séances : titres (`Séance du 6 octobre 2026`),
  puis des liens « Télécharger (pdf 348 ko) » ou « LIRE ». Le titre du document est le texte qui précède le lien.
  Les PDF sont sous `/files/<horodatage unix>-<nom d'origine>-<id>.pdf`, nom en général parlant
  (`jm_10_2026_autorisations_generales_2026_2031`), horodatage = date de dépôt.
- **Markdown.** Chaque page a sa version `.md` (`<link rel='alternate' … title='Markdown'>`) : titres et texte, mais
  **sans les liens vers les PDF** (vérifié à Jorat-Mézières). Elle sert pour une sonde ou pour lister les préavis,
  pas pour les documents.
- **Contenu.** Jorat-Mézières : séances 2025-2026 avec convocation, extrait du PV et « Préavis N°10/2026 : titre »
  (fautes de saisie : `12/206`) ; « 2016 à 2024 : documents archivés ». Penthaz : prochaines dates en texte, OdJ,
  résumés et PV ; page des préavis avec 311 liens depuis novembre 2021 (« Préavis n° 08-2026 – titre » et rapports de
  commission). Bournens : 5 préavis 2025 et 17 PV depuis 2021 (« PV 16-12-2021 »).
- **Fraîcheur.** OdJ et PV de la séance du 6 octobre 2026 en ligne à Penthaz et Jorat-Mézières.

**Balayage (21 communes).** 10 Séances et préavis, 5 Séances seules, 6 rien : petites communes (Ferreyres, Rivaz,
Suscévaz, Bavois, Montpreveyres, Eclépens) dont la page du conseil n'a pas été trouvée par le recensement ou ne
donne que la composition. Gimel ajoute une page par législature avec les PV et préavis de 2012-2013 : l'archive,
quand elle existe, est une page par période. 8 communes sur 16 datées ont un document depuis septembre 2026.

### COMMUNEapp WEB (Commune Agence) — 18 communes, 15 907 habitants

Échantillon : Cugy (2 787, communal), Borex (1 146, communal), Vulliens (628, général).

- **Forme.** Une seule grande page par rubrique (180 à 370 ko, `/Vie-politique-et-reglements`, sections en ancres
  `#_n`), qui contient tout : membres, dates des séances, PV, préavis, règlements, décisions municipales. PDF sous
  `/assets/idm_medias/<empreinte md5>.pdf` : **nom de fichier non parlant**, le titre n'est que dans le texte du lien.
  Quelques PDF sont servis par le domaine de l'éditeur (`communeapp.ch`).
- **Contenu.** Cugy : dates 2026 en texte, ~25 PV depuis 2022 (« Procès-verbal séance du Conseil communal du
  25 juin 2026 », pas tous dans l'ordre), préavis « n°1-2026 titre » depuis 2021 (226 PDF sur la page). Borex :
  convocations, PV, « Préavis 01-2026 » et « Préavis 01-2026_Décision CC » (140 PDF). Vulliens : 392 PDF dont les
  décisions municipales mensuelles, « Ordre du jour CG du 11 juin 2026 », « 2026-04 titre » depuis 2024.
- **Fraîcheur.** Convocation d'octobre 2026 à Borex, OdJ du 1er octobre 2026 à Vulliens.
- **Conditions.** Lien « Consultez nos conditions d'utilisation » vers une page `/lpd` (protection des données).

**Balayage (18 communes).** Une requête suffit par commune (tout est sur la page de la rubrique). 12 Séances et
préavis, 3 Séances seules, 1 préavis seuls, 2 rien (Valeyres-sous-Rances, Bursins : page non trouvée). Plusieurs
petits conseils généraux publient pourtant leurs préavis (Vaux-sur-Morges, 185 habitants ; Tartegnin, 235). 9 sur
16 datées ont un document depuis septembre 2026.

### imedia Communes (imedia.ch, Joomla) — 14 communes, 65 266 habitants

Échantillon : Ecublens (13 364, communal), Echallens (6 719, communal), Chessel (527, général).

- **Forme.** Articles Joomla rédigés par la commune, arborescence propre à chacune (la « page du conseil » du
  recensement est un intitulé de menu, en 404, à Ecublens). Joomla offre un flux RSS sur toute liste d'articles
  (`?format=feed&type=rss`, vu sur les actualités et enquêtes d'Ecublens), qui ne couvre pas les documents.
- **`robots.txt`.** Le fichier d'origine de Joomla (avant la version 3) interdit `/images/`, **là où sont les PDF**
  (Chessel, Echallens) : le robot peut lire les listes et les liens, mais pas ouvrir un PDF pour en tirer des
  métadonnées. Ecublens a retouché le sien et permet `/images/`.
- **Contenu.** Ecublens : OdJ de chaque séance depuis 2007 (173 PDF, chemins parlants
  `/cc_des_2013/2026/20260619/ODJ_19_6_26.pdf`), dates à venir en texte, un article par année de préavis
  (2008-2026), groupés par séance (« Préavis 2026/19 - titre » et annexes), pages des réponses aux interpellations et
  des PV. Echallens : « Préavis municipaux, rapports des commissions, postulats et motions » (336 documents,
  « PM2026-08 concernant … », rapports), 26 PV depuis 2021. Chessel : 34 PV « 20.04.2026 - PV Conseil général »
  depuis 2016.
- **Fraîcheur.** OdJ de la séance du 19 novembre 2026 déjà en ligne à Ecublens.

**Balayage (14 communes).** 4 Objets complets (Echallens, Bussigny, Chavannes-près-Renens, Orbe : pages de
préavis, de motions et postulats, de PV), 6 Séances et préavis, 1 Séances seules, 3 rien (Assens, Curtilles,
Ballaigues). À Ballaigues, les liens de la page vers les PV 2021 répondent 404 ; à Bussigny, l'adresse de la page
du conseil relevée par le recensement était un avis du pilier public, lien d'actualité et non page stable. Archives profondes : séances
depuis 2006 à Orbe et Chavannes-près-Renens.

### OIOI web (OFISA Informatique) — 21 communes, 23 694 habitants

Échantillon : Vully-les-Lacs (3 627, communal), Rennaz (949, général), Bougy-Villars (514, général).

- **Forme.** Pages de texte libre (éditeur Froala) rendues côté serveur ; contrairement à ce que notait le
  recensement, le menu est bien dans le HTML. PDF sous `/uploads/<empreinte>/documents/<nom>_<horodatage>.pdf` ;
  noms souvent non parlants (`10_1791014650.pdf`), l'horodatage est la date de dépôt ; le texte du lien porte la
  date ou le numéro. Pas de `robots.txt` (l'application rend sa page 404).
- **Contenu.** Vully-les-Lacs : une page par année depuis 2016 (« Préavis et rapports 2026 ») : séance (date, lieu),
  OdJ, PV, puis « Point No 7 titre » avec préavis 2026/13, rapports et extrait des délibérations, postulats. Rennaz :
  dates à venir en texte (avec une « séance annulée faute d'objet »), PV par séance depuis 2021, préavis par
  législature (« Préavis 41 - Décision - titre », 102 liens). Bougy-Villars : archives en **un PDF compilé par
  année** (préavis, décisions, OdJ et PV ensemble, 2007-2024) — inexploitable sans lire le PDF.
- **Régularité.** Tout est saisi à la main : la structure de Vully-les-Lacs est très régulière, celle de Rennaz
  aussi, mais chacune à sa façon.

**Balayage (21 communes).** 8 Séances et préavis, 10 Séances seules (listes de PV datés), 2 préavis seuls, 1 rien
(Bougy-Villars, d'après l'échantillon). Séances depuis 2006 à Chéserex, 2013 à Arzier-Le Muids. 14 communes sur 20
datées ont un document depuis septembre 2026.

### Webcommunes (WNG, TYPO3) — 5 communes, 15 660 habitants

Échantillon : Aubonne (3 856, communal), Saint-Sulpice (5 155, communal), Cuarny (241, général).

- **Forme.** Même arborescence partout (`/officiel/conseil-communal/` puis agenda, préavis et rapports, motions et
  postulats, PV, décisions, archives) et PDF sous `/fileadmin/documents/<domaine>/pdf/…` avec des **chemins
  parlants** (`OJ_2026/OJ_2026.01.27.pdf`, `Préavis_2026/Séance_du_27.01.2026/…`).
- **Contenu.** Aubonne : agenda par législature avec les dates à venir, OdJ et PV (148 PDF) ; préavis « n° 1/26
  relatif à …, déposé le 27 janvier 2026 », rapports et extrait de PV (351 PDF) ; motions et postulats depuis 2019.
  Saint-Sulpice : 72 PDF de motions, postulats, interpellations et résolutions, « Motion de M. X et consorts », statut
  parfois en texte (« Retirée par … »). Cuarny : archives par séance (« Séance du 15.06.26 » : OdJ, PV décisionnel,
  « Préavis n°1/2026: titre »), 53 PDF depuis 2024.
- **Voisins.** WNG fait aussi le site TYPO3 de Montreux, Prilly, Le Mont-sur-Lausanne et Yverdon ; Gland est sur le
  même /24 (`94.103.98.0/24`).

**Balayage (5 communes).** 2 Objets complets (Aubonne, Saint-Sulpice), 2 Séances et préavis (Forel, Cuarny),
1 Séances seules (Romanel-sur-Lausanne). Forel tient aussi une page par séance
(`/seances-2025/3-avril-2025`).

### Hekl@ (Designis) — 3 communes, 2 968 habitants

Jorat-Menthue (1 574, communal) : prochaine séance (date) et les 10 derniers PV (« 08.12.2025 PV séance », depuis
2023), PDF `/admin/resources/Default/2025-12-08pv-adopte.pdf` aux noms irréguliers. Bremblens (614, général) :
seulement la date de la prochaine séance. Montagny-près-Yverdon (780, communal) : PV et préavis (balayage).
`Crawl-delay: 10` partout.

## Villes sur mesure

Les sept villes demandées et deux autres conseils communaux parmi les plus peuplés (La Tour-de-Peilz, Prilly),
soit **168 785 habitants**. Toutes publient davantage que les petites communes : huit sur neuf atteignent le niveau
« Objets complets ». Mais chacune est un scraper à part, sauf deux paires : Montreux et Vevey (module Conseil de
Quicksite), Nyon et Renens (même développement Nuxt d'iomedia, qui fait aussi Morges en Symfony).

| Ville | Habitants | Technique | Séances | Objets | Archive | Niveau |
|---|---:|---|---|---|---|---|
| Montreux | 26 955 | module « Conseil communal » de Quicksite, site à part `conseilmontreux.ch` | page par séance (`?ID=4312`), points d'OdJ avec leurs documents (OdJ, PV provisoire, préavis, rapports) | fiche par Objet (`documents/recherche/?id=3403`) : titre, auteur (Municipalité ou élu·e), documents typés et datés ; pas de statut | séances depuis 2006 | Objets complets |
| Nyon | 23 351 | Nuxt (iomedia), Crawl-delay 10 | état (planifiée, prochaine, tenue), OdJ, liste des commissions, PV, vidéo YouTube | par séance : « Préavis N° 2026-12 », rapports-préavis, interpellations, extraits de décision ; fiche avec date de dépôt | années 2008-2026 au sélecteur | Objets complets |
| Renens | 21 541 | Nuxt (iomedia), Crawl-delay 10 ; menu chargé en JavaScript | date, heure, lieu, OdJ, PV, vidéo | rapports de commission « 92-2025 » et réponses aux interpellations, avec **statut** (Accepté, Accepté avec amendement, Répondu) | 50 séances 2020-2026, 1 060 documents au sitemap | Objets complets |
| Vevey | 20 142 | Drupal + module Conseil de Quicksite sur `conseil.vevey.ch` | date, lieu, OdJ (points numérotés), PV, vidéo | bibliothèque filtrable par type (14 types) et par auteur·e ; codes d'Objet `2026/P12`, `2026/RP18` | — | Objets complets |
| Pully | 19 538 | Umbraco, **une seule page de 3 Mo** | « Ordre du jour et procès-verbal » par séance | 685 blocs de texte, 1 364 PDF : préavis, interpellations, postulats, motions numérotés (`N° 05-2026`), auteur·e, statut en texte libre (« Déclarée irrecevable ») | 2018-2026 | Objets complets |
| Morges | 17 701 | Symfony (iomedia), Crawl-delay 10 | page des dates de séance | 8 listes par type et par année (préavis, motions, postulats, interpellations, questions, communications, décisions, rapports de gestion) : date, « N° 22/10.26 », titre, PDF | 2004-2026 | Objets complets |
| Gland | 13 987 | TYPO3 | une page par séance, à venir comprises : OdJ, PV, communications, préavis, rapports, extraits de PV | page des motions, postulats et interpellations : auteur·e·s, **statut** (Traité, Refusé), réponse, rapport, décision | législatures 2021-2026 et 2026-2031 | Objets complets |
| La Tour-de-Peilz | 12 812 | PHP maison (Equateur) | pages OdJ, PV, décisions, agenda | préavis « Nr. 13 \| 2026 » (527 PDF), motions, postulats et interpellations avec auteur·e, parti et statut en texte (« Non soutenu par le Conseil », « Retiré ») | par année | Objets complets |
| Prilly | 12 758 | TYPO3 (WNG), Crawl-delay 10 | page par année : OdJ, préavis, rapports de commission | préavis seulement (`P_01_2026`) | page d'archives | Séances et préavis |

Remarques :

- **Le module Conseil de Quicksite** (« Vision Citoyenne ») sert Montreux, Vevey et au moins une commune Quicksite
  (Ollon, `/conseilcommunal/public/`, vu au balayage). Ses URL sont stables (`ordredujour/?ID=`,
  `documents/recherche/?id=`, `download.asp?d=`) : un seul scraper pour les trois.
- **Vevey** : le `robots.txt` de `conseil.vevey.ch` interdit tout sauf `/ConseilCommunal/seances/` et
  `/conseilcommunal/download.asp`, **sensible à la casse** ; le site principal lie parfois des OdJ par des URL
  cassées (`www.vevey.ch/conseil.vevey.ch/…`). Les pages du module sont en ISO-8859-1.
- **Renens** et **Nyon** interdisent dans leur `robots.txt` une centaine de robots nommés, dont tous ceux d'IA (y
  compris ceux d'Anthropic) ; notre User-Agent n'y est pas, mais c'est un signal : ces villes ne veulent pas de
  moissonnage indiscriminé. Renens n'expose son menu qu'en JavaScript : l'entrée est le `sitemap.xml` (trois
  fichiers, 1 883 URL dont 1 121 sous `/officielle/autorites/`).
- **Pully** tient tout le conseil sur une page : une seule requête suffit, mais un changement de gabarit casse tout.
  Les blocs Umbraco (`widgetText` puis `widgetDocument`) donnent la structure.
- Noms d'élu·e·s dans les noms de fichiers (Montreux, Vevey, Gland, Morges) et, à Prilly, courriels personnels des
  élu·e·s en clair sur la page du conseil.

## Noms de particuliers

Repérage automatique sur toutes les pages en cache (commande `particuliers` du script) : une civilité suivie de
mots à majuscule, hors contexte d'élu·e (« conseiller », « consorts », « interpellation », « Rapp. »…) dans les 80
caractères qui précèdent ; les noms ne sont ni écrits ni gardés. 73 mentions sur 27 sites, relues à la main :

- **Dans le titre d'un Objet ou d'un de ses documents : 8 particuliers, dans 4 communes.** Le prénom et le nom
  complet d'une particulière, avec civilité, dans le titre d'un préavis sur une succession répudiée (Founex) ; une
  personnalité à qui un préavis propose la bourgeoisie d'honneur (La Tour-de-Peilz) ; à Valbroye, l'auteure d'un
  legs, un opposant (« levée de l'opposition de M. X », avec le nom de son avocate) et l'acheteur d'une parcelle
  dans des titres de préavis ; à Saint-Sulpice, trois opposants à un plan dans les titres des annexes d'un préavis
  (« Opposition et son retrait de M. X »). Ce sont les préavis d'**aménagement, de vente et de succession** qui
  nomment des particuliers, pas les pétitions : aucun pétitionnaire nommé dans les titres de pétitions lus
  (Blonay - Saint-Légier, Pully) ; une pétition y cite un n° CAMAC et l'adresse de la parcelle.
- **Dans une description de séance : 1 cas** (un intervenant extérieur invité, Vevey).
- **Ailleurs, hors Objets** : le personnel communal avec son téléphone (pied de page des gabarits Quicksite), un
  avis de décès au pilier public (Bussigny), des auteurs de films d'archives (Begnins, Oron), et surtout des élu·e·s
  nommé·e·s sans marque d'élu·e (membres des bureaux et commissions, auteur·e·s de postulats dans la liste de
  Chavannes-près-Renens).

Ce qui compte pour le masquage, c'est surtout l'inverse : **les élu·e·s apparaissent souvent sans marque d'élu·e**
— « (Rapp. M. X) » dans les titres de préavis de Montreux, « Interpellation C. X » et « motion X » à Aigle, noms
dans les noms de fichiers (Montreux, Vevey, Gland, Morges, Saint-Sulpice), listes de membres sans fonction. Sans
liste d'élu·e·s connu·e·s, la règle « nom après une civilité » de l'ADR-0007 masquerait ces élu·e·s. Les sources
qui donnent cette liste : i-web (tableau `personList` des membres, auteur·e·s des Objets), le module Conseil de
Quicksite (page `conseillers`), Vevey (filtre par auteur·e), la plupart des pages « membres » ou « composition »
(en PDF ailleurs).

## PDF : couche texte

Au plus trois PDF par plateforme, choisis parmi les OdJ et les PV (`pdffonts` et `pdftotext` sur les trois
premières pages ; fichiers gardés hors du dépôt).

| Plateforme | Document | Producteur | Polices | Caractères (3 p.) |
|---|---|---|---:|---:|
| Quicksite | OdJ d'Aigle, octobre 2026 | Quicksite via ABCpdf | 4 | 920 |
| Quicksite | PV de Ropraz, 2017 | Word (Mac) | 5 | 14 468 |
| i-web | OdJ de Blonay - Saint-Légier, septembre 2026 | Word 365 | 7 | 1 242 |
| OIOI web | PV de Rennaz, juin 2026 | **scanner Canon**, avec OCR | 13 | 6 929 |
| WebForge | PV de Penthaz, juin 2026 | Word 365 | 8 | 6 238 |
| COMMUNEapp WEB | PV de Borex, juin 2026 | macOS (Quartz) | 12 | 9 393 |
| imedia | OdJ d'Ecublens, juin 2026 | Word 365 | 6 | 2 788 |
| imedia | OdJ d'Ecublens, novembre 2007 | Ghostscript | 4 | 2 532 |
| Webcommunes | PV d'Aubonne, janvier 2026 | Microsoft Print to PDF | 3 | 5 444 |
| Webcommunes | extrait de PV de Cuarny, juin 2026 | **scanner ScanSnap**, sans OCR | 0 | **0** |
| Hekl@ | PV de Jorat-Menthue, décembre 2025 | Word 2007 | 5 | 9 963 |
| sur mesure (Gland) | PV « signé » d'août 2026 | Word 365 | 11 | 10 390 |

Onze sur douze ont une couche texte, y compris un OdJ de 2007 et un PV dit « signé » (Gland, exporté de Word). Le
scanner sert aux pièces signées à la main : un extrait de PV décisionnel (Cuarny) n'a aucun texte, un PV scanné
(Rennaz) a été reconnu par le copieur.

## Ce que ça change pour la carte

Faits utiles aux décisions à venir de #117, sans les prendre.

1. **Plateformes à retenir d'abord, chiffres à l'appui.** Quatre scrapers génériques — i-web (JSON
   `data-entities`), Quicksite (bibliothèque, `coreapi`, module Conseil), Webcommunes, COMMUNEapp — couvrent
   90 communes et 195 946 habitants ; 81 d'entre elles (183 511 habitants) donnent au moins leurs Séances, 59
   (145 137) Séances et préavis. Le module Conseil de Quicksite ajoute Montreux et Vevey (47 097 habitants) au même
   scraper. Viennent ensuite les villes une à une (Nyon et Renens partagent le développement d'iomedia), puis
   WebForge, OIOI web et imedia, qui demandent des règles par commune. Un objectif chiffré réaliste pour un premier
   jalon : **Séances pour ~80 communes et ~230 000 habitants** (quatre plateformes et le module Conseil), en plus de
   Lausanne et Yverdon.
2. **IA pour les PDF : pas nécessaire aux métadonnées.** Numéros, titres, types et dates sont dans le HTML ou le
   nom de fichier partout où un scraper a du sens ; 11 PDF sur 12 ont une couche texte. Ce qui manque, ce sont les
   **statuts** (adopté, refusé, retiré) et, hors i-web et module Conseil, les **auteur·e·s** : ils sont dans le
   texte des extraits de décision et des PV. C'est là, et pour les communes en texte libre (OIOI web, WebForge),
   qu'une lecture « intelligente » apporterait quelque chose (ADR-0003 : plus tard, au cron). Les recueils annuels
   compilés (Bougy-Villars) resteraient hors de portée sans elle.
3. **Masquage des particuliers.** Peu de particuliers dans les titres, mais là où ils sont, ce sont des préavis
   d'aménagement, de vente, de legs ou de succession, et des annexes nommées « Opposition de M. X ». La règle
   « civilité + nom » les attrape ; le risque est l'inverse : masquer des élu·e·s nommé·e·s sans marque. Il faut,
   par conseil, une **liste d'élu·e·s connu·e·s** tirée de la page des membres (structurée chez i-web et dans le
   module Conseil, en PDF ailleurs) avant d'importer les titres. Les noms de fichiers (titres de documents selon
   l'ADR-0007) contiennent souvent le nom de l'élu·e auteur·e.
4. **Rattrapage historique : faisable d'un coup, à petit débit.** Archives en ligne depuis 2004-2011 dans les
   villes et les bonnes communes (Montreux 2006, Morges 2004, Ecublens 2007, Blonay - Saint-Légier 2011), médiane
   2020-2021 ailleurs ; WebForge ne garde souvent que la législature en cours. Le volume est faible : quelques
   pages par commune pour i-web (tout est dans un tableau), 50 pages pour la bibliothèque d'Aigle, une page par
   séance pour Montreux (~200 séances). À 5 s par plateforme, un rattrapage complet des quatre plateformes tient en
   une ou deux heures de cron.
5. **Pannes et sondes.** La sonde naturelle d'une commune est sa page d'entrée et un marqueur propre à la
   plateforme : présence de `icmsTablePastSitzungen` (i-web), « N éléments trouvés » dans la réponse `coreapi`
   (Quicksite), page `.md` (WebForge). Pannes déjà visibles : page du conseil en 404 (Ecublens, l'adresse du
   recensement était un intitulé de menu), liens morts (Ballaigues), lien d'actualité pris pour la page du conseil
   (Bussigny), OdJ liés par des URL cassées (Vevey), dates de séance fictives (« 1er janvier 2025 » à Ropraz),
   statut figé (i-web). Une liste vide n'est pas toujours une panne : Lovatens n'affiche que les séances à venir.
   Les **fusions du 1er janvier 2027** (10 communes du recensement) changeront ces sites.
6. **Registre des communes.** Il faut, par commune : la plateforme corrigée, la variante (i-web : module Séances,
   module Objets ou pages ; Quicksite : ancienne, nouvelle, module Conseil), les URL d'entrée (séances, préavis,
   objets, membres — pas seulement « la page du conseil »), le projet `coreapi` et ses paramètres, le `Crawl-delay`,
   les particularités de `robots.txt` (`/images/` interdit chez imedia, casse à Vevey) et l'encodage (ISO-8859-1 du
   module Conseil). Le recensement (#118) n'en donne qu'une partie, et sa colonne `page_conseil` est fausse pour
   quelques communes.
7. **Politesse.** Le débit se règle par plateforme et par /24, et les plateformes se recoupent : Quicksite et le
   site du conseil de Montreux sont sur le même /24 (`185.54.6.0/24`) ; Webcommunes, Gland, Montreux (TYPO3) et Le
   Mont sur `94.103.98.0/24` ; i-web et OIOI web à traiter ensemble. `Crawl-delay: 10` à Nyon, Renens, Morges,
   Prilly, sur Hekl@ et Infomaniak. Nyon et Renens bannissent nommément les robots d'IA, et 6 des 9 mentions légales
   lues soumettent toute reproduction à autorisation (Nyon vise expressément le stockage
   « dans un système de recherche et d'extraction de données »). ADR-0006 ne garde que des métadonnées et un lien,
   et les procès-verbaux, rapports et actes officiels ne sont pas protégés par le droit d'auteur (LDA, art. 5) ;
   écrire tout de même à Nyon et Renens avant de les scraper serait prudent. Ce balayage : 750 requêtes, aucun
   blocage.
8. **Tests sur pages HTML enregistrées (ADR-0010).** Les pages sont lourdes : 340 ko pour une page i-web (menu
   compris), 0,8 à 1,5 Mo pour Nyon et Renens (état Nuxt embarqué), 3 Mo pour la page unique de Pully. Il faudra
   des pages enregistrées allégées ou compressées. Cas à couvrir : JSON échappé dans un attribut (i-web, avec
   `é`), fragment `coreapi`, ISO-8859-1, en-têtes `content-encoding` en minuscules (déjà vu au recensement),
   dates en toutes lettres, en `dd.mm.yy` et dans les noms de fichiers, fautes de saisie (`12/206`), séances
   annulées, PDF enveloppés dans une visionneuse (`viewer.php?file=` à La Tour-de-Peilz).

## Méthode

1. **Robot.** `publications-conseils.py`, bibliothèque standard de Python : User-Agent du recensement
   (`VigieVaud-recherche/0.1 (+https://github.com/Louni-M/vigie-vaud)`), une requête à la fois (verrou de fichier),
   au moins 5 s entre deux requêtes vers le même /24 **et** vers la même plateforme (i-web et OIOI web comptés
   ensemble), `Crawl-delay` respecté s'il est plus grand, `robots.txt` lu d'abord sur chaque hôte, redirections
   suivies à la main avec les mêmes contrôles, pause forcée de 30 min sur 403, 429, 503, refus de connexion ou délai
   dépassé, cache de toutes les réponses hors du dépôt, plafonds de 30 pages par commune et de 3 PDF par plateforme
   (hors commande `pdf`, une réponse PDF n'est pas téléchargée). Mesure du 20 octobre 2026, de 20 h à 21 h 20 UTC :
   **750 requêtes** (dont 160 `robots.txt`, 160 hôtes), aucune pause de blocage, au plus 11 pages pour une commune,
   12 PDF.
2. **Échantillon.** 25 communes des plateformes (dont Ollon, lue après le balayage) et 9 villes lues à la main : page du conseil, sous-pages des
   séances, préavis et Objets, une séance et un Objet types, dernière et première page d'archive.
3. **Balayage.** Pour les 149 communes des huit plateformes (plateforme corrigée), trois passes :
   `balayage-1` (la page du conseil du recensement, sinon l'accueil), `balayage-2` (jusqu'à 4 sous-pages du même
   site dont le lien parle de séances, préavis, PV, Objets ou documents du conseil, plus 2 choisies par l'adresse
   quand le lien dit seulement « Voir la liste »), `balayage-3` (la recherche `coreapi` des pages Quicksite de
   nouvelle génération). Puis `classer` compte, sur les pages en cache de chaque commune : dates de séance (dates
   proches d'un mot comme « séance », « PV », « ordre du jour »), numéros de préavis distincts, mentions de motions,
   postulats et interpellations, lignes des tableaux i-web, recueils i-web ; et en déduit le niveau (règles dans
   `niveau()`). Le niveau constaté à la main sur l'échantillon l'emporte (`ECHANTILLON`).
4. **PDF.** `pdffonts` et `pdftotext -l 3` (poppler) sur 12 PDF, gardés hors du dépôt.
5. **Particuliers.** `particuliers` : civilité suivie de noms hors contexte d'élu·e, noms remplacés par `[X]`
   avant affichage, relecture à la main ; rien de nominatif dans le dépôt.

Pour refaire la mesure (le cache reste hors du dépôt ; `--sites` pointe vers le CSV du recensement, sur la branche
`research/sites-communaux`) :

```
R="python3 -I docs/recherche/publications-conseils.py --cache /tmp/conseils --sites /chemin/sites-communaux.csv"
$R balayage-1 > p1.txt && $R lot p1.txt
$R balayage-2 > p2.txt && $R lot p2.txt
$R balayage-3 > p3.txt && $R lot p3.txt
$R classer > docs/recherche/publications-conseils.csv
$R particuliers > /tmp/particuliers.csv     # hors dépôt
```

Colonnes du CSV : `ofs`, `commune`, `habitants`, `conseil`, `plateforme` (corrigée, ou « sur mesure : … »),
`mesure` (échantillon ou balayage), `pages_lues`, `seances` (dates de séance distinctes), `preavis` (numéros
distincts), `autres_objets` (mentions de motions, postulats, interpellations…), `iweb_seances` et `iweb_objets`
(lignes des tableaux i-web), `recueils_preavis` et `recueils_pv` (recueils i-web), `depuis` (année de la plus
ancienne séance vue), `derniere_seance` (plus récente, jusqu'au jour de la mesure), `niveau_auto`, `niveau`
(retenu), `note`.

## Limites

- **Le niveau est une estimation** pour les 124 communes balayées : quelques pages par commune, des expressions
  régulières, pas de lecture humaine. Il sous-estime quand l'information est un niveau plus bas (recueils annuels
  i-web, listes chargées autrement chez Bex, page non trouvée par le recensement) et peut surestimer quand une page
  cite des préavis sans les publier. L'écart entre « Séances seules » et « Séances et préavis » est le moins sûr.
- **Statuts et auteur·e·s** n'ont été vérifiés que sur l'échantillon ; le balayage ne les compte pas.
- **Fraîcheur** : la date la plus récente vue n'est pas toujours celle d'une séance tenue (une date d'OdJ à venir
  est exclue, une date de mise en ligne peut passer).
- **Non mesuré** : Payerne, Lutry, Crissier, Epalinges et Le Mont-sur-Lausanne (conseils communaux de plus de
  9 500 habitants sur mesure, hors des 9 villes demandées) ; les 132 autres sites sur mesure (WordPress, Joomla…),
  hors du périmètre de cette question ; les PDF au-delà de 12 ; les flux RSS Joomla des pages du conseil (seulement
  vus sur les actualités d'Ecublens).
- **Mentions légales** : 9 pages lues (i-web, imedia, Nyon, WebForge, COMMUNEapp, Webcommunes, La Tour-de-Peilz,
  Morges, Chessel), pas toutes les plateformes ni toutes les communes ; rien d'un juriste.
- **Mesure datée** : les sites changent, surtout avec les fusions de 2027 ; le script refait la mesure.

## Sources

- Les sites des communes et leurs pages du conseil, lus le 20 octobre 2026 (liste et comptages dans le CSV), dont :
  i-web (`blonay-saint-legier.ch/seances`, `/objets-politiques`, `/_rte/information/<id>`), Quicksite
  (`aigle.ch/documents`, `founex.ch/coreapi/elasticsearch/projects/founex25/documentconseildates/search`,
  `ollon.ch/conseilcommunal/public/documents/recherche/`), `conseilmontreux.ch/conseilcommunal/public/ordredujour/`,
  `conseil.vevey.ch/ConseilCommunal/seances/`, `nyon.ch/nyon-officiel/autorites/conseil-communal/seances-1640`,
  `renens.ch/sitemap.xml`, `pully.ch/pully-officiel/conseil-communal/`, `morges.ch/preavis/2026`,
  `gland.ch/ma-ville/conseil-communal/motions-postulats-et-interpellations`.
- `robots.txt` de chaque hôte lu (160), en particulier ceux d'Echallens et Chessel (`Disallow: /images/`), de
  `conseil.vevey.ch` et de Renens.
- Mentions légales : Préverenges (`/_rtr/impressum`), Ecublens (`/informations-legales`), Nyon
  (`/mentions-legales-979`), Jorat-Mézières, Morges, La Tour-de-Peilz, Chessel.
- Script `sites-communaux.py` du recensement (#118), motif `i-web\.ch` de `PLATEFORMES`, pour la correction i-web /
  OIOI web.
- Loi fédérale sur le droit d'auteur (LDA, RS 231.1), art. 5 (œuvres non protégées : actes officiels, procès-verbaux
  et rapports des autorités).
- ADR-0003, ADR-0006, ADR-0007, ADR-0010 du dépôt ; `CONTEXT.md`.
