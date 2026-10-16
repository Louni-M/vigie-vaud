import { describe, expect, it } from 'vitest';
import { clesEnDouble } from './url.js';
import { COUCHES } from './couches.js';
import type { Codec, CoucheInscrite } from './types.js';

const codec = (...cles: string[]): Codec<null> => ({ cles, lire: () => null, ecrire: () => [] });

const couche = (id: string, champs: Partial<CoucheInscrite> = {}): CoucheInscrite => ({
	id,
	nom: id,
	sources: [],
	permanente: false,
	activeParDefaut: false,
	icone: { signe: id, couleur: '#000' },
	composants: { Carte: () => Promise.reject(new Error('non chargé')) },
	...champs
});

describe('clés d’URL', () => {
	it('sont uniques entre les couches inscrites et le registre', () => {
		expect(clesEnDouble(COUCHES)).toEqual([]);
	});

	it('comptent la clé d’élément de chaque couche inscrite, `c` des Conseils comprise', () => {
		expect(COUCHES.map((c) => c.cleElement).filter(Boolean)).toEqual(['d', 'c']);
	});

	it('signale une clé prise par deux couches', () => {
		const couches = [couche('a', { codec: codec('tri', 'x') }), couche('b', { codec: codec('tri') })];
		expect(clesEnDouble(couches)).toEqual(['tri']);
	});

	it('signale une clé du registre reprise par une couche', () => {
		expect(clesEnDouble([couche('a', { codec: codec('couches') }), couche('b', { codec: codec('vue') })])).toEqual([
			'couches',
			'vue'
		]);
	});

	it('signale une clé d’élément reprise par un codec ou par une autre couche', () => {
		expect(clesEnDouble([couche('a', { cleElement: 'd', codec: codec('d') })])).toEqual(['d']);
		expect(clesEnDouble([couche('a', { cleElement: 'd' }), couche('b', { cleElement: 'd' })])).toEqual(['d']);
	});
});
