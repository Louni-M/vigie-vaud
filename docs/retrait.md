# Retrait d'un nom : marche à suivre

Pour la personne qui tient le projet, quand quelqu'un demande par courriel qu'un nom soit retiré d'un élément
publié (ADR-0007, glossaire : *Retrait*). Délai annoncé par la page Protection des données : **7 jours**.

Une demande qui arrive par une issue publique : fermer l'issue sans citer le nom, en masquer le contenu
(« Hide » ou suppression par le propriétaire du dépôt), et répondre par courriel si une adresse est connue.

## 1. Trouver l'élément

Le titre signalé se cherche dans le clone du dépôt de données (`vigie-vaud-donnees`) :

```bash
grep -rl "Nom signalé" conseils/
```

Noter la **clé** de chaque élément touché (le chemin sans `conseils/`, `objets/` ou `seances/` ni `.json`) :
`5586/PET25-003` pour `conseils/5586/objets/PET25-003.json`, `5607/2026-06-11` pour
`conseils/5607/seances/2026-06-11.json`, et le **champ** où le nom apparaît.

## 2. Écrire la correction dans `retraits.json`

À la racine du dépôt de données, une entrée par champ, **sans jamais écrire le nom retiré** :

```json
[
  { "element": "5586/PET25-003", "cible": "titre", "texte": "Pétition de [particulier] : « Pour un parc à chiens »", "date": "2026-11-02" },
  { "element": "5607/2026-06-11", "cible": "point:4", "texte": "Préavis 7/2026 - Succession [particulier]", "date": "2026-11-02" },
  { "element": "5586/PET25-003", "cible": "document:https://www.lausanne.ch/pet25-003.pdf", "texte": "Pétition", "date": "2026-11-02" }
]
```

- `titre` : le titre d'un Objet ; `nom` : le nom d'une Séance ;
- `point:<n>` : le titre du n-ième point de l'ordre du jour d'une Séance, à partir de 1, dans l'ordre du fichier ;
- `document:<lien>` : le titre du document qui a exactement ce lien.

Puis, depuis `pipeline/` du dépôt principal, vérifier en local :

```bash
uv run python conseils.py --depot ../../vigie-vaud-donnees --depuis $(date +%F)
grep -rl "Nom signalé" ../../vigie-vaud-donnees/conseils/   # ne doit plus rien trouver
```

Le cron applique `retraits.json` à chaque import et à chaque rattrapage : le nom ne revient pas, même quand la
source rapporte le titre d'origine. Un fichier invalide fait échouer l'import (rien n'est écrit) ; une cible
introuvable est signalée par « Retrait sans effet » dans le journal du cron.

Si le cas révèle une règle (un mot déclencheur, une forme de nom), corriger aussi `pipeline/masquage.py` et
`web/src/lib/masquage.ts`, avec un test, dans le dépôt principal.

## 3. Réécrire l'historique du dépôt de données

Le nom reste dans les commits passés. Avec `git filter-repo` (à installer à part), dans un clone **frais** du dépôt
de données, cron mis en pause (`gh workflow disable cron.yml -R Louni-M/vigie-vaud-donnees`) :

```bash
printf 'Nom signalé==>[particulier]\n' > /tmp/remplacements.txt
git filter-repo --replace-text /tmp/remplacements.txt --force
grep -r "Nom signalé" . ; git log -p | grep -c "Nom signalé"   # 0 et 0
git remote add origin https://github.com/Louni-M/vigie-vaud-donnees.git
git push --force origin main
rm /tmp/remplacements.txt
gh workflow enable cron.yml -R Louni-M/vigie-vaud-donnees
```

`/tmp/remplacements.txt` contient le nom : il ne doit jamais être commité, ni collé dans une issue. Les Pages du dépôt
de données sont republiées au passage suivant du cron.

## 4. Répondre

Répondre par courriel une fois le push fait, en rappelant que le texte d'origine reste chez la source (OpenParlData
ou le site du conseil), que Vigie Vaud ne contrôle pas.
