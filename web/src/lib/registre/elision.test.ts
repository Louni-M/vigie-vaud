import { describe, expect, it } from 'vitest';
import { deNom } from './elision.js';

describe('complément « de » d’une commune', () => {
	it.each([
		['Pully', 'de Pully'],
		['Yverdon-les-Bains', 'd’Yverdon-les-Bains'],
		['Echallens', 'd’Echallens'],
		['Échallens', 'd’Échallens'],
		['Ollon', 'd’Ollon'],
		['Aigle', 'd’Aigle'],
		['Hautemorges', 'de Hautemorges'],
		['Le Chenit', 'du Chenit'],
		['Le Mont-sur-Lausanne', 'du Mont-sur-Lausanne'],
		['Les Clées', 'des Clées'],
		['La Sarraz', 'de La Sarraz'],
		["L'Abbaye", "de L'Abbaye"]
	])('%s → %s', (nom, attendu) => {
		expect(deNom(nom)).toBe(attendu);
	});
});
