# Un dépôt de données séparé, publié sur ses propres GitHub Pages

Le cron écrit son JSON dans un dépôt séparé, `vigie-vaud-donnees`, publié sur ses propres GitHub Pages et lu par
le site. L'historique git de ce dépôt sert d'archive, et le site n'a pas besoin d'être reconstruit à chaque passage
du cron.

## Conséquences

Ce JSON suit un schéma commun, dont on génère les types TypeScript du site.
