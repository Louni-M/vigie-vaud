import { describe, expect, it, vi } from 'vitest';
import { creerDonneesRoutes, type Restriction } from './donnees.svelte.js';
import { ficheRestriction, ligneMemesTravaux, memesTravaux, routeEnClair } from './fiche.js';
import { fauxDgmr, heureLocale, PIEGES, restriction, type RestrictionDgmr } from '#tests/faux-dgmr.js';

// Le module refuse d'interroger la DGMR ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

const maintenant = () => new Date('2026-10-18T10:00:00Z');

/** Des restrictions telles que les lit le module de données, depuis le faux DGMR. */
async function lues(enCours: RestrictionDgmr[], aVenir: RestrictionDgmr[] = []): Promise<Restriction[]> {
	return creerDonneesRoutes({ fetch: fauxDgmr({ enCours, aVenir }).fetch, maintenant }).charger();
}

describe('route en clair', () => {
	it.each([
		['626-B-P', 'Route cantonale 626 (réseau de base, principale)'],
		['701-C-S', 'Route cantonale 701 (réseau complémentaire, secondaire)'],
		['89-IL-P', 'Route cantonale 89 (intérêt local, principale)'],
		['1-IL-S', 'Route cantonale 1 (intérêt local, secondaire)'],
		['626 - B - P', 'Route cantonale 626 (réseau de base, principale)'],
		['626-b-p', 'Route cantonale 626 (réseau de base, principale)']
	])('lit « %s » : « %s »', (rhrc, attendue) => {
		expect(routeEnClair(rhrc)).toBe(attendue);
	});

	it.each(['RC 626', '626-X-P', '626-B', 'Route de Berne'])('donne telle quelle une valeur hors forme : « %s »', (rhrc) => {
		expect(routeEnClair(rhrc)).toBe(rhrc);
	});

	it('ne dit rien sans RHRC', () => {
		expect(routeEnClair(null)).toBeNull();
	});
});

describe('fiche d’une restriction', () => {
	it('dit la sorte, l’état et l’échéance, le nom, la période en toutes lettres, les horaires, la route et les communes', async () => {
		// 0,01° chez Lutry, puis 0,04° chez Pully : Pully d'abord.
		const nuit = {
			...PIEGES.nuitFinContredite,
			geometry: { type: 'LineString' as const, coordinates: [[6.71, 46.5], [6.66, 46.5]] as [number, number][] }
		};
		const [r] = await creerDonneesRoutes({ fetch: fauxDgmr({ aVenir: [nuit] }).fetch, maintenant }).rattachees();

		expect(ficheRestriction(r, { aujourdhui: '2026-10-18' })).toEqual({
			sorte: 'Fermeture',
			couleur: '#c92a2a',
			tirets: false,
			etat: 'À venir',
			echeance: 'commence dans 8 jours',
			nom: 'Lutry, Route des Essais nuit',
			periode: 'Du lundi 26 octobre 2026 au jeudi 29 octobre 2026',
			horaires: 'La nuit seulement, de 19 h 30 à 5 h 30',
			weekEnd: 'Levée le week-end',
			route: 'Route cantonale 701 (réseau de base, principale)',
			travaux: 'Revêtement',
			remarque: null,
			longueur: '3,8 km',
			communes: [
				{ slug: 'pully', nom: 'Pully', longueur: '3,1 km' },
				{ slug: 'lutry', nom: 'Lutry', longueur: '770 m' }
			]
		});
	});

	it('nomme en une ligne une autre restriction des mêmes travaux', async () => {
		const deviation = restriction(2, { RESTRICTION: 'Déviation' }, [[6.69, 46.5], [6.73, 46.5]]);
		const [r] = await creerDonneesRoutes({ fetch: fauxDgmr({ enCours: [deviation] }).fetch, maintenant }).rattachees();

		expect(ligneMemesTravaux(r)).toEqual({
			sorte: 'Déviation',
			couleur: '#e8590c',
			tirets: true,
			detail: 'en cours · Lutry, Pully · 3,1 km'
		});
	});
});

describe('mêmes travaux', () => {
	const ids = (rs: Restriction[]) => rs.map((r) => r.id);

	it('réunit les restrictions de même RHRC et même NOM, en cours et à venir ensemble', async () => {
		const travaux = { RHRC: '626-B-P', NOM: 'Lutry, Route de la Corniche' };
		const rs = await lues(
			[restriction(1, travaux), restriction(2, { ...travaux, RESTRICTION: 'Déviation' })],
			[restriction(3, { ...travaux, RESTRICTION: 'Feux' }), restriction(4)]
		);

		expect(ids(memesTravaux(rs[0], rs))).toEqual([2, 3]);
		expect(ids(memesTravaux(rs[2], rs))).toEqual([1, 2]);
		expect(memesTravaux(rs[3], rs)).toEqual([]);
	});

	it('sépare deux noms au même endroit : deux travaux', async () => {
		const rs = await lues([
			restriction(1, { RHRC: '702-C-S', NOM: 'Morcles Le Revers feux' }),
			restriction(2, { RHRC: '702-C-S', NOM: 'Morcles Le Revers nuit' })
		]);

		expect(memesTravaux(rs[0], rs)).toEqual([]);
	});

	it('sépare un même nom sur deux routes', async () => {
		const rs = await lues([restriction(1, { RHRC: '626-B-P' }), restriction(2, { RHRC: '701-B-P' })]);

		expect(memesTravaux(rs[0], rs)).toEqual([]);
	});

	it('ne réunit pas des restrictions sans nom', async () => {
		const rs = await lues([restriction(1, { NOM: null }), restriction(2, { NOM: '' })]);

		expect(memesTravaux(rs[0], rs)).toEqual([]);
	});

	it('range les autres restrictions dans l’ordre des listes : l’en cours par fin, puis l’à venir par début', async () => {
		const travaux = { RHRC: '626-B-P', NOM: 'Lutry, Route de la Corniche' };
		const rs = await lues(
			[
				restriction(1, travaux),
				restriction(2, { ...travaux, DATE_FIN: heureLocale('2026-10-30') }),
				restriction(3, { ...travaux, DATE_FIN: heureLocale('2026-10-20') })
			],
			[
				restriction(4, { ...travaux, DATE_DEBUT: heureLocale('2026-11-02') }),
				restriction(5, { ...travaux, DATE_DEBUT: heureLocale('2026-10-26') })
			]
		);

		expect(ids(memesTravaux(rs[0], rs))).toEqual([3, 2, 5, 4]);
	});
});
