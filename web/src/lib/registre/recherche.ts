import type { Resultat } from '#lib/types.js';
import type { CoucheInscrite } from './types.js';

/** Résultats `chercher` des couches inscrites pour une saisie, tels que les affiche la recherche du socle. */
export const resultatsCouches = (couches: readonly CoucheInscrite[], texte: string): Extract<Resultat, { type: 'element' }>[] =>
	couches.flatMap((c) =>
		(c.chercher?.(texte) ?? []).map((r) => ({
			type: 'element' as const,
			nomCouche: c.nom,
			libelle: r.libelle,
			couche: r.couche,
			element: r.element
		}))
	);
