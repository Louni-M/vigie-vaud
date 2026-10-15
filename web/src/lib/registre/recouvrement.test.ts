import { describe, expect, it } from 'vitest';
import { calquesAuDessus } from './recouvrement.js';

// Ordre de dessin de la carte : le fond, puis chaque couche range ses calques sous son ancre, puis le repère.
const ORDRE = [
	'fond',
	'permis-historique',
	'permis-actifs',
	'couche:permis',
	'hotels-de-ville-ouvert',
	'hotels-de-ville',
	'couche:hotels-de-ville',
	'repere'
];

describe('calques qui recouvrent une couche', () => {
	it('sont ceux des couches dessinées au-dessus, sans le repère du socle', () => {
		expect(calquesAuDessus(ORDRE, 'couche:permis')).toEqual(['hotels-de-ville-ouvert', 'hotels-de-ville']);
	});

	it('manquent pour la couche dessinée en dernier', () => {
		expect(calquesAuDessus(ORDRE, 'couche:hotels-de-ville')).toEqual([]);
	});
});
