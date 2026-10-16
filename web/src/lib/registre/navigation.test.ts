import { describe, expect, it } from 'vitest';
import { corrigerChemin, fermeture, mouvement } from './navigation.js';
import type { Ouvert } from './types.js';

const VUE = { lat: 46.5, lon: 6.6, zoom: 13 };
const DOSSIER = { couche: 'permis', element: '248845' };
const AUTRE = { couche: 'permis', element: '250001' };

/** Ce que reflétait l'adresse précédente. */
const avant = (commune: string | null, ouvert: Ouvert | null = null) => ({ commune, ouvert });
const DEPART = avant(null);

describe('mouvement de la carte quand l’adresse change', () => {
	describe('à l’arrivée sur le site', () => {
		it('rétablit la vue partagée, qui l’emporte sur la commune et sur l’élément', () => {
			expect(mouvement(DEPART, { commune: 'pully', vue: VUE, ouvert: null }, true)).toEqual({ aller: VUE });
			expect(mouvement(DEPART, { commune: 'lutry', vue: VUE, ouvert: DOSSIER }, true)).toEqual({ aller: VUE });
		});
		it('cadre la commune de l’adresse quand il n’y a pas de vue', () => {
			expect(mouvement(DEPART, { commune: 'pully', vue: null, ouvert: null }, true)).toEqual({ cadrer: 'pully' });
		});
		it('montre l’élément de l’adresse quand il n’y a pas de vue', () => {
			expect(mouvement(DEPART, { commune: null, vue: null, ouvert: DOSSIER }, true)).toBe('element');
			expect(mouvement(DEPART, { commune: 'lutry', vue: null, ouvert: DOSSIER }, true)).toBe('element');
		});
		it('laisse la carte sur sa vue de départ à l’adresse nue', () => {
			expect(mouvement(DEPART, { commune: null, vue: null, ouvert: null }, true)).toBeNull();
		});
	});

	describe('pendant la navigation', () => {
		it('cadre la commune qu’on vient d’ouvrir', () => {
			expect(mouvement(DEPART, { commune: 'pully', vue: null, ouvert: null }, false)).toEqual({ cadrer: 'pully' });
			expect(mouvement(avant('lutry'), { commune: 'pully', vue: null, ouvert: null }, false)).toEqual({
				cadrer: 'pully'
			});
		});
		it('rétablit la vue de l’entrée d’historique retrouvée', () => {
			expect(mouvement(avant('pully'), { commune: 'lutry', vue: VUE, ouvert: null }, false)).toEqual({ aller: VUE });
			expect(mouvement(avant('pully'), { commune: null, vue: VUE, ouvert: null }, false)).toEqual({ aller: VUE });
		});
		it('revient au canton à l’adresse nue « / »', () => {
			expect(mouvement(avant('pully'), { commune: null, vue: null, ouvert: null }, false)).toBe('canton');
			expect(mouvement(DEPART, { commune: null, vue: null, ouvert: null }, false)).toBe('canton');
		});
		it('ne bouge pas quand la commune reste la même', () => {
			expect(mouvement(avant('pully'), { commune: 'pully', vue: null, ouvert: null }, false)).toBeNull();
		});
		it('montre l’élément retrouvé par le précédent ou le suivant du navigateur', () => {
			expect(mouvement(avant('lutry'), { commune: 'lutry', vue: null, ouvert: DOSSIER }, false)).toBe('element');
			expect(mouvement(avant('lutry', AUTRE), { commune: 'lutry', vue: null, ouvert: DOSSIER }, false)).toBe(
				'element'
			);
		});
		it('ne bouge pas quand seul le chemin de l’élément ouvert est corrigé', () => {
			expect(mouvement(avant(null, DOSSIER), { commune: 'lutry', vue: null, ouvert: DOSSIER }, false)).toBeNull();
			expect(mouvement(avant('pully', DOSSIER), { commune: 'lutry', vue: null, ouvert: DOSSIER }, false)).toBeNull();
		});
		it('ne bouge pas quand on ferme l’élément pour revenir à l’onglet de sa commune, même vers une autre vue', () => {
			expect(mouvement(avant('lutry', DOSSIER), { commune: 'lutry', vue: null, ouvert: null }, false)).toBeNull();
			expect(mouvement(avant('lutry', DOSSIER), { commune: 'lutry', vue: VUE, ouvert: null }, false)).toBeNull();
		});
	});
});

describe('correction du chemin d’un élément ouvert', () => {
	const LUTRY = { commune: 'lutry' };
	const PULLY = { commune: 'pully' };
	const PROPRE = { fiche: 'propre' };

	it('mène à la fiche de l’élément depuis l’adresse nue ou une autre commune', () => {
		expect(corrigerChemin(null, { fiches: [LUTRY] })).toEqual(LUTRY);
		expect(corrigerChemin(PULLY, { fiches: [LUTRY] })).toEqual(LUTRY);
	});
	it('garde le chemin qui porte déjà la fiche de l’élément', () => {
		expect(corrigerChemin(LUTRY, { fiches: [LUTRY] })).toBeNull();
	});
	it('garde la fiche du chemin quand elle fait partie de celles de l’élément, même après la première', () => {
		expect(corrigerChemin(PULLY, { fiches: [LUTRY, PULLY, PROPRE] })).toBeNull();
		expect(corrigerChemin(PROPRE, { fiches: [LUTRY, PULLY, PROPRE] })).toBeNull();
	});
	it('mène à la première fiche de l’élément quand celle du chemin n’en fait pas partie', () => {
		expect(corrigerChemin({ commune: 'morges' }, { fiches: [LUTRY, PULLY, PROPRE] })).toEqual(LUTRY);
		expect(corrigerChemin(null, { fiches: [PROPRE, LUTRY] })).toEqual(PROPRE);
		expect(corrigerChemin({ commune: 'propre' }, { fiches: [LUTRY, PROPRE] })).toEqual(LUTRY);
	});
	it('retire l’élément que la couche ne trouve pas', () => {
		expect(corrigerChemin(PULLY, null)).toBe('retirer');
		expect(corrigerChemin(null, null)).toBe('retirer');
		expect(corrigerChemin(null, { fiches: [] })).toBe('retirer');
	});
});

describe('fermeture d’un élément', () => {
	const LUTRY = { commune: 'lutry' };
	const PROPRE = { fiche: 'propre' };

	it('revient en arrière quand l’application a ouvert l’élément depuis la même fiche', () => {
		expect(fermeture({ element: { depuis: { commune: 'lutry' } } }, LUTRY)).toBe('retour');
		expect(fermeture({ element: { depuis: { fiche: 'propre' } } }, PROPRE)).toBe('retour');
	});
	it('remplace l’adresse pour un élément ouvert par un lien direct', () => {
		expect(fermeture({}, LUTRY)).toBe('remplacer');
	});
	it('remplace l’adresse quand l’entrée précédente est une autre fiche ou la carte seule', () => {
		// Revenir en arrière quitterait la fiche où l'élément est ouvert au lieu de revenir à son onglet.
		expect(fermeture({ element: { depuis: { commune: 'pully' } } }, LUTRY)).toBe('remplacer');
		expect(fermeture({ element: { depuis: PROPRE } }, LUTRY)).toBe('remplacer');
		expect(fermeture({ element: { depuis: { commune: 'propre' } } }, PROPRE)).toBe('remplacer');
		expect(fermeture({ element: { depuis: null } }, LUTRY)).toBe('remplacer');
	});
});
