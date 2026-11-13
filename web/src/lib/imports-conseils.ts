// Dernier import réussi de chaque conseil (`conseils/import.json`), écrit par le cron dans le dépôt de données et
// lu par le navigateur pour le badge de fraîcheur des sources `import`. On n'y valide rien au-delà de `version`.
import { lireJsonVersionne } from './chargement.js';
import { DONNEES } from './config.js';
import type { ImportConseils, Source } from './schema.js';
import { cleConseil } from './sources.js';

/** Seule version du format que le site connaît. */
export const VERSION_IMPORTS = 1;

/**
 * Charge `conseils/import.json` à l'adresse de base `donnees`. Absent, injoignable, trop lent, illisible ou d'une
 * version inconnue, il vaut `null` : le badge dit alors le dernier import inconnu, sans jamais lever d'erreur.
 */
export const chargerImports = (f: typeof fetch, donnees: string = DONNEES): Promise<ImportConseils | null> =>
	lireJsonVersionne<ImportConseils>(f, `${donnees}/conseils/import.json`, VERSION_IMPORTS, {
		init: { cache: 'no-cache' }
	}).catch(() => null);

/** Heure du dernier import réussi du conseil de cette source (par sa clé, `cleConseil`), ou `null`. */
export function dernierImport(imports: ImportConseils | null, source: Source): Date | null {
	const quand = source.conseil && imports?.conseils?.[cleConseil(source.conseil)];
	return quand ? new Date(quand) : null;
}
