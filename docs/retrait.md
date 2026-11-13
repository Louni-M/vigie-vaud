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

## 2. Calculer l'empreinte d'un point d'ordre du jour

Pour un point (`point:<n>`), **avant** d'écrire la correction : l'empreinte du titre d'origine permet au cron de
retrouver le point quand la source en insère un avant lui (ADR-0007). C'est un HMAC-SHA256 sous la clé secrète
`RETRAITS_CLE` du dépôt de données, dont la personne qui tient le projet garde une copie hors ligne (gestionnaire
de mots de passe) : GitHub ne rend pas un secret. Depuis `pipeline/` du dépôt principal, la clé saisie sans écho
(elle n'entre pas dans l'historique du terminal) :

```bash
read -rs RETRAITS_CLE && export RETRAITS_CLE
uv run python retraits.py --depot ../../vigie-vaud-donnees 5607/2026-06-11 point:4
```

La commande lit le titre du 4ᵉ point dans le clone et affiche son empreinte (64 caractères hexadécimaux), sans
jamais demander le titre ni la clé sur la ligne de commande. Si le point est déjà corrigé dans le clone (retrait
ancien, sans empreinte), le titre d'origine vient de la source : `uv run python retraits.py --stdin`, coller le
titre, puis Ctrl-D.

Première fois : créer la clé (au moins 32 caractères aléatoires) et la poser comme secret du dépôt de données,
sans qu'elle passe par l'historique du terminal ni par un fichier :

```bash
python -c "import secrets; print(secrets.token_hex(32))"      # à copier dans le gestionnaire de mots de passe
gh secret set RETRAITS_CLE -R Louni-M/vigie-vaud-donnees       # la coller à l'invite
```

Changer la clé impose de recalculer chaque empreinte de `retraits.json` (avec `--stdin`, depuis le titre de la
source).

## 3. Écrire la correction dans `retraits.json`

À la racine du dépôt de données, une entrée par champ, **sans jamais écrire le nom retiré** :

```json
[
  { "element": "5586/PET25-003", "cible": "titre", "texte": "Pétition de [particulier] : « Pour un parc à chiens »", "date": "2026-11-02" },
  { "element": "5607/2026-06-11", "cible": "point:4", "empreinte": "3f0c…(64 caractères)…9a1e", "texte": "Préavis 7/2026 - Succession [particulier]", "date": "2026-11-02" },
  { "element": "5586/PET25-003", "cible": "document:https://www.lausanne.ch/pet25-003.pdf", "texte": "Pétition", "date": "2026-11-02" }
]
```

- `titre` : le titre d'un Objet ; `nom` : le nom d'une Séance ;
- `point:<n>` : le titre du n-ième point de l'ordre du jour d'une Séance, à partir de 1, dans l'ordre du fichier,
  avec l'`empreinte` de l'étape 2 : le cron corrige le point qui a cette empreinte, même si la source l'a déplacé.
  Une entrée sans empreinte (les plus anciennes) reste valide et vise le seul rang ;
- `document:<lien>` : le titre du document qui a exactement ce lien.

Puis, depuis `pipeline/` du dépôt principal, `RETRAITS_CLE` toujours exportée (sans elle, l'empreinte n'est pas
vérifiée et le point est corrigé à son rang), vérifier en local :

```bash
uv run python conseils.py --depot ../../vigie-vaud-donnees --depuis $(date +%F)
grep -rl "Nom signalé" ../../vigie-vaud-donnees/conseils/   # ne doit plus rien trouver
```

Le cron applique `retraits.json` à chaque import et à chaque rattrapage : le nom ne revient pas, même quand la
source rapporte le titre d'origine ou insère un point avant celui qui est corrigé. Un fichier invalide fait échouer
l'import (rien n'est écrit). Une cible introuvable, ou une empreinte qu'aucun point n'a plus (la source a changé le
titre), est signalée par « Retrait sans effet » dans le journal du cron et dans l'issue `retrait-sans-effet` du
dépôt de données, qui ne donne que la clé de l'élément et la cible : vérifier l'élément, recalculer l'empreinte
(étape 2) ou corriger le rang. Le cron ferme l'issue quand chaque retrait a de nouveau effet. La même issue signale
une `RETRAITS_CLE` absente du workflow : les retraits à empreinte y sont corrigés à leur rang, sans vérification.

Si le cas révèle une règle (un mot déclencheur, une forme de nom), corriger aussi `pipeline/masquage.py` et
`web/src/lib/masquage.ts`, avec un test, dans le dépôt principal.

## 4. Réécrire l'historique du dépôt de données

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

## 5. Répondre

Répondre par courriel une fois le push fait, en rappelant que le texte d'origine reste chez la source (OpenParlData
ou le site du conseil), que Vigie Vaud ne contrôle pas.
