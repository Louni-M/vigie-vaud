# Rattachement par le nom : contextes exclus et corrections

Remplace l'ADR-0009. Un élément d'une source qui porte sur le canton (le Grand Conseil, plus tard la presse et les
incidents) est rattaché aux communes dont le nom apparaît dans son texte, d'après `communes.json` : communes
actuelles, anciennes communes et anciens noms, qui mènent tous à la commune actuelle. Les Objets et les Séances d'un
conseil communal n'appartiennent qu'à leur commune, même quand ils en nomment d'autres. La recherche sur les Objets
du Grand Conseil (ticket #47) a montré que les erreurs ne viennent pas des noms ambigus de l'ADR-0009 mais du
contexte (« district de Nyon », « Université de Lausanne », « avenue de Provence », « en séance du Conseil d'État, à
Lausanne », « Article Premier ») : les exclusions portent donc sur des contextes, pas sur des noms.

Écartés : la page vd.ch d'un Objet du Grand Conseil (« Texte déposé »), qui nomme une commune dans 21 % des cas mais
demanderait de scraper vd.ch, une source et du code propres au Grand Conseil ; la transcription des débats, où
l'élu·e déclare souvent sa propre commune ; les formes courtes ambiguës (Chavannes, Belmont, Corcelles, Romanel,
Mont), qu'aucune règle ne peut départager.

## Conséquences

- Pour un Objet du Grand Conseil, on lit le titre, après le masquage de l'ADR-0007, et le texte de ses documents
  dans l'API, qui n'est pas conservé (ADR-0015). Le titre long n'apporte que des districts et n'est pas lu.
- Les exclusions sont des données communes à toutes les sources : formules retirées avant l'appariement, motifs
  avant ou après le nom (district, région, rue, route, institution, raison sociale, « du X », mot courant). Aucun
  nom de commune n'est banni, sauf l'ancienne commune Mur.
- « St- » et « Ste- » sont lus comme « Saint- » et « Sainte- » ; une courte liste de formes usuelles, tenue à la
  main, reconnaît les formes courtes sans ambiguïté (Cheseaux, Saint-Légier).
- Au-delà de 10 communes dans ses documents, un Objet n'est rattaché que par son titre : ce sont des énumérations.
- Le rattachement retient où la commune est nommée, dans le titre ou dans un document. Les communes du titre passent
  en tête, dans leur ordre ; celles des documents suivent, de la plus mentionnée à la moins mentionnée.
- Un fichier de corrections du dépôt de données retire ou ajoute une commune à un élément ; le cron l'applique à
  chaque import. Une correction récurrente devient un contexte exclu.
- Le dépôt garde la commune actuelle. Une fusion, comme un changement de règle, se recalcule en relançant le
  rattrapage.
