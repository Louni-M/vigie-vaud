import { coucheConseils } from '#lib/couches/conseils/index.js';
import { coucheHotelsDeVille } from '#lib/couches/hotels-de-ville/index.js';
import { couchePermis } from '#lib/couches/permis/index.js';
import { coucheRoutesPrototype } from '#lib/couches/routes-prototype/index.js';
import type { CoucheInscrite } from './types.js';

/**
 * Les couches inscrites. Leur ordre est celui du rail et celui du dessin : la première est dessinée
 * en dessous des autres. Hôtels de ville est dessinée en dernier, au-dessus de toutes.
 */
export const COUCHES: readonly CoucheInscrite[] = [
	couchePermis,
	// PROTOTYPE : en développement seulement.
	...(import.meta.env.DEV ? [coucheRoutesPrototype] : []),
	coucheConseils,
	coucheHotelsDeVille
];
