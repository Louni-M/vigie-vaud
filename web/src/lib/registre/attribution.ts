import { couchesSurLaCarte } from './dessin.js';
import type { CoucheInscrite } from './types.js';

/** Source du fond de carte, citée en premier. */
export const FOND = 'swisstopo-fond';

/**
 * Sources citées par l'attribution de la carte : le fond, puis celles des couches sur la carte (la couche dessinée et
 * celles qui le sont toujours), dans l'ordre du registre.
 */
export function sourcesCarte(couches: readonly CoucheInscrite[], dessinee: string | null): string[] {
	const surLaCarte = couchesSurLaCarte(couches, dessinee);
	const ids = couches.filter((c) => surLaCarte.includes(c.id)).flatMap((c) => c.sources);
	return [...new Set([FOND, ...ids])];
}
