import { describe, expect, it } from 'vitest';
import { messageNonCouvert, sourcesDeLOnglet } from './onglet.js';
import { coucheConseils } from '#lib/couches/conseils/index.js';
import { couchePermis } from '#lib/couches/permis/index.js';
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import type { CoucheInscrite } from './types.js';
import { commune } from '#tests/faux-canton.js';

const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
const BUSSIGNY = commune(5624, 'Bussigny', [6.53, 46.54, 6.57, 46.57]);

const noms = (couche: CoucheInscrite, bfs: number, sources: readonly Source[] = SOURCES) =>
	sourcesDeLOnglet(couche, sources, bfs).map((s) => s.nom_court);

describe('badges sous le nom d’un onglet', () => {
	it('à Lausanne, le conseil de la commune puis le Grand Conseil, qui porte sur le canton', () => {
		expect(noms(coucheConseils, LAUSANNE.bfs)).toEqual(['Conseil de Lausanne', 'Grand Conseil']);
	});

	it('à Bussigny, que le conseil couvert ne concerne pas, seulement le Grand Conseil', () => {
		expect(noms(coucheConseils, BUSSIGNY.bfs)).toEqual(['Grand Conseil']);
	});

	it('pour Permis, la source qui couvre tout le canton, partout', () => {
		expect(noms(couchePermis, LAUSANNE.bfs)).toEqual(['CAMAC']);
		expect(noms(couchePermis, BUSSIGNY.bfs)).toEqual(['CAMAC']);
	});

	it('écarte une source dont la Couverture ne compte pas la commune', () => {
		const source = (id: string, couverture: Source['couverture']): Source => ({
			...SOURCES[0],
			id,
			nom_court: id,
			couverture
		});
		const sources = [source('a', { communes: [5590], mode: 'scrape' }), source('b', { communes: 'canton', mode: 'api' })];
		const couche = { ...couchePermis, sources: ['a', 'b'] };

		expect(noms(couche, 5590, sources)).toEqual(['a', 'b']);
		expect(noms(couche, 5586, sources)).toEqual(['b']);
	});
});

describe('« Non couvert » en tête de l’onglet', () => {
	it('dit ce qui manque, dans les mots de la couche', () => {
		expect(messageNonCouvert(coucheConseils, BUSSIGNY)).toBe(
			'OpenParlData ne donne pas le conseil communal de Bussigny.'
		);
	});

	it('sinon, que la couche n’a pas de source pour la commune', () => {
		expect(messageNonCouvert(couchePermis, BUSSIGNY)).toBe('la couche Permis n’a pas de source pour Bussigny.');
	});
});
