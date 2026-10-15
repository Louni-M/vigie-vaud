// Types TypeScript du schéma commun (ADR 0013), tirés des JSON Schema de `schema/` que génère
// `pipeline/schema.py`. Lancé par `pnpm schema`, après la génération des JSON Schema.
//
// Les documents sont réunis en un seul schéma, pour que chaque type partagé ne soit écrit qu'une fois
// dans `src/lib/schema.ts`.
import { readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { compile } from 'json-schema-to-typescript';

const DOSSIER = new URL('../../schema/', import.meta.url);
const SORTIE = new URL('../src/lib/schema.ts', import.meta.url);

const EN_TETE = `/* Fichier généré par \`pnpm schema\` depuis pipeline/schema.py : ne pas modifier.
 * Pour changer le schéma commun, modifier les modèles Pydantic puis relancer \`pnpm schema\`. */`;

const defs = {};
const documents = [];
for (const fichier of readdirSync(DOSSIER).filter((f) => f.endsWith('.schema.json')).sort()) {
	const { $schema: _, $defs = {}, ...racine } = JSON.parse(readFileSync(new URL(fichier, DOSSIER), 'utf8'));
	for (const [nom, def] of Object.entries({ ...$defs, [racine.title]: racine })) {
		if (nom in defs && JSON.stringify(defs[nom]) !== JSON.stringify(def)) {
			throw new Error(`${fichier} : le type ${nom} diffère d'un autre document du schéma commun`);
		}
		defs[nom] = def;
	}
	documents.push({ $ref: `#/$defs/${racine.title}` });
}

const ts = await compile({ title: 'DocumentCommun', anyOf: documents, $defs: defs }, 'DocumentCommun', {
	bannerComment: EN_TETE,
	unreachableDefinitions: true,
	style: { useTabs: true, singleQuote: true, printWidth: 120 }
});
writeFileSync(SORTIE, ts);
console.log('web/src/lib/schema.ts');
