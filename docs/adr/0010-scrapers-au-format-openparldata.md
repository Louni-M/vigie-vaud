# Scrapers communaux au format OpenParlData

Les scrapers communaux, à partir de J3 Conseils communaux, produisent des séances et des objets au format des
*meetings* et *affairs* d'OpenParlData, plutôt qu'un format propre. On pourra ainsi les proposer à OpenParlData.

## Conséquences

- Chaque scraper est testé sur des pages HTML enregistrées.
- En production, un résultat vide ou un format inattendu ouvre une issue GitHub et passe la commune « en panne »
  sur la page Couverture.
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
