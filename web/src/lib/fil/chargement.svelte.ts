import type { CoucheInscrite, Fil } from '#lib/registre/types.js';
import { depuisFil, type SourceFil } from './fil.js';

/**
 * Chargement des entrées du fil : il parcourt les couches à la recherche de `fil`, sans en connaître aucune par
 * son nom, et leur demande leurs entrées à la première ouverture du fil, qu'elles soient activées ou non.
 */
export function creerChargementFil(couches: readonly CoucheInscrite[]) {
	const avecFil = couches.filter((c): c is CoucheInscrite & { fil: Fil } => c.fil !== undefined);
	let etats = $state<Record<string, SourceFil['etat']>>({});
	let depuis: string | null = null;

	function lancer(c: CoucheInscrite & { fil: Fil }, d: string) {
		etats[c.id] = 'chargement';
		c.fil.entrees(d).then(
			(entrees) => (etats[c.id] = { entrees }),
			() => (etats[c.id] = 'panne')
		);
	}

	return {
		/** Les couches du fil, dans l'ordre du rail ; `chargement` tant que leurs entrées n'ont pas été lues. */
		get sources(): SourceFil[] {
			return avecFil.map((c) => ({
				couche: c.id,
				nom: c.nom,
				types: c.fil.types,
				etat: etats[c.id] ?? 'chargement'
			}));
		},
		/** Première ouverture du fil : chaque couche est lue une fois, depuis le premier jour du fil. */
		charger(aujourdhui: string) {
			if (depuis !== null) return;
			const d = (depuis = depuisFil(aujourdhui));
			for (const c of avecFil) lancer(c, d);
		},
		/** « Réessayer » sur la ligne d'une couche en panne. */
		reessayer(id: string) {
			const c = avecFil.find((c) => c.id === id);
			if (c && depuis !== null) lancer(c, depuis);
		}
	};
}

export type ChargementFil = ReturnType<typeof creerChargementFil>;
