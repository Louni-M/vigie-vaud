import { describe, expect, it } from 'vitest';
import { apercuElement } from './apercu.js';
import { objet, seance } from '#tests/faux-conseils.js';

describe('aperçu d’un Objet ou d’une Séance sur téléphone', () => {
	it('donne la sorte, le conseil et la date d’un Objet, puis son titre', () => {
		const motion = objet({
			numero: 'POS25/115',
			type: 'Motion',
			depose: '2026-09-29',
			titre: 'Pour des pistes cyclables continues à la Pontaise'
		});
		expect(apercuElement('5586/POS25-115', motion)).toEqual({
			meta: 'Motion · Conseil communal de Lausanne · 29 sept.',
			titre: 'Pour des pistes cyclables continues à la Pontaise'
		});
	});

	it('date un Objet sans date de dépôt par sa dernière étape', () => {
		const sansDepot = objet({
			depose: null,
			etapes: [
				{ date: '2026-09-01', libelle: 'Dépôt' },
				{ date: '2026-10-06', libelle: 'Renvoi en commission' }
			]
		});
		expect(apercuElement('vd/26_INT_140', sansDepot).meta).toBe('Interpellation · Grand Conseil · 6 oct.');
	});

	it('donne « Séance », le conseil et la date d’une Séance, puis son nom composé', () => {
		expect(apercuElement('vd/2026-10-06', seance())).toEqual({
			meta: 'Séance · Grand Conseil · 6 oct.',
			titre: 'Séance du mardi 6 octobre 2026'
		});
	});

	it('se contente de la clé quand l’élément n’a pas pu être lu', () => {
		expect(apercuElement('5586/POS25-115', null)).toEqual({
			meta: 'Conseil communal de Lausanne',
			titre: 'Objet POS25/115'
		});
		expect(apercuElement('vd/2026-10-06', null)).toEqual({
			meta: 'Grand Conseil',
			titre: 'Séance du 6 octobre 2026'
		});
	});
});
