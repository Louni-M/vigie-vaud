import { describe, expect, it } from 'vitest';
import { MASQUE, masquerNoms } from '#lib/masquage.js';
import { apres, avant, PERMIS } from './exemples.js';

describe('Diagramme du masquage', () => {
	it('montre pour les permis ce que fait vraiment le masquage du site', () => {
		expect(masquerNoms(avant(PERMIS))).toBe(apres(PERMIS, MASQUE));
	});
});
