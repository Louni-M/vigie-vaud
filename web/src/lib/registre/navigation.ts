import type { Centre } from '#lib/types.js';
import type { Ouvert } from './types.js';

/** Ce que l'adresse dit de la carte : la commune du chemin, la vue et l'élément de la requête. */
export interface Adresse {
	commune: string | null;
	vue: Centre | null;
	ouvert: Ouvert | null;
}

/** Ce que doit faire la carte : rétablir une vue, cadrer une commune, revenir au canton, ou rien (`null`). */
export type Mouvement = { aller: Centre } | { cadrer: string } | 'canton' | null;

/**
 * Mouvement de la carte quand l'adresse change sous le registre : arrivée sur le site (`initial`), lien suivi,
 * précédent ou suivant du navigateur. La vue de l'adresse l'emporte toujours ; sinon une commune qu'on vient
 * d'ouvrir est cadrée, et l'adresse nue « / » ramène au canton. `avant` est la commune de l'adresse précédente.
 */
export function mouvement(avant: string | null, apres: Adresse, initial: boolean): Mouvement {
	if (apres.vue) return { aller: apres.vue };
	if (apres.commune) return apres.commune === avant ? null : { cadrer: apres.commune };
	if (initial || apres.ouvert) return null;
	return 'canton';
}
