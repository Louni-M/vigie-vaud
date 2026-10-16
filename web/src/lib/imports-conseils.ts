// Dernier import réussi de chaque conseil (`conseils/import.json`), écrit par le cron dans le dépôt de données et
// lu par le navigateur pour le badge de fraîcheur des sources `import`. On n'y valide rien au-delà de `version`.
import { DONNEES } from './config.js';
import type { ImportConseils, Source } from './schema.js';

/** Seule version du format que le site connaît. */
export const VERSION_IMPORTS = 1;

/**
 * Charge `conseils/import.json` à l'adresse de base `donnees`. Absent, injoignable, illisible ou d'une version
 * inconnue, il vaut `null` : le badge dit alors le dernier import inconnu, sans jamais lever d'erreur.
 */
export async function chargerImports(f: typeof fetch, donnees: string = DONNEES): Promise<ImportConseils | null> {
	try {
		const reponse = await f(`${donnees}/conseils/import.json`, { cache: 'no-cache' });
		if (!reponse.ok) return null;
		const objet = (await reponse.json()) as Partial<ImportConseils> | null;
		return typeof objet === 'object' && objet !== null && objet.version === VERSION_IMPORTS
			? (objet as ImportConseils)
			: null;
	} catch {
		return null;
	}
}

/** Heure du dernier import réussi du conseil de cette source (clé : `body_key` en minuscules), ou `null`. */
export function dernierImport(imports: ImportConseils | null, source: Source): Date | null {
	const quand = source.conseil && imports?.conseils?.[source.conseil.body_key.toLowerCase()];
	return quand ? new Date(quand) : null;
}
