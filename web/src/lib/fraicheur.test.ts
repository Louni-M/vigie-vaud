import { describe, expect, it } from 'vitest';
import { libelleBadge } from './fraicheur.js';

/** Horloge fixée : 15 octobre 2026, 10 h UTC. */
const maintenant = new Date('2026-10-15T10:00:00Z');
const ilYa = (minutes: number) => new Date(maintenant.getTime() - minutes * 60_000);

const camac = { fraicheur: 'requete', nom_court: 'CAMAC' } as const;
const dgmr = { fraicheur: 'donnee', nom_court: 'DGMR' } as const;
const ucv = { fraicheur: 'millesime', nom_court: 'UCV' } as const;

describe('libellé du badge de fraîcheur', () => {
	it('donne l’heure de la requête pour une source consultée en direct', () => {
		expect(libelleBadge(camac, { derniere: ilYa(2), erreur: null }, maintenant)).toBe('consulté il y a 2 min · CAMAC');
	});

	it('donne l’âge de la donnée elle-même', () => {
		expect(libelleBadge(dgmr, { derniere: ilYa(4), erreur: null }, maintenant)).toBe('il y a 4 min · DGMR');
	});

	it('donne l’édition d’une source préparée', () => {
		expect(libelleBadge(ucv, { derniere: 2025, erreur: null }, maintenant)).toBe('édition 2025 · UCV');
	});

	it('passe des minutes aux heures puis aux jours', () => {
		const libelle = (minutes: number) => libelleBadge(dgmr, { derniere: ilYa(minutes), erreur: null }, maintenant);
		expect(libelle(0.5)).toBe('à l’instant · DGMR');
		expect(libelle(59)).toBe('il y a 59 min · DGMR');
		expect(libelle(60)).toBe('il y a 1 h · DGMR');
		expect(libelle(23 * 60 + 59)).toBe('il y a 23 h · DGMR');
		expect(libelle(3 * 24 * 60)).toBe('il y a 3 j · DGMR');
	});

	it('dit qu’une source n’a pas encore été obtenue', () => {
		expect(libelleBadge(camac, { derniere: null, erreur: null }, maintenant)).toBe('pas encore consulté · CAMAC');
		expect(libelleBadge(dgmr, { derniere: null, erreur: null }, maintenant)).toBe('pas encore chargé · DGMR');
		expect(libelleBadge(ucv, { derniere: null, erreur: null }, maintenant)).toBe('édition inconnue · UCV');
	});

	it('passe en erreur, hors ligne ou service indisponible, même après un succès', () => {
		expect(libelleBadge(camac, { derniere: ilYa(2), erreur: 'hors_ligne' }, maintenant)).toBe('hors ligne · CAMAC');
		expect(libelleBadge(camac, { derniere: null, erreur: 'indisponible' }, maintenant)).toBe(
			'service indisponible · CAMAC'
		);
	});
});
