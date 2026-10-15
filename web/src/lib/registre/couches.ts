import { couchePermis } from '#lib/couches/permis/index.js';
import type { CoucheInscrite } from './types.js';

/**
 * Les couches inscrites. Leur ordre est celui du rail et celui du dessin : la première est dessinée
 * en dessous des autres.
 */
export const COUCHES: readonly CoucheInscrite[] = [couchePermis];
