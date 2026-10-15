import type { CoucheInscrite } from './types.js';

/** Source du fond de carte, citée en premier. */
export const FOND = 'swisstopo-fond';

/** Sources citées par l'attribution de la carte : le fond, puis celles des couches activées, dans l'ordre du registre. */
export function sourcesCarte(couches: readonly CoucheInscrite[], actives: readonly string[]): string[] {
	const ids = couches.filter((c) => actives.includes(c.id)).flatMap((c) => c.sources);
	return [...new Set([FOND, ...ids])];
}
