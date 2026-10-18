import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { COUCHES } from '#lib/registre/couches.js';
import { teteCommune } from '#lib/registre/tete.js';
import { ecrireUrl, lireUrl } from '#lib/registre/url.js';
import { calculerFil, depuisFil, type ContexteFil, type ReglagesFil, type SourceFil } from '#lib/fil/fil.js';
import { commune, LUTRY, PULLY } from '#tests/faux-canton.js';
import { fauxDgmr, heureLocale, restriction, type FauxDgmr } from '#tests/faux-dgmr.js';
import { coucheRoutes } from './index.js';

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
		const etat = { ...lireUrl(COUCHES, new URLSearchParams()), ouvert: ouverte };

		expect(ecrireUrl(COUCHES, etat)).toBe('?r=5031');
		expect(lireUrl(COUCHES, new URLSearchParams('r=5031')).ouvert).toEqual(ouverte);
	});

	it('ne met que l’élément ouvert dans l’adresse, sans réglage de la couche', () => {
		expect(coucheRoutes.codec).toBeUndefined();
		expect(coucheRoutes.cleElement).toBe('r');
	});
});

describe('messages et titres d’une restriction', () => {
	it('dit qu’une restriction introuvable n’est plus publiée, sans son numéro', () => {
		expect(coucheRoutes.introuvable?.('5031')).toBe(
			'Cette restriction de circulation n’est plus publiée par la DGMR : elle a pu être levée ou modifiée.'
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

describe('Routes dans le fil cantonal', () => {
	// Le module de données et les limites des communes sont gardés pour la visite : un module neuf à chaque cas.
	beforeEach(() => vi.resetModules());
	afterEach(() => vi.unstubAllGlobals());

	const AUJOURDHUI = '2026-10-16';
	const CONTEXTE = { aujourdhui: AUJOURDHUI, zone: null, communes: [PULLY, LUTRY] };
	const CANTON: ReglagesFil = { masques: [], portee: 'canton' };

	/** Le fil calculé avec les seules entrées des Routes, lues sur le faux DGMR comme le fait le chargement du fil. */
	async function filDesRoutes(dgmr: FauxDgmr, reglages = CANTON, ctx: Partial<ContexteFil> = {}) {
		vi.stubGlobal('fetch', dgmr.fetch);
		const { coucheRoutes: c } = await import('./index.js');
		const fil = c.fil!;
		const source: SourceFil = {
			couche: c.id,
			nom: c.nom,
			types: fil.types,
			etat: { entrees: await fil.entrees(depuisFil(AUJOURDHUI)) },
			sansCommune: fil.sansCommune
		};
		return calculerFil([source], reglages, { ...CONTEXTE, ...ctx });
	}
	const elements = (lignes: { element: string }[]) => lignes.map((l) => l.element);

	it('donne une entrée par restriction, déviations comprises, nommée par ses travaux et sa première commune', async () => {
		const fermeture = restriction(1, { NOM: 'Lutry, Route du Lac' }, [[6.71, 46.5], [6.72, 46.5]]);
		// 0,01° chez Pully, 0,03° chez Lutry : Lutry d'abord.
		const deviation = restriction(2, { RESTRICTION: 'Déviation', NOM: 'Lutry, Route du Lac' }, [
			[6.69, 46.5],
			[6.73, 46.5]
		]);

		const v = await filDesRoutes(fauxDgmr({ enCours: [fermeture, deviation] }));

		expect(v.jours.map((j) => [j.date, elements(j.entrees)])).toEqual([['2026-10-12', ['1', '2']]]);
		expect(v.jours[0].entrees[1]).toMatchObject({
			couche: 'routes',
			element: '2',
			type: 'restrictions',
			date: '2026-10-12',
			sorte: 'Déviation',
			titre: 'Lutry, Route du Lac',
			qui: 'Lutry',
			communes: ['lutry', 'pully'],
			position: [expect.closeTo(6.71, 6), expect.closeTo(46.5, 6)]
		});
	});

	it('date une entrée du jour de `DATE_DEBUT` tel qu’écrit, même tard le soir', async () => {
		const nuit = restriction(1, { DATE_DEBUT: heureLocale('2026-10-12T23:30'), HEURE_DEBUT: '23:30' });
		const ete = restriction(2, { DATE_DEBUT: heureLocale('2026-10-05T22:15') });

		const v = await filDesRoutes(fauxDgmr({ enCours: [nuit, ete] }));

		expect(v.jours.map((j) => [j.date, elements(j.entrees)])).toEqual([
			['2026-10-12', ['1']],
			['2026-10-05', ['2']]
		]);
	});

	it('met en « À venir » ce qui commence après aujourd’hui, le plus proche d’abord', async () => {
		const v = await filDesRoutes(
			fauxDgmr({
				enCours: [restriction(1, { DATE_DEBUT: heureLocale('2026-10-16T07:00') })],
				aVenir: [
					restriction(2, { DATE_DEBUT: heureLocale('2026-10-26') }),
					restriction(3, { DATE_DEBUT: heureLocale('2026-10-19T19:30') })
				]
			})
		);

		expect(elements(v.avenir)).toEqual(['3', '2']);
		expect(v.jours.map((j) => [j.date, elements(j.entrees)])).toEqual([['2026-10-16', ['1']]]);
	});

	it('n’entre pas une restriction commencée avant la fenêtre, même si elle court encore', async () => {
		const v = await filDesRoutes(
			fauxDgmr({
				enCours: [
					restriction(1, { DATE_DEBUT: heureLocale('2026-10-01T23:30'), DATE_FIN: heureLocale('2026-11-30') }),
					restriction(2, { DATE_DEBUT: heureLocale('2026-10-02') })
				]
			})
		);

		expect(v.jours.map((j) => [j.date, elements(j.entrees)])).toEqual([['2026-10-02', ['2']]]);
	});

	it('teste la zone visible sur le milieu du tracé, pas sur ses communes', async () => {
		const aPully = restriction(1, {}, [[6.66, 46.5], [6.67, 46.5]]);
		// De Pully à Lutry, son milieu chez Lutry.
		const versLutry = restriction(2, { RESTRICTION: 'Déviation' }, [[6.68, 46.5], [6.74, 46.5]]);

		const v = await filDesRoutes(
			fauxDgmr({ enCours: [aPully, versLutry] }),
			{ masques: [], portee: 'zone' },
			{ zone: PULLY.bbox }
		);

		expect(v.jours.flatMap((j) => elements(j.entrees))).toEqual(['1']);
	});

	it('n’a qu’une puce « Restrictions », aux signe et couleur de la couche, et ne force pas « Sans commune »', async () => {
		// La seconde passe tout entière hors des communes connues (hors du canton) : sans commune, elle n'a pas de ligne.
		const horsCanton = restriction(2, {}, [[6.5, 46.5], [6.51, 46.5]]);
		const v = await filDesRoutes(fauxDgmr({ enCours: [restriction(1), horsCanton] }));

		expect(v.compteur).toBe(1);
		expect(v.puces).toEqual([
			{
				id: 'restrictions',
				nom: 'Restrictions',
				signe: coucheRoutes.icone.signe,
				couleur: coucheRoutes.icone.couleur,
				cle: 'routes:restrictions',
				active: true
			}
		]);
		expect(v.aideSansCommune).toBeNull();
		expect(v.sansCommune).toEqual([]);
	});

	it('rejette quand la 596 ou la 595 de la DGMR est en panne', async () => {
		vi.useFakeTimers({ toFake: ['setTimeout'] });
		try {
			const dgmr = fauxDgmr({ enCours: [restriction(1)] });
			dgmr.panne(503, 595);
			vi.stubGlobal('fetch', dgmr.fetch);
			const { coucheRoutes: c } = await import('./index.js');

			const attendu = expect(c.fil!.entrees('2026-10-02')).rejects.toThrow();
			await vi.advanceTimersByTimeAsync(6_000);
			await attendu;
		} finally {
			vi.useRealTimers();
		}
	});
});
