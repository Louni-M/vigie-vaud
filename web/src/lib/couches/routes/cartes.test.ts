import { describe, expect, it, vi } from 'vitest';
import { source } from '#lib/sources.js';
import { fauxDgmr, heureLocale, PIEGES, restriction, type RestrictionDgmr } from '#tests/faux-dgmr.js';
import { carteRestriction, encadreLimites, sectionsDeLaCommune } from './cartes.js';
import { creerDonneesRoutes } from './donnees.svelte.js';

// Le module de données refuse d'interroger la DGMR ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

const maintenant = () => new Date('2026-10-18T10:00:00Z');

/** Les restrictions telles que les lit et les rattache le module de données, sur le faux canton (Pully, Lutry). */
async function lues(dgmr: { enCours?: RestrictionDgmr[]; aVenir?: RestrictionDgmr[] }) {
	return creerDonneesRoutes({ fetch: fauxDgmr(dgmr).fetch, maintenant }).rattachees();
}

describe('encadré de l’onglet Routes', () => {
	it('reprend les limites de la DGMR déclarées dans sources.json', () => {
		expect(encadreLimites(source('dgmr-restrictions'))).toBe(
			'La DGMR publie surtout les routes cantonales ; les routes communales n’y figurent pas toujours.'
		);
	});

	it('suit le champ limites de la source, et ne dit rien sans lui', () => {
		const dgmr = source('dgmr-restrictions');
		expect(encadreLimites({ ...dgmr, limites: 'seulement les ponts' })).toBe('La DGMR publie seulement les ponts.');
		expect(encadreLimites({ ...dgmr, limites: null })).toBeNull();
	});
});

describe('sections de l’onglet Routes', () => {
	const fin = (jour: string) => ({ DATE_FIN: heureLocale(jour) });
	const debut = (jour: string) => ({ DATE_DEBUT: heureLocale(jour), DATE_FIN: heureLocale('2026-11-06') });
	/** Une déviation de Pully à Lutry : 0,01° chez Pully, 0,03° chez Lutry. */
	const DE_PULLY_A_LUTRY: [number, number][] = [[6.69, 46.5], [6.73, 46.5]];
	const A_LUTRY: [number, number][] = [[6.71, 46.5], [6.72, 46.5]];
	const DGMR = {
		enCours: [
			restriction(1, fin('2026-10-23')),
			restriction(2, { RESTRICTION: 'Feux', ...fin('2026-10-20') }),
			restriction(3, { RESTRICTION: 'Déviation', ...fin('2026-10-30') }, DE_PULLY_A_LUTRY),
			restriction(4, fin('2026-10-19'), A_LUTRY)
		],
		aVenir: [
			restriction(5, debut('2026-10-28')),
			PIEGES.nuitFinContredite,
			restriction(7, { RESTRICTION: 'Feux', ...debut('2026-10-25') })
		]
	};
	const ids = ({ enCours, aVenir }: ReturnType<typeof sectionsDeLaCommune>) => ({
		enCours: enCours.map((r) => r.id),
		aVenir: aVenir.map((r) => r.id)
	});

	it('range l’en cours par fin la plus proche, puis l’à venir par jour de début, déviations qui traversent la commune comprises', async () => {
		const restrictions = await lues(DGMR);
		expect(ids(sectionsDeLaCommune(restrictions, 'pully'))).toEqual({ enCours: [2, 1, 3], aVenir: [7, 5] });
		expect(ids(sectionsDeLaCommune(restrictions, 'lutry'))).toEqual({ enCours: [4, 3], aVenir: [9001] });
	});

	it('n’a rien pour une commune sans restriction', async () => {
		expect(ids(sectionsDeLaCommune(await lues(DGMR), 'morges'))).toEqual({ enCours: [], aVenir: [] });
	});
});

describe('carte d’une restriction', () => {
	const aujourdhui = '2026-10-18';

	it('dit la sorte, les communes, la source, la période et l’échéance, et la longueur dans la commune quand il y en a plusieurs', async () => {
		const [deviation] = await lues({
			enCours: [restriction(3, { RESTRICTION: 'Déviation', DATE_FIN: heureLocale('2026-10-30') }, [[6.69, 46.5], [6.73, 46.5]])]
		});
		expect(carteRestriction(deviation, { aujourdhui, commune: 'pully' })).toEqual({
			sorte: 'Déviation',
			couleur: '#e8590c',
			tirets: true,
			aVenir: false,
			communes: 'Lutry, Pully',
			source: 'DGMR',
			periode: 'Du lun. 12 oct. au ven. 30 oct.',
			echeance: 'encore 12 jours',
			plage: null,
			remarque: null,
			dansLaCommune: '770 m dans la commune, sur 2 communes'
		});
		expect(carteRestriction(deviation, { aujourdhui, commune: 'lutry' }).dansLaCommune).toBe(
			'2,3 km dans la commune, sur 2 communes'
		);
		expect(carteRestriction(deviation, { aujourdhui }).dansLaCommune).toBeNull();
	});

	it('donne la plage de nuit d’une restriction à venir, sans longueur dans sa seule commune', async () => {
		const [nuit] = await lues({ aVenir: [PIEGES.nuitFinContredite] });
		expect(carteRestriction(nuit, { aujourdhui, commune: 'lutry' })).toMatchObject({
			sorte: 'Fermeture',
			tirets: false,
			aVenir: true,
			communes: 'Lutry',
			periode: 'Du lun. 26 oct. au jeu. 29 oct.',
			echeance: 'commence dans 8 jours',
			plage: 'La nuit seulement, de 19 h 30 à 5 h 30',
			dansLaCommune: null
		});
	});

	it('reprend la remarque, et la sorte publiée d’une valeur inconnue, en gris', async () => {
		const [r] = await lues({
			enCours: [restriction(8, { RESTRICTION: 'Manifestation', REMARQUE: 'Sens unique en direction de Lausanne' })]
		});
		expect(carteRestriction(r, { aujourdhui })).toMatchObject({
			sorte: 'Manifestation',
			couleur: '#868e96',
			remarque: 'Sens unique en direction de Lausanne'
		});
	});
});
