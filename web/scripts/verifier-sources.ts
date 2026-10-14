// Contrôle de `sources.json` à la construction du site (ADR 0013) : la construction échoue si le fichier ne suit
// pas le JSON Schema tiré des modèles Pydantic, ou s'il cite un n° OFS qui n'est pas une commune actuelle.
// Le site se construit sans Python : la validation passe par Ajv, sur le JSON Schema versionné dans `schema/`.
import { readFileSync } from 'node:fs';
import { Ajv2020 } from 'ajv/dist/2020.js';
import type { Plugin } from 'vite';
import type { FichierSources } from '../src/lib/schema.ts';

const lire = (chemin: string): unknown => JSON.parse(readFileSync(chemin, 'utf8'));

/** Erreurs de la déclaration des sources ; aucune si elle est valide. */
export function erreursSources(fichier: unknown, schema: object, communes: Set<number>): string[] {
	const valider = new Ajv2020({ allErrors: true }).compile<FichierSources>(schema);
	if (!valider(fichier)) {
		return (valider.errors ?? []).map((e) => `${e.instancePath || '/'} ${e.message}`);
	}
	const erreurs: string[] = [];
	const vus = new Set<string>();
	for (const source of fichier.sources) {
		if (vus.has(source.id)) erreurs.push(`identifiant de source en double : ${source.id}`);
		vus.add(source.id);
		const { communes: couvertes } = source.couverture;
		if (couvertes === 'canton') continue;
		for (const ofs of couvertes) {
			if (!communes.has(ofs)) erreurs.push(`${source.id} : le n° OFS ${ofs} n'est pas une commune actuelle`);
		}
	}
	return erreurs;
}

/** Fait échouer la construction (et le serveur de développement) si `sources.json` est invalide. */
export function verifierSources(chemins: { sources: string; schema: string; communes: string }): Plugin {
	return {
		name: 'verifier-sources',
		buildStart() {
			for (const chemin of Object.values(chemins)) this.addWatchFile(chemin);
			const communes = new Set((lire(chemins.communes) as { bfs: number }[]).map((c) => c.bfs));
			const erreurs = erreursSources(lire(chemins.sources), lire(chemins.schema) as object, communes);
			if (erreurs.length > 0) {
				this.error(`sources.json invalide :\n- ${erreurs.join('\n- ')}`);
			}
		}
	};
}
