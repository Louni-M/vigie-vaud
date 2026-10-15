import { describe, expect, it } from 'vitest';
import { mouvement } from './navigation.js';

const VUE = { lat: 46.5, lon: 6.6, zoom: 13 };
const DOSSIER = { couche: 'permis', element: '248845' };

describe('mouvement de la carte quand l’adresse change', () => {
	describe('à l’arrivée sur le site', () => {
		it('rétablit la vue partagée, qui l’emporte sur la commune', () => {
			expect(mouvement(null, { commune: 'pully', vue: VUE, ouvert: null }, true)).toEqual({ aller: VUE });
		});
		it('cadre la commune de l’adresse quand il n’y a pas de vue', () => {
			expect(mouvement(null, { commune: 'pully', vue: null, ouvert: null }, true)).toEqual({ cadrer: 'pully' });
		});
		it('laisse la carte sur sa vue de départ à l’adresse nue', () => {
			expect(mouvement(null, { commune: null, vue: null, ouvert: null }, true)).toBeNull();
		});
	});

	describe('pendant la navigation', () => {
		it('cadre la commune qu’on vient d’ouvrir', () => {
			expect(mouvement(null, { commune: 'pully', vue: null, ouvert: null }, false)).toEqual({ cadrer: 'pully' });
			expect(mouvement('lutry', { commune: 'pully', vue: null, ouvert: null }, false)).toEqual({ cadrer: 'pully' });
		});
		it('rétablit la vue de l’entrée d’historique retrouvée', () => {
			expect(mouvement('pully', { commune: 'lutry', vue: VUE, ouvert: null }, false)).toEqual({ aller: VUE });
			expect(mouvement('pully', { commune: null, vue: VUE, ouvert: null }, false)).toEqual({ aller: VUE });
		});
		it('revient au canton à l’adresse nue « / »', () => {
			expect(mouvement('pully', { commune: null, vue: null, ouvert: null }, false)).toBe('canton');
			expect(mouvement(null, { commune: null, vue: null, ouvert: null }, false)).toBe('canton');
		});
		it('ne bouge pas quand la commune reste la même', () => {
			expect(mouvement('pully', { commune: 'pully', vue: null, ouvert: null }, false)).toBeNull();
			expect(mouvement('pully', { commune: 'pully', vue: null, ouvert: DOSSIER }, false)).toBeNull();
		});
		it('ne bouge pas pour un élément ouvert sans commune', () => {
			expect(mouvement(null, { commune: null, vue: null, ouvert: DOSSIER }, false)).toBeNull();
		});
	});
});
