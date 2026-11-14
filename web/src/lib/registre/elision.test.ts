import { describe, expect, it } from 'vitest';
import casElision from '../../../../cas-partages/elision.json';
import { deNom } from './elision.js';

describe('complément « de » d’une commune', () => {
	// Les cas de `cas-partages/elision.json`, que lit aussi `de_nom` du cron : il nomme les sources communales de son
	// brouillon (« Site du Mont-sur-Lausanne »).
	it.each(casElision.cas)('$nom → $de', ({ nom, de }) => {
		expect(deNom(nom)).toBe(de);
	});
});
