import { describe, expect, it } from 'vitest';
import { grisageApres } from './grisage-mobile.js';

describe('grisage sur téléphone, montré par « Voir sur la carte »', () => {
	it('commence sans grisage, et « Voir sur la carte » grise selon la couche de son volet', () => {
		expect(grisageApres(null, { voir: 'conseils' })).toBe('conseils');
	});
	it('s’efface à la croix de la pastille', () => {
		expect(grisageApres('conseils', { effacer: true })).toBeNull();
	});
	it('passe à l’autre couche quand on choisit « Voir sur la carte » dans son volet', () => {
		expect(grisageApres('conseils', { voir: 'permis' })).toBe('permis');
	});
	it('s’efface quand on désactive la couche', () => {
		expect(grisageApres('conseils', { actives: ['permis', 'hotels-de-ville'] })).toBeNull();
	});
	it('reste quand on active ou désactive une autre couche', () => {
		expect(grisageApres('conseils', { actives: ['conseils', 'hotels-de-ville'] })).toBe('conseils');
		expect(grisageApres('conseils', { actives: ['permis', 'conseils', 'hotels-de-ville'] })).toBe('conseils');
	});
	it('ne revient pas quand on réactive la couche après l’avoir désactivée', () => {
		const desactivee = grisageApres('conseils', { actives: ['permis'] });
		expect(grisageApres(desactivee, { actives: ['permis', 'conseils'] })).toBeNull();
	});
});
