import { describe, expect, it } from 'vitest';
import { coucheConseils } from './index.js';

describe('couche Conseils', () => {
	it.each([
		['5586/POS25-115', 'Lausanne', 'Objet POS25/115 – Lausanne – Vigie Vaud'],
		['vd/26_INT_140', 'Grand Conseil', 'Objet 26_INT_140 – Grand Conseil – Vigie Vaud'],
		['vd/26_INT_140', 'Pully', 'Objet 26_INT_140 – Pully – Vigie Vaud'],
		['5586/2026-10-06', 'Lausanne', 'Séance du 6 octobre 2026 – Lausanne – Vigie Vaud'],
		['5938/2026-10-01', 'Yverdon-les-Bains', 'Séance du 1er octobre 2026 – Yverdon-les-Bains – Vigie Vaud']
	])('titre l’élément %s, ouvert dans la fiche %s, par sa clé seule', (cle, fiche, attendu) => {
		expect(coucheConseils.titre?.(cle, fiche)).toBe(attendu);
	});
});

describe('fil d’Ariane de l’élément ouvert', () => {
	it.each([
		['5586/POS25-115', 'POS25/115'],
		['vd/26_INT_140', '26_INT_140'],
		['5586/2026-10-06', 'Séance du 6 octobre 2026']
	])('%s', (cle, attendu) => {
		expect(coucheConseils.libelle?.(cle)).toBe(attendu);
	});
});

describe('élément introuvable', () => {
	it.each([
		['vd/26_INT_999', 'Aucun objet n° 26_INT_999 au Grand Conseil dans les données d’OpenParlData.'],
		['5586/POS25-999', 'Aucun objet n° POS25/999 au Conseil communal de Lausanne dans les données d’OpenParlData.'],
		[
			'5586/2026-10-07',
			'Aucune séance le 7 octobre 2026 au Conseil communal de Lausanne dans les données d’OpenParlData.'
		],
		['9999/POS25-115', 'Aucun objet n° 9999/POS25-115 dans les données d’OpenParlData.'],
		['n’importe quoi', 'Aucun objet n° n’importe quoi dans les données d’OpenParlData.']
	])('%s', (cle, attendu) => {
		expect(coucheConseils.introuvable?.(cle)).toBe(attendu);
	});
});
