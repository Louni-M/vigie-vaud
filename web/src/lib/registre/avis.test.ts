import { describe, expect, it } from 'vitest';
import { avisIntrouvable, avisNonCherche } from './avis.js';
import { COUCHES } from './couches.js';
import type { CoucheInscrite } from './types.js';

/** Une couche future qui déclare son message de source injoignable. */
const ROUTES: CoucheInscrite = {
	id: 'routes',
	nom: 'Routes',
	sources: [],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'R', couleur: '#c92a2a' },
	cleElement: 'r',
	localiser: () => Promise.reject(new Error('injoignable')),
	introuvable: () => 'Cette restriction de circulation n’est plus publiée par la DGMR.',
	nonCherche: () =>
		'La restriction de circulation n’a pas pu être cherchée : vérifiez votre connexion, puis réessayez.',
	composants: { Carte: () => Promise.reject(new Error()), Onglet: () => Promise.reject(new Error()) }
};
const AVEC_ROUTES = [...COUCHES, ROUTES];

describe('élément que sa couche n’a pas pu chercher', () => {
	it('affiche le message de la couche quand elle le déclare', () => {
		expect(avisNonCherche(AVEC_ROUTES, { couche: 'routes', element: '5031' })).toBe(
			'La restriction de circulation n’a pas pu être cherchée : vérifiez votre connexion, puis réessayez.'
		);
	});

	it.each([
		['permis', '248845'],
		['conseils', 'vd/26_INT_140']
	])('garde le message commun pour %s, qui ne le déclare pas', (couche, element) => {
		expect(avisNonCherche(AVEC_ROUTES, { couche, element })).toBe(
			`Le n° ${element} n’a pas pu être cherché : vérifiez votre connexion, puis réessayez.`
		);
	});
});

describe('élément introuvable', () => {
	const LUTRY = { commune: 'lutry' };

	it.each([
		['permis', '999999', 'Aucun dossier n° 999999.'],
		[
			'conseils',
			'5586/POS25-999',
			'Aucun objet n° POS25/999 au Conseil communal de Lausanne dans les données d’OpenParlData.'
		],
		['routes', '5031', 'Cette restriction de circulation n’est plus publiée par la DGMR.']
	])('ouvre la fiche commune du chemin sur l’onglet %s, avec le message de la couche', (couche, element, avis) => {
		expect(avisIntrouvable(AVEC_ROUTES, { couche, element }, LUTRY)).toEqual({ avis, onglet: couche });
	});

	it('sans fiche dans le chemin, il n’y a que le message', () => {
		expect(avisIntrouvable(AVEC_ROUTES, { couche: 'permis', element: '999999' }, null)).toEqual({
			avis: 'Aucun dossier n° 999999.',
			onglet: null
		});
	});

	it('dans une fiche propre, qui n’a que l’onglet de sa couche, il n’y a que le message', () => {
		expect(avisIntrouvable(AVEC_ROUTES, { couche: 'permis', element: '999999' }, { fiche: 'grand-conseil' })).toEqual(
			{ avis: 'Aucun dossier n° 999999.', onglet: null }
		);
	});

	it('une couche sans onglet laisse la fiche sur l’onglet choisi', () => {
		const sansOnglet = { ...ROUTES, id: 'sans-onglet', composants: { Carte: ROUTES.composants.Carte } };
		expect(avisIntrouvable([...COUCHES, sansOnglet], { couche: 'sans-onglet', element: '1' }, LUTRY).onglet).toBeNull();
	});
});
