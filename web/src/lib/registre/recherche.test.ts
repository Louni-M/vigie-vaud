import { describe, expect, it } from 'vitest';
import { COUCHES } from './couches.js';
import { resultatsCouches } from './recherche.js';

const GRAND_CONSEIL = { type: 'fiche', nomCouche: 'Conseils', libelle: 'Grand Conseil', fiche: 'grand-conseil' };

describe('recherche des fiches propres', () => {
	it.each(['gr', 'Grand', 'grand conseil', 'GRAND-CONSEIL', 'pa', 'parl', 'Parlement', 'GC', 'gc', ' gc '])(
		'« %s » propose le Grand Conseil',
		(texte) => {
			expect(resultatsCouches(COUCHES, texte)).toEqual([GRAND_CONSEIL]);
		}
	);

	it('ignore les accents et la casse', () => {
		expect(resultatsCouches(COUCHES, 'GRÂND')).toEqual([GRAND_CONSEIL]);
		expect(resultatsCouches(COUCHES, 'pàrlé')).toEqual([GRAND_CONSEIL]);
	});

	it.each(['g', 'p', 'gcx', 'conseil', 'parlements', 'grand conseil vaudois', ''])('« %s » ne le propose pas', (texte) => {
		expect(resultatsCouches(COUCHES, texte)).toEqual([]);
	});
});

describe('ordre des résultats des couches', () => {
	it('donne les fiches propres avant les éléments des couches', () => {
		const pa = resultatsCouches(COUCHES, 'pa');
		expect(pa.map((r) => r.type)).toEqual(['fiche']);
		const numero = resultatsCouches(COUCHES, '26 int 140');
		expect(numero).toEqual([
			{
				type: 'element',
				nomCouche: 'Conseils',
				libelle: 'Objet 26_INT_140 · Grand Conseil',
				couche: 'conseils',
				element: 'vd/26_INT_140'
			}
		]);
	});
});
