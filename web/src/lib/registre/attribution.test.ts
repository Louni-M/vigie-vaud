import { describe, expect, it } from 'vitest';
import { sourcesCarte } from './attribution.js';
import type { CoucheInscrite } from './types.js';

const couche = (id: string, sources: string[]): CoucheInscrite => ({
	id,
	nom: id,
	sources,
	permanente: false,
	activeParDefaut: false,
	icone: { signe: id, couleur: '#000' },
	composants: { Carte: () => Promise.reject(new Error('non chargé')) }
});

const COUCHES = [couche('a', ['sa', 'commune']), couche('b', ['sb']), couche('c', ['commune', 'sc'])];

describe('attribution de la carte', () => {
	it('cite le fond de carte, puis les sources des seules couches activées, une fois chacune', () => {
		expect(sourcesCarte(COUCHES, ['a', 'c'])).toEqual(['swisstopo-fond', 'sa', 'commune', 'sc']);
		expect(sourcesCarte(COUCHES, [])).toEqual(['swisstopo-fond']);
	});
});
