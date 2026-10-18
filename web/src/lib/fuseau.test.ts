import { describe, expect, it } from 'vitest';

/*
 * Toute la suite tourne à l'heure de Lausanne (vite.config.ts), quel que soit le fuseau de la machine : les heures
 * de la DGMR, codées comme de l'UTC, doivent être lues par leurs composantes UTC. Une lecture locale fautive décale
 * alors de 1 h en hiver et de 2 h en été, et échoue ; en UTC (la CI), elle passerait.
 */
describe('fuseau de la suite de tests', () => {
	it('est celui de Lausanne : UTC+1 en hiver, UTC+2 en été', () => {
		expect(new Date(Date.UTC(2026, 0, 15, 12)).getTimezoneOffset()).toBe(-60);
		expect(new Date(Date.UTC(2026, 6, 15, 12)).getTimezoneOffset()).toBe(-120);
	});
});
