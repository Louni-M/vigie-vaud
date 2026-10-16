import { describe, expect, it } from 'vitest';
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import { lireCle, numeroObjet } from './cles.js';
import { cleObjet, reconnaitreNumero } from './numeros.js';

describe('numéros d’Objet et sources.json', () => {
	it('ne propose que les conseils dont une source donne les Objets', () => {
		const sansLausanne = SOURCES.filter((s) => s.id !== 'openparldata-5586');
		expect(reconnaitreNumero('int 26/56', sansLausanne)).toEqual([]);
		expect(reconnaitreNumero('26 int 140', sansLausanne).map((r) => r.cle)).toEqual(['vd/26_INT_140']);
		const seancesSeulement = SOURCES.map(
			(s): Source =>
				s.id === 'openparldata-5586' && s.conseil ? { ...s, conseil: { ...s.conseil, donne: ['seances'] } } : s
		);
		expect(reconnaitreNumero('int 26/56', seancesSeulement)).toEqual([]);
	});

	it('nomme le conseil par le nom court de sa source', () => {
		const renomme = SOURCES.map((s): Source => (s.id === 'openparldata-vd' ? { ...s, nom_court: 'Parlement' } : s));
		expect(reconnaitreNumero('26 int 140', renomme).map((r) => r.nom)).toEqual(['Parlement']);
		expect(reconnaitreNumero('int 26/56').map((r) => r.nom)).toEqual(['Conseil de Lausanne']);
	});

	it('ne cherche pas par numéro un conseil dont aucun préfixe n’est connu', () => {
		const yverdon = SOURCES.map(
			(s): Source => (s.id === 'openparldata-5938' && s.conseil ? { ...s, conseil: { ...s.conseil, donne: ['objets'] } } : s)
		);
		expect(reconnaitreNumero('int 26/56', yverdon).map((r) => r.cle)).toEqual(['5586/INT26-056']);
	});
});

// Les mêmes cas que `cle_objet` du cron (`pipeline/tests/test_import_conseils.py`), qui nomme le fichier d'archive
// que le site ouvre par cette clé : un cas ajouté d'un côté s'ajoute de l'autre.
describe('clé d’un Objet, comme le cron', () => {
	it.each([
		['vd', '26_INT_140', 'vd/26_INT_140'],
		['vd', '8_LEG_124', 'vd/8_LEG_124'],
		['vd', 'V 1.9.2026', 'vd/V_1.9.2026'],
		['vd', '  21_POS_3 ', 'vd/21_POS_3'],
		['5586', 'POS25/115', '5586/POS25-115'],
		['5586', 'INT26/056', '5586/INT26-056'],
		['5586', 'PR 25/3/bis', '5586/PR_25-3-bis'],
		['5586', 'INT \t 26/056', '5586/INT_26-056'],
		['5586', 'INT 26/056', '5586/INT_26-056']
	])('%s, « %s » → %s', (conseil, numero, cle) => {
		expect(cleObjet(conseil, numero)).toBe(cle);
	});

	it('rend le numéro tel quel depuis la clé pour les formes de FORMES_NUMEROS', () => {
		for (const [conseil, numero] of [
			['vd', '26_INT_140'],
			['vd', '8_LEG_124'],
			['5586', 'POS25/115'],
			['5586', 'PREA26/007']
		])
			expect(numeroObjet(lireCle(cleObjet(conseil, numero))!)).toBe(numero);
	});

	it('n’approche que les numéros hors de ces formes (l’Objet ouvert montre le sien)', () => {
		expect(numeroObjet(lireCle('vd/V_1.9.2026')!)).toBe('V_1.9.2026');
		expect(numeroObjet(lireCle('5586/PR_25-3-bis')!)).toBe('PR_25/3/bis');
	});
});
