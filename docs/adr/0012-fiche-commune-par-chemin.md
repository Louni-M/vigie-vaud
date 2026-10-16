# Les fiches ont un chemin, le reste de l'état est en requête

Le site est statique (GitHub Pages) : seule une page pré-générée peut porter un titre, une description et un aperçu
propres, puisque les paramètres de requête ne sont lus que dans le navigateur. Chaque commune a donc pour adresse
`/commune/<slug>`, pré-générée, qui ouvre la carte avec sa fiche commune : un lien partagé affiche « Pully – Vigie
Vaud » et les moteurs peuvent indexer les 300 communes. Tout le reste de l'état (couches, vue, dossier ouvert, filtres)
reste en paramètres de requête, y compris `?d=` pour un dossier : ses données sont lues en direct, une page pré-générée
n'apporterait rien.

La fiche du Grand Conseil, la seule qui n'est pas celle d'une commune, suit la même règle (J1) : `/grand-conseil`,
pré-générée et dans le sitemap, et `/grand-conseil?c=vd/26_INT_140` pour un Objet ou une Séance ouverts. Le registre ne
la connaît pas par son nom : c'est la couche Conseils qui la déclare (chemin, nom, position), comme une couche déclare
ses entrées du fil. Un élément peut appartenir à plusieurs fiches (un Objet du Grand Conseil, à chaque commune qu'il
nomme et à la fiche du Grand Conseil) : il s'ouvre dans la fiche du chemin si elle en fait partie, sinon dans la
première.

## Considered Options

- **Une page relais pré-générée qui redirige vers `/?commune=<slug>`** : l'aperçu fonctionne, mais l'adresse change
  sous les yeux de l'utilisateur et les moteurs indexent mal les pages qui redirigent.
- **`/?commune=<slug>` seulement** : plus simple, mais aucun aperçu par commune ni indexation.
- **Le Grand Conseil codé en dur dans le registre** : une route et un cas particulier de moins à déclarer, mais le
  registre connaîtrait une couche par son nom, ce que le fil cantonal s'interdit aussi.
