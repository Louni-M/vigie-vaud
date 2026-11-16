# Règles de code

Les défauts qu'un changement doit éviter dans ce dépôt, et qu'une revue cherche dans chaque diff. Chaque règle vient d'un constat de revue corrigé, d'un commit de correction ou d'un nettoyage, et aucun contrôle de la CI (svelte-check, ESLint, ruff, tests, construction) ne la tient. Les commandes, l'installation et ce que la CI vérifie n'ont pas leur place ici.

## Commun au site et au pipeline

- **Une règle n'est écrite qu'à un endroit.** La construction d'une entité du domaine (Séance, Objet, document, restriction), un client de service, une règle de comptage, une liste d'états et leurs libellés ou une forme répétée (promesse gardée, test d'identifiant) vivent dans une seule fonction ou un seul module, que les autres appellent. Une copie qui recopie un client ou une règle voisine est un défaut, même quand elle se comporte pareil aujourd'hui. (#102 : `005b915`, `33968a8`, `c9b4af9`, `55ecd58`, `2eac3b8` ; PR #182 : `ca703b4`, `2abca82`, `4873577` ; `638b089`, `500374b`, `8177f26`, `2d5971a`)
- **Une règle que le site et le pipeline appliquent tous deux a ses cas dans `cas-partages/`.** Élision, niveaux, masquage, nom et clé d'un conseil : les deux suites de tests lisent la même table, pour que le site et le cron ne divergent pas en silence. Une règle partagée nouvelle y ajoute sa table. (`3fcfbd5`, `ce81a03`, `96fee0b`)
- **Le code parle le vocabulaire de `GLOSSARY.md`.** Noms, messages d'erreur, commentaires et noms de tests emploient le terme du glossaire, jamais un terme listé sous « À éviter » (par exemple « calque » pour une couche, « tracé » pour une restriction). Un concept absent du glossaire y est ajouté plutôt qu'inventé. (#102 : `e841650` ; #184 : `15e92ad`, `5f4aec9` ; PR #182 : `16a5dcf`)
- **Une règle de lecture ou de rangement nouvelle ou changée est écrite dans son ADR dans le même changement.** Quand un changement décide où va un document, quel numéro prend un préavis ou ce que coûte un retrait, l'ADR qui porte la règle (et `docs/retrait.md` ou `docs/sources.md` s'ils la décrivent) le dit dans le même commit. (PR #182 : `0c6e95c`, `2379b60` ; #184 : `5c91618` ; `e0188f5`, `cbadeca`)
- **L'état de référence des linters ne couvre pas de code nouveau.** Les constats gelés de `web/eslint.config.js` et de `pipeline/pyproject.toml` ne servent qu'au code d'avant leur ajout. Un fichier nouveau ou un constat nouveau se corrige, ou porte une exception motivée sur sa ligne. (#184 : `9986b91` ; `3a6b203`)

## Tests et portabilité

- **Les tests ne quittent pas la machine.** Git se teste contre un dépôt nu, les services par leurs faux, sans requête DNS ni appel réseau réel. (`774cb9a`)
- **Le code et les tests tournent aussi sous Windows.** Toute lecture ou écriture de texte et tout appel de sous-processus nomment l'encodage utf-8. Un chemin se compare sous sa forme à barres obliques. Un test ne dépend ni de la fin de ligne du système ni d'un délai serré. (`b94f92a`, `8b5b371`, `80ba7b6`, `fc29ada`, `436c615`, `2fa6fb1`)

## Pipeline

- **Une lecture ne perd rien en silence.** Une liste tronquée par un garde-fou, une page sautée, une recherche vide ou un document écarté se notent dans le journal du passage, avec ce qui manque. Quand rien ne se lit, l'import est en échec plutôt qu'un succès vide. Un document rangé au mauvais endroit reste pour toujours, puisque l'import garde les documents archivés. (PR #182 : `0c6e95c`, `16a5dcf`, `2379b60`)
- **Seul un échec attendu, levé exprès, garde la ligne courte d'un conseil en échec.** Une exception qui dit qu'un lecteur est cassé (validation, JSON ou décodage illisible, erreur imprévue) montre sa trace dans le journal. Attraper une famille d'exceptions entière pour la réduire à un message cache le défaut. (#184 : `7c7fb2f` ; `4cddfcc`)

## Site

- **Toute lecture d'une source se reflète dans l'état de cette source.** Pas seulement le chargement principal : un fil, un lien direct ou une nouvelle tentative qui échoue met la source en erreur (badge, « Réessayer »), et sa réussite suivante la rétablit. (#102 : `c76d083` ; `da1406b`)
- **Les textes suivent la typographie française.** Un texte venu d'une source passe par la typographie du site (`web/src/lib/almanach/typographie.ts`). Les chaînes du code portent leurs insécables (« 19 h 30 », « n° 12 », avant « : »), les nombres passent par le formateur fr-CH partagé et l'élision d'un nom de commune par celle du registre. (`aba2bef`, `61f9e36`, `1f9f34b`, `a130fa9`, `1268496`)
- **Ce qu'on peut partager est un lien et une adresse.** Une navigation est un `<a href>`, pour que Cmd/Ctrl-clic et le clic du milieu marchent. Le volet ouvert, l'onglet, la vue du téléphone et les filtres sont dans l'adresse, et précédent/suivant les rendent. (`1f9f34b`, `91ff6c2`)
- **Les transitions et animations ne touchent que `transform` et `opacity`** et respectent le mouvement réduit ; un changement de couleur, de fond ou de soulignement se fait d'un coup. (`91ff6c2`, `1f9f34b`)
- **Rien n'est seulement visuel.** Un glyphe décoratif (flèche, puce) est masqué aux lecteurs d'écran, avec un texte équivalent quand il porte un sens. Les titres gardent leur hiérarchie et chaque page ses repères. (`aba2bef`, `1f9f34b`, `a729f0f`)

## Tenir ce fichier

Un défaut entre ici seulement s'il est apparu dans un constat de revue que l'auteur a corrigé, dans un commit de correction, dans un nettoyage qui l'a retiré de tout le code ou dans une fiche de `docs/solutions/`, et si aucun contrôle ne le tient. Chaque règle décrit le défaut comme une condition, en quelques phrases qui restent vraies sans nombres ni symboles qui changent, sous le domaine qu'elle touche, avec ses sources. Une règle qu'un contrôle tient désormais, ou dont le code a disparu, est retirée.
