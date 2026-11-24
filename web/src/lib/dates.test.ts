import { describe, expect, it } from 'vitest';
import { jourDe } from './dates.js';

describe('jour d’un instant à Lausanne', () => {
	it('suit l’heure d’été de Zurich : minuit à Lausanne est 22 h UTC', () => {
		expect(jourDe(new Date('2026-07-14T21:59:59Z'))).toBe('2026-07-14');
		expect(jourDe(new Date('2026-07-14T22:00:00Z'))).toBe('2026-07-15');
	});

	it('suit l’heure d’hiver de Zurich : minuit à Lausanne est 23 h UTC', () => {
		expect(jourDe(new Date('2026-12-31T22:59:59Z'))).toBe('2026-12-31');
		expect(jourDe(new Date('2026-12-31T23:00:00Z'))).toBe('2027-01-01');
	});
});
