import { describe, expect, it } from 'vitest';
import { commune } from '#tests/faux-canton.js';
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

describe('recherche d’un Objet par son numéro', () => {
	const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
	const cherche = (texte: string) => coucheConseils.chercher?.(texte, [LAUSANNE]) ?? [];

	it('reconnaît un numéro du Grand Conseil et le donne à sa forme canonique', () => {
		expect(cherche('26 int 140')).toEqual([
			{ couche: 'conseils', element: 'vd/26_INT_140', libelle: 'Objet 26_INT_140 · Grand Conseil' }
		]);
	});

	it.each([
		['26-INT-140', 'vd/26_INT_140', 'Objet 26_INT_140 · Grand Conseil'],
		['26_int_0140', 'vd/26_INT_140', 'Objet 26_INT_140 · Grand Conseil'],
		['  26INT140 ', 'vd/26_INT_140', 'Objet 26_INT_140 · Grand Conseil'],
		['25 hqu 7', 'vd/25_HQU_7', 'Objet 25_HQU_7 · Grand Conseil'],
		['int 26/56', '5586/INT26-056', 'Objet INT26/056 · Lausanne'],
		['POS25/115', '5586/POS25-115', 'Objet POS25/115 · Lausanne'],
		['prea 20 12', '5586/PREA20-012', 'Objet PREA20/012 · Lausanne'],
		['Q22-3', '5586/Q22-003', 'Objet Q22/003 · Lausanne'],
		['comc24014', '5586/COMC24-014', 'Objet COMC24/014 · Lausanne']
	])('« %s » : %s', (texte, element, libelle) => {
		expect(cherche(texte)).toEqual([{ couche: 'conseils', element, libelle }]);
	});

	it('garde tel quel un ancien numéro du Grand Conseil, dont les zéros de tête varient', () => {
		expect(cherche('07 int 004').map((r) => r.element)).toEqual(['vd/07_INT_004']);
		expect(cherche('8_LEG_124').map((r) => r.element)).toEqual(['vd/8_LEG_124']);
	});

	it.each([
		'25 rue 12',
		'26 abc 140',
		'26 PREA 140',
		'abc 26/56',
		'HQU 26/56',
		'26 int',
		'int 26',
		'26 int 0',
		'2026 int 140',
		'Pully 26 int 140',
		'248845',
		'gr'
	])('« %s » n’est pas un numéro d’Objet', (texte) => {
		expect(cherche(texte)).toEqual([]);
	});
});
