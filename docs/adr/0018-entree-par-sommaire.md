# L'entrée du site est un sommaire, et la carte suit le sujet ouvert

Quand le site ne montrait que les permis de construire, un visiteur comprenait tout de suite ce qu'il voyait. Avec les
conseils communaux, le Grand Conseil et les routes, l'écran d'arrivée empilait tout : le fil cantonal ouvrait plus de
cent entrées du Grand Conseil et des Séances avant le premier permis, la carte affichait toutes les couches dès
l'arrivée, et des mots comme « Fil », « Couches », « Couverture » ou « Sans commune » ne disaient rien à qui ne
connaît pas le projet.

À l'arrivée, le panneau posé sur la carte montre donc un **sommaire** : une ligne par **rubrique**, avec son nom, une
phrase et son nombre d'éléments dans la zone affichée (le Grand Conseil, sans position, compte pour tout le canton).
Une rubrique est un sujet tel que le visiteur le nomme ; ce n'est pas une couche : chaque couche déclare les siennes,
avec leur rang au sommaire, et la couche Conseils en déclare deux, Conseils communaux et Grand Conseil. Le registre
les range et les compte sans en nommer aucune, comme il ne nomme aucune couche (ADR-0012). Un clic sur une ligne
ouvre la liste complète de la rubrique dans le panneau, avec un lien de retour au sommaire, ou, pour le Grand Conseil,
sa fiche. Une seule rubrique est ouverte à la fois. Le fil cantonal, qui mélangeait tous les sujets, est retiré du
site ; « plus récents d'abord » devient un tri des listes.

La carte dessine une seule couche à la fois, en plus des hôtels de ville et du marqueur du Grand Conseil, toujours
là : celle de l'onglet de la fiche commune ouverte, sinon celle de la rubrique ouverte, sinon aucune. Le grisage,
la légende et l'attribution de la carte suivent cette couche. L'interrupteur « Affichée » et la clé d'adresse
`couches=` disparaissent ; une ancienne adresse qui la porte s'ouvre sur le sommaire.

Les mots montrés au visiteur changent ; les termes du glossaire, du code et des adresses restent. `GLOSSARY.md` donne,
pour chaque terme visible, le mot montré au visiteur.

## Considered Options

- **Des onglets toujours visibles, un par sujet** : un clic de moins pour ouvrir un sujet, mais rien ne dit d'un coup
  d'œil ce que contient le site.
- **L'entrée par le lieu (« Que se passe-t-il près de chez vous ? »)** : parle au visiteur qui vient pour sa commune,
  mais cache l'étendue du site derrière une recherche ; gardée pour plus tard.
- **Le fil filtré sur le sujet ouvert** : garde le fil, mais un même élément aurait deux endroits, sa liste et le fil.
- **Une cinquième rubrique « Quoi de neuf »** : refait le fil mélangé sous un autre nom.
- **Garder l'interrupteur « Affichée » et `couches=`** : le visiteur choisirait ce que la carte montre, mais la carte
  ne montrerait plus ce qu'il est en train de lire.

## Conséquences

- Le panneau garde la clé d'adresse `volet=` : `volet=routes` ouvre la rubrique Routes, une valeur qui n'est pas celle
  d'une rubrique à volet (`volet=fil`, `volet=hotels-de-ville`, `volet=`) donne le sommaire. Sans `volet=`, un lien
  vers un élément ouvre sa rubrique ; un élément ouvert depuis le sommaire écrit `volet=sommaire`. Les liens déjà
  partagés restent valides.
- Le nombre d'une rubrique est celui de sa liste à l'ouverture : la même fonction de compte, avec les réglages par
  défaut de la couche et la zone de la carte. Une source en échec rend sa ligne « indisponible », jamais un nombre
  partiel.
- Une fiche commune ouverte fait dessiner à la carte la couche de son onglet courant, sans changer le panneau : un
  visiteur qui lit les permis de Morges les voit sur la carte, même si la rubrique Routes est ouverte à gauche.
- Sur téléphone, trois vues : le panneau (le sommaire ou la rubrique ouverte, la recherche en tête), la carte et la
  fiche. L'arrivée se fait sur le panneau, sauf quand l'adresse ouvre une fiche, un élément ou une vue de la carte ;
  `affichage=fil` et `affichage=couches` sont lus comme le panneau.
- Une couche nouvelle (trains, presse, incidents) s'ajoute comme une ligne du sommaire en déclarant sa rubrique, sans
  changer le reste de l'entrée.
- Le cron n'écrit plus `conseils/fil.json`. Son motif reste dans `MOTIFS_LECTURE` pour que le passage suivant retire
  l'ancien fichier du dépôt de données ; il pourra partir ensuite.
