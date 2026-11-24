import { describe, expect, it } from 'vitest';
import { sourcesCarte } from './attribution.js';
import type { CoucheInscrite } from './types.js';

const couche = (id: string, sources: string[], champs: Partial<CoucheInscrite> = {}): CoucheInscrite => ({
	id,
	nom: id,
	sources,
	permanente: false,
	composants: { Carte: () => Promise.reject(new Error('non chargé')) },
	...champs
});

/** `a` et `b` ne sont sur la carte que dessinées ; `h` est permanente. */
const COUCHES = [couche('a', ['sa', 'commune']), couche('b', ['sb']), couche('h', ['commune', 'sh'], { permanente: true })];

describe('attribution de la carte', () => {
	it('cite le fond de carte, puis les sources des couches sur la carte, une fois chacune', () => {
		expect(sourcesCarte(COUCHES, 'a')).toEqual(['swisstopo-fond', 'sa', 'commune', 'sh']);
	});

	it('suit la couche dessinée', () => {
		expect(sourcesCarte(COUCHES, null)).toEqual(['swisstopo-fond', 'commune', 'sh']);
		expect(sourcesCarte(COUCHES, 'b')).toEqual(['swisstopo-fond', 'sb', 'commune', 'sh']);
	});
});
