# La fiche commune a un chemin, le reste de l'état est en requête

Le site est statique (GitHub Pages) : seule une page pré-générée peut porter un titre, une description et un aperçu
propres, puisque les paramètres de requête ne sont lus que dans le navigateur. Chaque commune a donc pour adresse
`/commune/<slug>`, pré-générée, qui ouvre la carte avec sa fiche commune : un lien partagé affiche « Pully – Vigie
Vaud » et les moteurs peuvent indexer les 300 communes. Tout le reste de l'état (couches, vue, dossier ouvert, filtres)
reste en paramètres de requête, y compris `?d=` pour un dossier : ses données sont lues en direct, une page pré-générée
n'apporterait rien.

## Considered Options

- **Une page relais pré-générée qui redirige vers `/?commune=<slug>`** : l'aperçu fonctionne, mais l'adresse change
  sous les yeux de l'utilisateur et les moteurs indexent mal les pages qui redirigent.
- **`/?commune=<slug>` seulement** : plus simple, mais aucun aperçu par commune ni indexation.
