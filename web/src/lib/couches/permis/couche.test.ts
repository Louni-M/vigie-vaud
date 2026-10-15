import { describe, expect, it } from 'vitest';
import { couchePermis } from './index.js';

describe('couche Permis', () => {
	it('titre un dossier ouvert par son n° et sa commune', () => {
		expect(couchePermis.titre?.('248845', 'Lutry')).toBe('Dossier n° 248845 – Lutry – Vigie Vaud');
	});
});
