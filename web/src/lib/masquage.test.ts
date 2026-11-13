import { describe, expect, it } from 'vitest';
import casMasquage from '../../../cas-partages/masquage.json';
import { masquerNoms } from './masquage.js';

// Les cas de `cas-partages/masquage.json`, que lit aussi `masquer` du cron : il masque les titres des conseils comme le
// site masque les descriptions des permis. `null` : le titre ne change pas.
describe('masquerNoms, mêmes cas que le cron', () => {
	it.each(casMasquage.cas)('$titre', ({ titre, attendu }) => {
		expect(masquerNoms(titre)).toBe(attendu ?? titre);
	});

	// Au site seulement : le cron masque un nom après « hoirie » dans les titres des conseils (ADR 0007).
	it('voit une entité après « Hoirie »', () => {
		const titre = 'Rénovation pour le compte de l’Hoirie Favre';
		expect(masquerNoms(titre)).toBe(titre);
	});
});
