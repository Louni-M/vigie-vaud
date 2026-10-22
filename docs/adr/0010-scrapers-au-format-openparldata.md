# Scrapers communaux au format OpenParlData

Les scrapers communaux, à partir de J3 Conseils communaux, produisent des séances et des objets au format des
*meetings* et *affairs* d'OpenParlData, plutôt qu'un format propre. On pourra ainsi les proposer à OpenParlData.

## Conséquences

- Chaque scraper est testé sur des pages HTML enregistrées.
- Comme pour toute source, seules les sondes décident d'une panne. La sonde d'une commune scrapée lit sa page de
  liste et y cherche le marqueur de sa plateforme (`icmsTablePastSitzungen` chez i-web, la réponse `coreapi` chez
  Quicksite…). Elle passe une fois par jour, juste avant l'import, et non toutes les 30 minutes (3 840 requêtes
  par jour vers des sites communaux). Une sonde en échec est refaite au passage suivant, et l'import du jour
  attend qu'elle réussisse. Sont des pannes : une erreur HTTP, un délai dépassé, un marqueur absent (refonte du
  site), une page illisible. Une liste vide n'en est pas une (un conseil général entre deux séances, un site qui
  ne garde que les Séances à venir). Une liste dont aucune ligne ne se lit est un import en échec, un élément
  illisible est sauté et noté dans le journal, et une date fictive est importée telle quelle. Écartée : la panne
  au premier résultat vide ou inattendu du scraper, qui faisait deux règles et prenait chaque silence pour une
  panne.
- Les issues des communes scrapées (`panne-source`, `import-conseils`, et `a-verifier` pour un conseil sans
  nouvelle Séance, tenue ou annoncée, depuis 9 mois) s'ouvrent par plateforme : une seule issue par sorte, avec la
  liste des communes touchées, que le cron tient à jour. Elle s'ouvre avec la première commune touchée et se
  ferme au retour de la dernière. L'état reste mesuré commune par commune. Écartée : une issue par commune, car
  une refonte de plateforme en ouvrirait des dizaines d'un coup.
- Le rattrapage d'une commune scrapée (ADR-0008) prend tout ce que son site garde, sans plancher. À la différence
  de J1, le passage ordinaire ne lit jamais l'historique, même au premier import d'une commune : sur une
  trentaine de communes ajoutées d'un coup, il ne tiendrait pas dans un passage. L'historique arrive par un
  rattrapage ciblé, lancé à la main sur une plateforme ou une commune : à chaque étape de J3 avant sa mise en
  ligne, puis pour chaque commune ajoutée plus tard. Le rattrapage global, qui relit aussi OpenParlData, ne
  relance pas tous les sites communaux pour autant.
- Le passage ordinaire relit chaque jour les pages de liste en entier. Il ne rouvre les pages d'une Séance ou d'un
  Objet que pour ceux des 6 derniers mois et ceux à venir : un procès-verbal publié plus tard ne s'ajoute qu'au
  rattrapage suivant. Écartés : ne rouvrir que les nouveaux éléments (les procès-verbaux d'un conseil général qui
  siège quatre fois par an manqueraient tous) ; tout rouvrir chaque jour (environ 2 000 pages chez i-web).
- Un site qui ne garde que le présent (les seules Séances à venir) s'archive à partir du premier import ; le passé
  d'avant est perdu, et on ne va pas le chercher ailleurs (Wayback Machine, recueils en PDF). Une Séance qui
  disparaît du site reste dans le dépôt de données (ADR-0017) et ne vaut pas une panne.
- Le rattrapage suit la même règle de débit que le passage ordinaire.
- Les ancien·ne·s élu·e·s nommé·e·s dans les titres rattrapés, absent·e·s de la page des membres actuelle et
  jamais vu·e·s comme auteur·e·s, sont masqué·e·s après une civilité (ADR-0007) : c'est le prix d'un historique
  sans plancher.
- Les communes scrapées sont déclarées dans `sources.json`, une source par commune (`site-<n° OFS>`), comme toute
  source (ADR-0013) : il n'y a pas de registre à part. Chaque source donne sa plateforme, sa variante, sa page de liste
  des Séances (la page sondée), et selon le cas celles des Objets et des membres et les paramètres `coreapi` ; son
  niveau se déclare dans `conseil.donne` (Objets, préavis ou Séances seules), et non d'après ce que l'import trouve.
  Une section `plateformes` déclare une fois chaque plateforme, ses variantes, leur marqueur de sonde et les niveaux
  qu'elles permettent. Une commune non couverte d'une plateforme retenue a aussi sa source, sans conseil ni sonde,
  avec une raison prise dans une liste fermée (« préavis seuls », « rien en ligne », « à la demande de la commune »,
  « le site refuse les robots », « nouveau site pas encore lu »). Écartés : un fichier préparé à part, comme
  `hotels-de-ville.csv` (deux déclarations d'une même source) ; la découverte des pages par le cron (une erreur y
  publierait n'importe quelle page).
- Ces déclarations ne changent que par une PR dans le dépôt principal, jamais par le cron. Un script de `pipeline/`
  les prépare une fois en remesurant chaque site (plateforme réelle, variante, pages, plafond de requêtes), puis les
  revérifie à la demande sans les écrire ; le recensement du 20 octobre 2026 reste une mesure datée, non corrigée.
  Ce qui se lit au passage n'y est pas : le /24 (résolu à chaque passage), `robots.txt` et `Crawl-delay`, l'encodage.
  Seul le ralentissement d'un /24 à la main y figure. Ce qui reste à rattraper est un état : le dépôt de données garde
  la date du dernier rattrapage de chaque conseil.
- Les tests du dépôt principal vérifient, sans réseau, que chaque commune déclarée existe dans `communes.json` (une
  fusion qui l'efface fait échouer la PR qui met `communes.json` à jour), qu'un conseil n'a qu'une source, que chaque
  plateforme et variante citées sont déclarées et permettent le niveau déclaré, et qu'une commune non couverte a une
  raison et pas de conseil.
- Une étape de J3 ajoute les sources de sa plateforme dans sa PR, puis un rattrapage ciblé est lancé à la main ; une
  commune ajoutée plus tard suit le même chemin. Après une refonte, la commune reste en panne jusqu'à la PR qui la
  corrige : nouvelles pages, autre plateforme retenue, ou non couverte « nouveau site pas encore lu ».
- Les communes qui disparaissent au 1er janvier 2027 (Le Lieu sur i-web, Lucens sur Quicksite) ne sont pas
  scrapées ; les nouvelles communes entrent comme des communes ajoutées, une fois leur site en ligne et s'il tourne
  sur une plateforme retenue.
