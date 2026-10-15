import { describe, expect, it } from 'vitest';
import { cheminACompter, mesureAudience } from './audience.js';

const url = (chemin: string) => new URL(chemin, 'https://vigie.exemple.ch');

describe('mesure d’audience activée à la construction', () => {
	it('est désactivée sans code GoatCounter', () => {
		expect(mesureAudience(undefined)).toBeNull();
		expect(mesureAudience('')).toBeNull();
		expect(mesureAudience('  ')).toBeNull();
	});

	it('donne l’adresse de comptage et le tableau de bord public du code', () => {
		expect(mesureAudience('vigievaud')).toEqual({
			compteur: 'https://vigievaud.goatcounter.com/count',
			tableau: 'https://vigievaud.goatcounter.com'
		});
	});
});

describe('chemin compté après une navigation', () => {
	it('compte l’arrivée sur le site par son chemin seul, sans les paramètres', () => {
		expect(cheminACompter(null, url('/commune/pully?d=2024-123&centre=46.5,6.6'))).toBe('/commune/pully');
		expect(cheminACompter(null, url('/?centre=46.5,6.6&zoom=14#carte'))).toBe('/');
	});

	it('compte un changement de page', () => {
		expect(cheminACompter(url('/?centre=46.5,6.6'), url('/commune/pully?d=2024-123'))).toBe('/commune/pully');
		expect(cheminACompter(url('/commune/pully'), url('/protection-des-donnees'))).toBe('/protection-des-donnees');
	});

	it('ne compte pas un déplacement de la carte ni l’ouverture d’un dossier sur la même page', () => {
		expect(cheminACompter(url('/commune/pully'), url('/commune/pully?d=2024-123'))).toBeNull();
		expect(cheminACompter(url('/?centre=46.5,6.6'), url('/?centre=46.6,6.7'))).toBeNull();
	});

	it('garde le chemin de base du site', () => {
		expect(cheminACompter(null, url('/vigie-vaud/commune/pully?d=1'))).toBe('/vigie-vaud/commune/pully');
	});

	it('ne compte rien quand la navigation quitte le site', () => {
		expect(cheminACompter(url('/'), null)).toBeNull();
	});
});
