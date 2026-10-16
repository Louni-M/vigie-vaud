import { describe, expect, it } from 'vitest';
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import { reconnaitreNumero } from './numeros.js';

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
});
