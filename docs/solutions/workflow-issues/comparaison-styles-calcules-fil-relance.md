---
title: La comparaison des styles calculés voit un faux écart dans le Fil des fiches d'Objet et de Séance
date: 2026-11-16
category: workflow-issues
module: web (preuve « aucun changement visible » des PR de CSS)
problem_type: workflow_issue
component: testing_framework
severity: medium
applies_when:
  - Prouver qu'un changement de CSS ne change rien, par la comparaison des styles calculés avant / après décidée dans #210
  - Un état relevé ouvre une fiche sans `vue=` dans l'adresse, avec le Fil ouvert à côté
tags: [css, styles-calcules, preuve-visuelle, fil, playwright, comparaison]
---

# La comparaison des styles calculés voit un faux écart dans le Fil des fiches d'Objet et de Séance

## Context

La décision de #210 (point 4) demande, pour une PR de CSS, de comparer les styles calculés de chaque élément avant et après, à 1024 et à 375 px, sur une liste d'états. #210 (PR #225) et #211 l'ont fait avec un script Playwright jetable, hors du dépôt :

- réponses des services enregistrées une fois, puis rejouées ;
- horloge figée ;
- pour chaque état, une capture d'écran, puis le relevé de toutes les propriétés de chaque élément, y compris sous `:hover`, `:active` et `:focus-visible` forcés.

Dans #211, les états `bureau-objet-ouvert` (`/commune/lausanne?c=5586/INT26-069`) et `bureau-seance-ouverte` montraient des dizaines de milliers d'éléments présents d'un seul côté, et plus de 250 groupes de différences. Le Fil avait 119 lignes d'un côté, 331 de l'autre, avec d'autres groupes de communes. La CSS n'y était pour rien :

- le Fil change d'une exécution à l'autre, sur les deux sites. Deux relevés du même site ont fini par différer entre eux, et un essai a donné 330 lignes sur le site « avant » ;
- relever les styles avant la capture d'écran ne suffit pas : un relevé fait ainsi a encore donné 331 lignes ;
- deux relevés de suite peuvent tomber d'accord par hasard. Dans #211, les deux relevés « avant » avaient 119 lignes et les deux « après » 331, ce qui faisait croire à un écart dû au build.

La cause n'est pas établie. La zone du Fil suit certains déplacements de la carte (`deplacement`, `web/src/lib/registre/registre.svelte.ts:506-511`), mais le délai qui les rend « voulus » ne s'ouvre qu'après un choix dans la Recherche (`deplacementVoulu`, appelé seulement dans `web/src/routes/(carte)/+layout.svelte:167`). Ces états n'en font pas.

## Guidance

Rendre la preuve indépendante de la cause :

- **Hors du Fil** (`section.fil`), comparer tous les relevés deux à deux. Dans #211, chaque paire avant / après donnait 0 élément différent sur les deux états.
- **Dans le Fil**, ne comparer qu'une paire dont le Fil a le même contenu, en le vérifiant par le nombre de lignes ou leur texte. Une telle paire donnait 0 différence en tout (19 430 éléments × états).
- Les éléments « présents d'un seul côté » hors du Fil viennent des états forcés : la clé d'un élément forcé porte le rang de la commande dans la page, que des lignes de plus dans le Fil décalent. Ce n'est pas un écart.
- Avant de lire un écart ailleurs, faire un relevé de contrôle (deux relevés « avant », 0 différence attendue). Un écart limité à un sous-arbre, avec des éléments présents d'un seul côté, est d'abord un écart de contenu, pas de style.

## Why This Matters

Pris pour un vrai écart, ce faux écart fait chercher une régression qui n'existe pas. Il peut aussi masquer un vrai écart du Fil, noyé dans des milliers d'éléments décalés. Dans #211, il a coûté une demi-heure de relevés, dont une fausse piste (la capture d'écran).

## When to Apply

- Toute PR qui ne doit pas changer l'apparence et le prouve par cette comparaison : regroupement de règles, déplacement entre la feuille globale et un composant, renommage de jetons.
- Tout état dont l'adresse ouvre une fiche et laisse la carte cadrer la commune elle-même, sans `vue=`.

## Examples

Relevés de #211, état `bureau-objet-ouvert` puis `bureau-seance-ouverte` :

```text
paire                    lignes du Fil   hors Fil : différents   en tout
avant    / après         119 / 331       0                       14 614 éléments d'un seul côté
avant-2  / après-2       119 / 119       0                       0
séance : avant / après-1 119 / 331       0                       écart
séance : avant / après-2 119 / 119       0                       0
```

## Related

- #210 (décision, point 4) et PR #225 : la méthode de comparaison.
- #211 : le regroupement des règles CSS répétées, où l'écart est apparu.
