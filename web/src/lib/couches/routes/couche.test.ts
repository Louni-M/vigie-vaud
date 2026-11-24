import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { COUCHES } from '#lib/registre/couches.js';
import { teteCommune } from '#lib/registre/tete.js';
import { clesEnDouble, ecrireUrl, lireUrl } from '#lib/registre/url.js';
import { commune } from '#tests/faux-canton.js';
import { fauxDgmr, restriction } from '#tests/faux-dgmr.js';
import { coucheRoutes, FILTRES_INITIAUX } from './index.js';
import type { Filtres } from './volet.js';
// Importé dès la collecte, hors du délai des tests : la première transformation du module de données par Vite, qui
// prend des secondes sur une machine chargée, est faite ; le module neuf de chaque test n'est plus qu'évalué.
import './donnees.svelte.js';

// Le module de données refuse d'interroger la DGMR ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

describe('couche Routes au registre', () => {
	it('est inscrite après Conseils et avant Hôtels de ville, dessinée au-dessus de tout', () => {
		expect(COUCHES.map((c) => c.id)).toEqual(['permis', 'conseils', 'routes', 'hotels-de-ville']);
	});

	it('nomme les restrictions de circulation dans la description de chaque commune, sans nombre', () => {
		const lutry = commune(5606, 'Lutry', [6.7, 46.49, 6.75, 46.52]);
		expect(teteCommune(lutry, COUCHES).description).toContain('les restrictions de circulation en cours et à venir');
	});
});

describe('adresse d’une restriction ouverte', () => {
	const ouverte = { couche: 'routes', element: '5031' };

	it('fait l’aller-retour par `?r=<OBJECTID>`', () => {
		// Ouverte depuis sa rubrique : l'adresse n'a pas à la nommer.
		const etat = { ...lireUrl(COUCHES, new URLSearchParams()), ouvert: ouverte, panneau: 'routes' };

		expect(ecrireUrl(COUCHES, etat)).toBe('?r=5031');
		expect(lireUrl(COUCHES, new URLSearchParams('r=5031')).ouvert).toEqual(ouverte);
	});

	it('garde l’élément ouvert à côté des puces du volet', () => {
		// Ouverte depuis sa rubrique : l'adresse n'a pas à la nommer.
		const etat = { ...lireUrl(COUCHES, new URLSearchParams()), ouvert: ouverte, panneau: 'routes' };
		const requete = ecrireUrl(COUCHES, {
			...etat,
			parametres: { ...etat.parametres, routes: { ...FILTRES_INITIAUX, sortes: ['feux'], etats: ['a_venir'] } }
		});

		expect(requete).toBe('?r=5031&sortes=feux&etats=a_venir');
		expect(lireUrl(COUCHES, new URLSearchParams(requete.slice(1))).ouvert).toEqual(ouverte);
	});
});

describe('puces du volet Routes dans l’adresse', () => {
	const codec = coucheRoutes.codec!;
	const lire = (requete: string) => codec.lire(new URLSearchParams(requete));

	it('allume toutes les puces sans rien écrire par défaut', () => {
		expect(lire('')).toEqual(FILTRES_INITIAUX);
		expect(codec.ecrire(FILTRES_INITIAUX)).toEqual([]);
		expect(ecrireUrl(COUCHES, lireUrl(COUCHES, new URLSearchParams()))).toBe('');
	});

	it('n’écrit que les puces allumées, dans l’ordre de la légende, et seulement si l’une est éteinte', () => {
		expect(codec.ecrire({ ...FILTRES_INITIAUX, sortes: ['feux', 'fermeture'] })).toEqual([['sortes', 'fermeture,feux']]);
		expect(codec.ecrire({ ...FILTRES_INITIAUX, etats: ['en_cours'] })).toEqual([['etats', 'en_cours']]);
		expect(codec.ecrire({ ...FILTRES_INITIAUX, sortes: [], etats: [] })).toEqual([
			['sortes', ''],
			['etats', '']
		]);
	});

	it.each<[string, Filtres]>([
		['sortes=feux,fermeture', { ...FILTRES_INITIAUX, sortes: ['fermeture', 'feux'] }],
		['etats=a_venir', { ...FILTRES_INITIAUX, etats: ['a_venir'] }],
		['sortes=&etats=', { ...FILTRES_INITIAUX, sortes: [], etats: [] }],
		['sortes=feux,inconnue&etats=hier', { ...FILTRES_INITIAUX, sortes: ['feux'], etats: [] }],
		['ordre=recent', { ...FILTRES_INITIAUX, ordre: 'recent' }],
		['ordre=inconnu', FILTRES_INITIAUX]
	])('lit « %s »', (requete, attendu) => {
		expect(lire(requete)).toEqual(attendu);
	});

	it('fait l’aller-retour', () => {
		for (const f of [
			FILTRES_INITIAUX,
			{ sortes: ['deviation', 'autre'], etats: ['a_venir'], ordre: 'recent' },
			{ sortes: [], etats: [], ordre: 'echeance' }
		] as Filtres[])
			expect(lire(new URLSearchParams(codec.ecrire(f)).toString())).toEqual(f);
	});

	it('ne prend aucune clé déjà prise', () => {
		expect(clesEnDouble(COUCHES)).toEqual([]);
	});
});

describe('messages et titres d’une restriction', () => {
	it('dit qu’une restriction introuvable n’est plus publiée, sans son numéro', () => {
		expect(coucheRoutes.introuvable?.('5031')).toBe(
			'Cette restriction de circulation n’est plus publiée par la DGMR : elle a pu être levée ou modifiée.'
		);
	});

	it('nomme la restriction ouverte dans le fil d’Ariane, sans numéro', () => {
		expect(coucheRoutes.libelle?.('5031')).toBe('Restriction de circulation');
	});
});

describe('localiser une restriction', () => {
	// Le module de données et les limites des communes sont gardés pour la visite : un module neuf à chaque cas.
	beforeEach(() => vi.resetModules());
	afterEach(() => vi.unstubAllGlobals());
	const localiser = async (element: string) => (await import('./index.js')).coucheRoutes.localiser!(element);

	it('l’ouvre dans ses communes, de la plus longue à la plus courte, au milieu de son tracé', async () => {
		// 0,01° chez Pully, 0,03° chez Lutry.
		const deviation = restriction(5031, { RESTRICTION: 'Déviation' }, [[6.69, 46.5], [6.73, 46.5]]);
		vi.stubGlobal('fetch', fauxDgmr({ aVenir: [deviation] }).fetch);

		expect(await localiser('5031')).toEqual({
			fiches: [{ commune: 'lutry' }, { commune: 'pully' }],
			position: [expect.closeTo(6.71, 6), expect.closeTo(46.5, 6)]
		});
	});

	it('ne trouve pas une restriction que la DGMR ne publie plus, ni un élément qui n’est pas un OBJECTID', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1)] });
		vi.stubGlobal('fetch', dgmr.fetch);

		expect(await localiser('5031')).toBeNull();
		expect(await localiser('A9')).toBeNull();
		expect(dgmr.requetes.map((q) => q.where)).toEqual(['OBJECTID IN (5031)', 'OBJECTID IN (5031)']);
	});

	it('rejette quand la DGMR est injoignable', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1)] });
		dgmr.horsLigne(true);
		vi.stubGlobal('fetch', dgmr.fetch);

		await expect(localiser('1')).rejects.toThrow();
	});
});

