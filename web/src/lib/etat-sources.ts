// État des sources (`etat-sources.json`), écrit par le cron dans le dépôt de données et lu par le navigateur au
// chargement, depuis les Pages de ce dépôt. On n'y valide rien au-delà de `version` : le cron valide à l'écriture.
import { DEPOT_DONNEES, DONNEES } from './config.js';
import type { EtatSources, Source } from './schema.js';

/** Seule version du format que le site connaît. */
export const VERSION_ETAT = 1;

/** L'état des sources lu, ou `null` (état « inconnu ») si ce n'est pas un objet de la version connue. */
export function lireEtatSources(json: unknown): EtatSources | null {
	const objet = json as Partial<EtatSources> | null;
	return typeof objet === 'object' && objet !== null && objet.version === VERSION_ETAT ? (objet as EtatSources) : null;
}

/**
 * Charge l'état des sources à l'adresse de base `donnees`. Absent, injoignable, illisible ou d'une version
 * inconnue, il vaut `null` : la Couverture dit alors l'état « inconnu », sans jamais lever d'erreur.
 */
export async function chargerEtatSources(f: typeof fetch, donnees: string = DONNEES): Promise<EtatSources | null> {
	try {
		const reponse = await f(`${donnees}/etat-sources.json`, { cache: 'no-cache' });
		return reponse.ok ? lireEtatSources(await reponse.json()) : null;
	} catch {
		return null;
	}
}

/**
 * Issues `panne-source` ouvertes pour cette source dans le dépôt de données. Le cron les titre
 * « Panne : <nom de la source> » (`titre_panne` dans `pipeline/cron.py`).
 */
export function lienPannes(source: Source): string {
	const q = `is:issue is:open label:panne-source in:title "Panne : ${source.nom}"`;
	return `${DEPOT_DONNEES}/issues?${new URLSearchParams({ q })}`;
}
