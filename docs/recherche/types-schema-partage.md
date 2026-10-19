# Types TypeScript générés depuis un schéma partagé avec Python

> Recherche pour l'issue #3 (carte #1). Relevé le 13 octobre 2026. Le choix final revient au ticket « Schéma commun
> du dépôt de données » (#9). Ce document compare les options ; il ne tranche pas.

## La question

L'ADR-0005 impose un schéma commun au JSON du dépôt de données `vigie-vaud-donnees`, dont on génère les types
TypeScript du site. Le producteur est le cron Python (`pipeline/`, uv, Python 3.11), le lecteur est le site
Svelte 5 + TypeScript (`web/`, pnpm). Aujourd'hui, les types du site sont écrits à la main dans
`web/src/lib/types.ts` (« Un dossier tel qu'écrit par pipeline/fetch.py »), sans lien vérifié avec ce qu'écrit
`fetch.py`.

Deux contraintes du projet pèsent sur la réponse :

- **Le site n'est pas reconstruit à chaque passage du cron** (ADR-0005). Un JSON qui change de forme peut donc
  casser un site déjà déployé : le schéma doit évoluer de manière compatible, ou porter une version.
- **Les scrapers de la phase 2 suivent le format OpenParlData** (ADR-0010) et doivent signaler un « format
  inattendu ». Une validation à l'écriture, côté Python, est donc de toute façon nécessaire.

## Les options

### A. JSON Schema écrit à la main, source unique

Un fichier `*.schema.json` (draft 2020-12) est la source de vérité. On en tire :

- **TypeScript** avec `json-schema-to-typescript` (`json2ts`), en dépendance de développement pnpm ;
- **la validation Python** avec `jsonschema` (`Draft202012Validator`) au moment d'écrire ;
- éventuellement **des modèles Python typés** avec `datamodel-code-generator` (Pydantic v2, dataclasses,
  `TypedDict` ou msgspec), lancé par `uv`.

Avantages : source neutre vis-à-vis des langages, publiable telle quelle (pour OpenParlData ou d'autres
réutilisateurs). Inconvénients : le JSON Schema est verbeux à écrire et à relire, et le code Python n'est typé que
si l'on ajoute un second générateur. Chaque évolution touche donc un fichier JSON et régénère deux sorties.

### B. Modèles Pydantic, source unique, JSON Schema exporté

Les modèles Pydantic du cron sont la source de vérité. Un petit script `uv run` écrit leur JSON Schema
(`model_json_schema()`) dans un fichier versionné, que `json2ts` convertit en TypeScript côté pnpm.

Avantages : le cron valide naturellement ce qu'il écrit (construire le modèle *est* la validation), le code Python
est typé sans générateur, et le JSON Schema reste un artefact publiable. Inconvénients : il faut régler l'export
pour obtenir des types TypeScript propres (voir l'essai plus bas), et la source est liée à Python.

L'outil `pydantic-to-typescript` enveloppe exactement cette chaîne (il appelle `json2ts`), mais il n'a pas eu de
version depuis novembre 2024 ; un script de dix lignes fait la même chose sans cette dépendance.

### C. Schéma écrit en TypeScript (Zod 4, TypeBox, Valibot), exporté vers Python

Le schéma vit côté site, sous forme de code TypeScript, et on exporte un JSON Schema pour Python :
`z.toJSONSchema()` (Zod 4), les schémas TypeBox (qui *sont* des objets JSON Schema), ou `@valibot/to-json-schema`.
Côté Python, on valide avec `jsonschema` ou on génère des modèles avec `datamodel-code-generator`.

Avantages : validation à la lecture idiomatique côté site (SvelteKit parle Standard Schema, que Zod et Valibot
implémentent). Inconvénients : la source vit du côté du *consommateur*, alors que le producteur est Python ; le
cron devrait dépendre d'une étape Node pour connaître son propre format.

### D. Outils multilangages (quicktype) et formats lourds

- **quicktype** génère TypeScript et Python depuis un JSON Schema (`quicktype -s schema schema.json`). Sa
  documentation promet des « modèles et sérialiseurs », sans validation décrite côté Python ; il ne remplace donc
  pas `jsonschema` ou Pydantic à l'écriture.
- **Protobuf, Avro, OpenAPI, LinkML** : faits pour des API ou des flux binaires, surdimensionnés pour quelques
  fichiers JSON statiques. `datamodel-code-generator` les lit tous si le besoin apparaît un jour.
- **msgspec** : alternative plus légère à Pydantic côté Python, qui exporte aussi un JSON Schema
  (`msgspec.json.schema`). Même schéma que l'option B, avec une communauté plus petite.

### Et OpenParlData ?

L'API publie bien un document OpenAPI 3.1 (`https://api.openparldata.ch/openapi.json`), mais ses réponses
`affairs` et `meetings` y sont décrites par un schéma vide (`{}`) : les seuls schémas nommés concernent les
statistiques et les erreurs. On ne peut donc pas importer leur format ; il faudra le recopier à la main dans le
nôtre, quelle que soit l'option.

## Maturité et maintenance

Relevé le 13 octobre 2026 dans les registres npm et PyPI et sur GitHub.

| Outil | Rôle | Dernière version | Dernier commit | Remarque |
|---|---|---|---|---|
| `pydantic` | Modèles Python, export JSON Schema | 2.14.1 (11.10.2026) | 13.10.2026 | ~29 000 étoiles, Python ≥ 3.10 |
| `json-schema-to-typescript` | JSON Schema → TS | 16.0.0 (28.08.2026) | 06.09.2026 | Node ≥ 22.19, Prettier inclus |
| `jsonschema` (Python) | Validation à l'écriture | 4.26.0 (07.01.2026) | 07.10.2026 | Drafts 3 à 2020-12 |
| `fastjsonschema` | Validation rapide | 2.22.2 (15.08.2026) | 24.09.2026 | **Drafts 4, 6 et 7 seulement** |
| `datamodel-code-generator` | JSON Schema → Python | 0.83.0 (24.09.2026) | 13.10.2026 | Encore en 0.x ; mode `--check` |
| `pydantic-to-typescript` | Pydantic → TS | 2.0.0 (22.11.2024) | 22.11.2024 | Inactif depuis près de deux ans |
| `zod` | Schéma TS, export JSON Schema | 4.6.7 (12.10.2026) | 13.10.2026 | ~44 000 étoiles |
| `typebox` | Schéma TS = JSON Schema | 1.3.37 (12.10.2026) | 12.10.2026 | ESM seulement ; 0.x en LTS |
| `valibot` | Schéma TS | 1.5.0 (09.09.2026) | 09.10.2026 | Export via `@valibot/to-json-schema` |
| `ajv` | Validation JSON Schema en JS | 8.20.0 (24.04.2026) | 24.04.2026 | Code autonome précompilé |
| `quicktype` | Multilangage | 26.0.0 (20.07.2026) | 08.09.2026 | Entrée TypeScript expérimentale |
| `json-schema-to-zod` | JSON Schema → Zod | 2.8.1 (01.04.2026) | — | **Archivé le 30.06.2026** |

## Validation côté site, à la lecture

Elle est facultative, mais le dépôt de données vit à son propre rythme (ADR-0005). Trois niveaux possibles :

1. **Aucune** : on fait confiance au cron, qui valide à l'écriture. Simple, mais un site ancien face à un JSON
   nouveau échoue de manière imprévisible.
2. **Un numéro de version** du schéma dans `meta.json`, que le site compare à celui qu'il attend, avec un
   message clair en cas d'écart. Presque gratuit.
3. **Une validation complète** avec Ajv en code autonome : le validateur est généré au build depuis le même JSON
   Schema, sans `new Function` à l'exécution (compatible avec une CSP stricte) et sans embarquer Ajv entier. Ajv
   gère le draft 2020-12 avec une classe dédiée. Coût : du poids dans le bundle, pour des fichiers parfois gros
   (tous les dossiers d'une commune).

Partir de Zod ou Valibot *depuis* un JSON Schema n'est pas recommandable aujourd'hui : `z.fromJSONSchema()` est
déclaré expérimental et hors de l'API stable de Zod, et `json-schema-to-zod` est archivé.

## Essai : Pydantic → JSON Schema → TypeScript

Fait le 13 octobre 2026 avec pydantic 2.14.1 et json-schema-to-typescript 16.0.0, sur un extrait du `Dossier`
actuel. Trois réglages se sont révélés nécessaires pour obtenir des types aussi propres que ceux écrits à la main :

- **Retirer les titres de champs.** Par défaut, Pydantic donne un `title` à chaque propriété, et `json2ts` en
  fait un alias par champ (`export type Id = number`, `Statut1`…). Une sous-classe de `GenerateJsonSchema` dont
  `field_title_should_be_set` renvoie `False` les supprime.
- **Nommer les énumérations partagées** avec `TypeAliasType("Statut", Literal[...])` : Pydantic les place dans
  `$defs` et `json2ts` produit un seul `export type Statut`, réutilisé partout.
- **Interdire les champs inconnus** (`extra="forbid"`), sinon `json2ts` ajoute `[k: string]: unknown` à chaque
  interface (`additionalProperties` vaut `true` par défaut).

Résultat obtenu :

```ts
export type Statut = "enquete" | "procedure" | "delivre" | "realise" | "abandonne" | "autre";

export interface Dossier {
  id: number;
  fao?: string | null;
  statut: Statut;
  precedent?: Statut | null;
}
```

Écart restant : un champ `str | None = None` devient `fao?: string | null`, plus large que le `fao?: string`
actuel (le cron omet les champs vides). C'est sans danger si l'on écrit avec `model_dump_json(exclude_none=True)`.
Pour un type exact, un `TypedDict` avec `NotRequired[str]` donne bien `fao?: string`.

## Coût d'une évolution du schéma

| | A. JSON Schema à la main | B. Pydantic | C. Zod / TypeBox |
|---|---|---|---|
| Où l'on modifie | Le `.schema.json` | Le modèle Python | Le schéma TS |
| Ce qu'on régénère | TS (pnpm) + modèles Python (uv), si utilisés | Schéma (uv) puis TS (pnpm) | Schéma (pnpm) puis Python (uv), si utilisé |
| Python typé | Seulement avec `datamodel-code-generator` | Oui, nativement | Seulement avec `datamodel-code-generator` |
| Validation à l'écriture | `jsonschema` | Le modèle lui-même | `jsonschema` |
| Contrôle en CI | `git diff --exit-code` après régénération | Idem | Idem |

Dans tous les cas, `pipeline/` et `web/` vivant dans le même dépôt, on versionne le JSON Schema et les types
générés, et la CI vérifie qu'une régénération ne change rien. Publier aussi le schéma dans `vigie-vaud-donnees`
(référencé par `$schema`) le rendrait utilisable par d'autres.

Quelle que soit l'option, l'ajout d'un champ facultatif est sans risque pour un site déjà déployé ; un renommage
ou un changement de type demande une nouvelle version du schéma.

## Pistes de recommandation

Pour le ticket #9, l'option **B (Pydantic comme source, JSON Schema 2020-12 versionné, `json2ts` côté site)**
semble la mieux adaptée :

- le producteur est Python, et la validation à l'écriture, déjà exigée par l'ADR-0010, vient sans effort ;
- une seule source à modifier, et le code du cron est typé sans générateur supplémentaire ;
- les deux outils de la chaîne sont activement maintenus, et l'essai produit des types équivalents à ceux de
  `types.ts` moyennant trois réglages ;
- le JSON Schema reste un artefact neutre, publiable et réutilisable par Ajv si l'on veut valider côté site.

L'option **A** reste défendable si l'on veut une source indépendante de tout langage (par exemple pour la proposer
à OpenParlData), au prix d'un fichier plus verbeux et d'un second générateur. L'option **C** inverse le sens de la
dépendance et n'a d'intérêt que si la validation côté site devient centrale.

Côté site, un **numéro de version dans `meta.json`** suffit probablement au début ; Ajv en code autonome peut venir
plus tard, sans changer de schéma.

## Sources

- ADR-0005 et ADR-0010 du projet ; `web/src/lib/types.ts` ; `pipeline/fetch.py`.
- Pydantic, JSON Schema : <https://pydantic.dev/docs/validation/latest/concepts/json_schema/>
- json-schema-to-typescript : <https://github.com/bcherny/json-schema-to-typescript>
- python-jsonschema : <https://python-jsonschema.readthedocs.io/en/stable/>
- fastjsonschema : <https://horejsek.github.io/python-fastjsonschema/>
- datamodel-code-generator : <https://github.com/koxudaxi/datamodel-code-generator>, et dans le dépôt
  `docs/ci-cd.md` (mode `--check`) et `docs/supported_formats.md` (drafts pris en charge)
- pydantic-to-typescript : <https://github.com/phillipdupuis/pydantic-to-typescript>
- Zod et JSON Schema : <https://zod.dev/json-schema>
- TypeBox : <https://github.com/sinclairzx81/typebox>
- Ajv, code autonome : <https://ajv.js.org/standalone.html> ; draft 2020-12 : <https://ajv.js.org/json-schema.html>
- quicktype : <https://github.com/glideapps/quicktype>
- json-schema-to-zod (archivé) : <https://github.com/StefanTerdell/json-schema-to-zod>
- SvelteKit et Standard Schema : <https://svelte.dev/docs/kit/remote-functions>
- OpenParlData, OpenAPI : <https://api.openparldata.ch/openapi.json>
- Versions et activité : registres `registry.npmjs.org` et `pypi.org`, API GitHub (`repos/*`, `commits`).
