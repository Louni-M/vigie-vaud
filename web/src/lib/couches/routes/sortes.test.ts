import { describe, expect, it } from 'vitest';
import type { EtatRestriction } from './etats.js';
import { plusContraignante, type Sorte } from './sortes.js';

/** Une restriction sous le clic, telle que la carte la lit dans ses calques. */
const restriction = (id: number, sorte: Sorte, etat: EtatRestriction = 'en_cours') => ({ id, sorte, etat });

describe('priorité au clic sur des restrictions superposées', () => {
	it.each<[string, Sorte[], Sorte]>([
		['la fermeture avant sa déviation', ['deviation', 'fermeture'], 'fermeture'],
		['les feux avant une restriction particulière', ['particuliere', 'feux'], 'feux'],
		['la fermeture avant les feux', ['feux', 'fermeture'], 'fermeture'],
		['une restriction particulière avant une autre sorte', ['autre', 'particuliere'], 'particuliere'],
		['une autre sorte avant une déviation', ['deviation', 'autre'], 'autre'],
		['toutes les sortes : la fermeture', ['deviation', 'autre', 'particuliere', 'feux', 'fermeture'], 'fermeture'],
		['une déviation seule', ['deviation'], 'deviation']
	])('ouvre %s', (_, sortes, attendue) => {
		expect(plusContraignante(sortes.map((s, i) => restriction(i + 1, s)))?.sorte).toBe(attendue);
	});

	it('à sorte égale, ouvre l’en cours, dessinée au-dessus de l’à venir', () => {
		expect(plusContraignante([restriction(1, 'fermeture', 'a_venir'), restriction(2, 'fermeture')])?.id).toBe(2);
	});

	it('à sorte et état égaux, ouvre toujours la même : le plus petit OBJECTID', () => {
		expect(plusContraignante([restriction(7, 'feux'), restriction(3, 'feux')])?.id).toBe(3);
	});

	it('n’ouvre rien sans restriction sous le clic', () => {
		expect(plusContraignante([])).toBeNull();
	});
});
