import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { creerDonneesRoutes } from './donnees.svelte.js';
import { fauxDgmr, heureLocale, PIEGES, restriction, type RestrictionDgmr } from '#tests/faux-dgmr.js';

// Le module refuse d'interroger la DGMR ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

/** Horloge fixée : 18 octobre 2026. */
const maintenant = () => new Date('2026-10-18T10:00:00Z');

const ids = (rs: { id: number }[]) => rs.map((r) => r.id);

describe('restrictions en cours et à venir', () => {
	it('réunit les deux couches, chacune dans l’état de sa couche d’origine', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(3), restriction(1)], aVenir: [restriction(2)] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const restrictions = await routes.charger();

		expect(restrictions.map((r) => [r.id, r.etat])).toEqual([
			[1, 'en_cours'],
			[2, 'a_venir'],
			[3, 'en_cours']
		]);
		expect(routes.restrictions).toEqual(restrictions);
	});

	it('ne garde qu’une fois, en cours, une restriction passée de la 595 à la 596 entre les deux requêtes', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(1), restriction(2)] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const restrictions = await routes.charger();

		expect(restrictions.map((r) => [r.id, r.etat])).toEqual([
			[1, 'en_cours'],
			[2, 'a_venir']
		]);
	});

	it('lit les champs de la DGMR tels qu’écrits, et place le milieu du tracé à mi-longueur', async () => {
		const dgmr = fauxDgmr({ aVenir: [PIEGES.nuitFinContredite] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const [r] = await routes.charger();

		expect(r).toStrictEqual({
			id: 9001,
			etat: 'a_venir',
			sorte: 'fermeture',
			libelleSorte: 'Fermeture',
			nom: 'Lutry, Route des Essais nuit',
			rhrc: '701-B-P',
			dateDebut: heureLocale('2026-10-26T19:30'),
			dateFin: heureLocale('2026-10-29T23:59'),
			heureDebut: '19:30',
			heureFin: '05:30',
			weekEnd: 'non',
			travaux: 'Revêtement',
			remarque: null,
			lignes: [
				[
					[6.71, 46.5],
					[6.72, 46.5]
				]
			],
			longueur: expect.closeTo(765.4, 0),
			milieu: [expect.closeTo(6.715, 9), expect.closeTo(46.5, 9)]
		});
	});

	it('lit une MultiLineString morceau par morceau', async () => {
		const dgmr = fauxDgmr({ enCours: [PIEGES.enMorceaux] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const [r] = await routes.charger();

		expect(r.lignes).toHaveLength(3);
		// Deux morceaux de 0,01° de part et d’autre : la mi-longueur tombe au milieu du deuxième (à quelques mètres près).
		expect(r.milieu[0]).toBeCloseTo(6.685, 4);
	});

	it.each([
		['Fermeture', 'fermeture'],
		['Déviation', 'deviation'],
		['Feux', 'feux'],
		['Restriction particulière', 'particuliere'],
		['Manifestation', 'autre'],
		[null, 'autre']
	] as const)('range « %s » dans la sorte %s, en gardant le libellé publié', async (publie, sorte) => {
		const dgmr = fauxDgmr({ enCours: [restriction(1, { RESTRICTION: publie })] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const [r] = await routes.charger();

		expect(r.sorte).toBe(sorte);
		expect(r.libelleSorte).toBe(publie ?? 'Autre');
	});

	it('remet à null les champs vides ou faits d’espaces', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1, { REMARQUE: '  ', TYPE: '', WEEK_END: null, RHRC: ' 626-C-S ' })] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const [r] = await routes.charger();

		expect(r).toMatchObject({ remarque: null, travaux: null, weekEnd: null, rhrc: '626-C-S' });
	});
});

describe('requêtes à la DGMR', () => {
	it('demande chaque couche une seule fois par visite, pour tous les usages', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		await Promise.all([routes.charger(), routes.charger()]);
		await routes.charger();

		expect(dgmr.requetes.map((q) => [q.couche, q.where]).sort()).toEqual([
			[595, '1=1'],
			[596, '1=1']
		]);
	});

	it('demande tout le canton, sans emprise, en WGS84', async () => {
		const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		await routes.charger();

		for (const { parametres: p } of dgmr.requetes) {
			for (const cle of ['geometry', 'geometryType', 'spatialRel', 'inSR']) expect(p.has(cle)).toBe(false);
			expect(p.get('outSR')).toBe('4326');
		}
	});

	it('suit la pagination au-delà de 2000 restrictions', async () => {
		const beaucoup: RestrictionDgmr[] = Array.from({ length: 4500 }, (_, i) => restriction(i + 1));
		const dgmr = fauxDgmr({ enCours: beaucoup, aVenir: [restriction(5000)] });
		const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

		const restrictions = await routes.charger();

		expect(restrictions).toHaveLength(4501);
		expect(new Set(ids(restrictions)).size).toBe(4501);
		expect(dgmr.requetes.filter((q) => q.couche === 596)).toHaveLength(3);
	});
});

describe('état de la source DGMR', () => {
	it('date la dernière consultation réussie', async () => {
		let heure = new Date('2026-10-18T10:00:00Z');
		const routes = creerDonneesRoutes({ fetch: fauxDgmr({ enCours: [restriction(1)] }).fetch, maintenant: () => heure });
		expect(routes.source).toMatchObject({ derniere: null, erreur: null });

		heure = new Date('2026-10-18T10:02:00Z');
		await routes.charger();

		expect(routes.source).toMatchObject({ derniere: heure, erreur: null });
	});

	describe('échecs', () => {
		beforeEach(() => {
			vi.useFakeTimers();
			vi.stubGlobal('navigator', { onLine: true });
		});
		afterEach(() => {
			vi.useRealTimers();
			vi.unstubAllGlobals();
		});

		it('passe en « service indisponible » sur une erreur HTTP, après une seule nouvelle tentative', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
			dgmr.panne(503);
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

			const rejet = expect(routes.charger()).rejects.toThrow();
			await vi.advanceTimersByTimeAsync(4_000);
			expect(routes.source.erreur).toBeNull();
			await vi.advanceTimersByTimeAsync(60_000);
			await rejet;

			expect(routes.source).toMatchObject({ derniere: null, erreur: 'indisponible' });
			expect(routes.restrictions).toEqual([]);
		});

		it('passe en « hors ligne » quand le navigateur n’a plus de réseau', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)] });
			dgmr.horsLigne(true);
			vi.stubGlobal('navigator', { onLine: false });
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

			const rejet = expect(routes.charger()).rejects.toThrow();
			await vi.advanceTimersByTimeAsync(6_000);
			await rejet;

			expect(routes.source.erreur).toBe('hors_ligne');
		});

		it('se rétablit seul si la nouvelle tentative réussit', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
			dgmr.panne(503);
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

			const chargement = routes.charger();
			await vi.advanceTimersByTimeAsync(10);
			dgmr.panne(null);
			await vi.advanceTimersByTimeAsync(6_000);

			expect(ids(await chargement)).toEqual([1, 2]);
			expect(routes.source.erreur).toBeNull();
		});

		it('met la source en erreur quand seule la 595 est en panne, et garde l’en cours', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
			dgmr.panne(500, 595);
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });

			const rejet = expect(routes.charger()).rejects.toThrow();
			await vi.advanceTimersByTimeAsync(6_000);
			await rejet;

			expect(routes.source.erreur).toBe('indisponible');
			expect(routes.restrictions.map((r) => [r.id, r.etat])).toEqual([[1, 'en_cours']]);
		});

		it('« Réessayer » lève l’erreur et ne redemande que la couche manquée', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
			dgmr.panne(500, 595);
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });
			routes.charger().catch(() => {});
			await vi.advanceTimersByTimeAsync(6_000);
			expect(routes.source.erreur).toBe('indisponible');

			dgmr.panne(null);
			dgmr.requetes.length = 0;
			routes.source.recharger();
			expect(routes.source.erreur).toBeNull();
			await vi.advanceTimersByTimeAsync(10);

			expect(routes.restrictions.map((r) => [r.id, r.etat])).toEqual([
				[1, 'en_cours'],
				[2, 'a_venir']
			]);
			expect(dgmr.requetes.map((q) => q.couche)).toEqual([595]);
			expect(routes.source.erreur).toBeNull();
		});

		it('« Réessayer » après une coupure recharge les deux couches', async () => {
			const dgmr = fauxDgmr({ enCours: [restriction(1)], aVenir: [restriction(2)] });
			dgmr.horsLigne(true);
			vi.stubGlobal('navigator', { onLine: false });
			const routes = creerDonneesRoutes({ fetch: dgmr.fetch, maintenant });
			routes.charger().catch(() => {});
			await vi.advanceTimersByTimeAsync(6_000);
			expect(routes.source.erreur).toBe('hors_ligne');

			dgmr.horsLigne(false);
			vi.stubGlobal('navigator', { onLine: true });
			routes.source.recharger();
			await vi.advanceTimersByTimeAsync(10);

			expect(ids(routes.restrictions)).toEqual([1, 2]);
			expect(routes.source).toMatchObject({ derniere: maintenant(), erreur: null });
		});
	});
});
