import { describe, expect, it } from 'vitest';
import { LARGEUR_UTILE, margeDuPanneau } from './marge.js';

describe('marge du panneau', () => {
	it('est le bord du panneau quand il reste assez de carte à côté de lui', () => {
		expect(margeDuPanneau(1280, 370)).toBe(370);
		expect(margeDuPanneau(370 + LARGEUR_UTILE, 370)).toBe(370);
	});

	it('est nulle quand il en reste trop peu (tablette, fiche ouverte)', () => {
		expect(margeDuPanneau(480, 370)).toBe(0);
		expect(margeDuPanneau(370 + LARGEUR_UTILE - 1, 370)).toBe(0);
	});
});
