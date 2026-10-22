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
