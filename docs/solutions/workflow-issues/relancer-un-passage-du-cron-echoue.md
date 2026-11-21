---
title: Relancer un passage du cron échoué repart des données d'avant et échoue au push
date: 2026-11-21
category: workflow-issues
module: cron (workflow réutilisable `.github/workflows/cron.yml`, déclencheur du dépôt de données)
problem_type: workflow_issue
component: development_workflow
severity: medium
applies_when:
  - Un passage du cron de `vigie-vaud-donnees` a échoué après avoir poussé au moins une phase, par exemple au déploiement Pages
  - On veut rattraper le site ou les données sans attendre le prochain passage planifié
symptoms:
  - "La relance (« Re-run failed jobs », `gh run rerun --failed`) échoue à l'étape « Passage du cron »"
  - "Push refusé, puis `CONFLICT (content): Merge conflict in etat-sources.json` au `pull --rebase`"
root_cause: wrong_api
resolution_type: workflow_improvement
tags: [cron, github-actions, relance, rerun, workflow-dispatch, pages, etat-sources]
---

# Relancer un passage du cron échoué repart des données d'avant et échoue au push

## Context

Le passage du 21 novembre 2026 (run 198 de `vigie-vaud-donnees`) a poussé ses commits d'archive, puis échoué au déploiement Pages. Pour rattraper le site, on a relancé le job échoué (`gh run rerun 44943001972 --failed`). La relance a échoué plus tôt, à l'étape « Passage du cron » :

```
Push refusé : pull --rebase puis nouvel essai (1/2)
CONFLICT (content): Merge conflict in etat-sources.json
Push refusé : le passage échoue, le suivant repartira de l'état relu.
```

Une relance garde le `GITHUB_SHA` du premier essai. `actions/checkout` du dépôt de données clone donc ce commit-là, celui qui avait déclenché le passage, et non le bout actuel de `main` :

```
git fetch ... origin +76d5b92...:refs/remotes/origin/main
git checkout --progress --force -B main refs/remotes/origin/main
```

Le passage relancé part ainsi de données plus anciennes que celles que le premier essai a déjà poussées. Son push est refusé, et le `pull --rebase` de `pousser` (`pipeline/cron.py`, « Push refusé ») bute sur `etat-sources.json`, que chaque passage réécrit. Le passage s'arrête sans rien pousser : les données restent intactes, mais rien n'est rattrapé.

## Guidance

Pour rattraper un passage échoué, lancer un nouveau passage, jamais une relance :

```bash
gh workflow run Cron -R Louni-M/vigie-vaud-donnees
```

Un lancement manuel (`workflow_dispatch`) a son propre `GITHUB_SHA`, le bout actuel de `main`. Il appelle aussi `cron.yml@cron` à son bout du moment, alors qu'une relance garde, d'après ce qu'on en sait, le commit du workflow réutilisable du premier essai : un correctif arrivé sur `cron` depuis n'y serait pas.

Attendre que la relance ou le passage en cours soit fini avant de lancer : le groupe de concurrence `cron` mettrait sinon un second passage à la suite.

## Why This Matters

La relance semble l'outil naturel pour un job qui a échoué à sa dernière étape. Ici elle ne rejoue pas seulement le déploiement mais tout le job, sondes et imports compris, depuis un état périmé. Elle coûte un passage entier (environ 15 minutes) pour échouer, et le site reste en retard jusqu'au passage suivant, parfois plusieurs heures plus tard.

## When to Apply

Pour tout passage du cron qui a poussé au moins un commit avant d'échouer. La relance ne fonctionnerait que si aucun commit n'avait été poussé entre-temps, ni par ce passage ni par un autre : on ne le sait pas d'avance, autant lancer un passage neuf.

## Examples

- Run 198, tentative 1 : données poussées, déploiement Pages échoué (artefact pas encore listé, voir le commentaire de l'étape « Laisser l'artefact apparaître » dans `.github/workflows/cron.yml`, PR #232).
- Run 198, tentative 2 (relance) : checkout de `76d5b92`, push refusé, conflit sur `etat-sources.json`, échec sans push.
- Rattrapage correct : `gh workflow run Cron -R Louni-M/vigie-vaud-donnees`, une fois le passage précédent terminé.
