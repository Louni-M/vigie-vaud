import { coucheConseils } from '#lib/couches/conseils/index.js';
import { coucheHotelsDeVille } from '#lib/couches/hotels-de-ville/index.js';
import { couchePermis } from '#lib/couches/permis/index.js';
import { coucheRoutes } from '#lib/couches/routes/index.js';
import type { CoucheInscrite } from './types.js';

/**
 * Les couches inscrites. Leur ordre est celui du rail et celui du dessin : la première est dessinée
 * en dessous des autres. Hôtels de ville est dessinée en dernier, au-dessus de toutes.
 */
export const COUCHES: readonly CoucheInscrite[] = [couchePermis, coucheConseils, coucheRoutes, coucheHotelsDeVille];
