import { describe, expect, it, vi } from 'vitest';
import { fauxDgmr, heureLocale, restriction, type RestrictionDgmr } from '#tests/faux-dgmr.js';
import { creerDonneesRoutes, type Restriction } from './donnees.svelte.js';
import { FILTRES_INITIAUX, sortesDesPuces, visibles, type Filtres } from './volet.js';

// Le module de données refuse d'interroger la DGMR ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

const maintenant = () => new Date('2026-10-18T10:00:00Z');

/** Les restrictions telles que les lit le module de données. */
async function lues(dgmr: { enCours?: RestrictionDgmr[]; aVenir?: RestrictionDgmr[] }): Promise<Restriction[]> {
	const donnees = creerDonneesRoutes({ fetch: fauxDgmr(dgmr).fetch, maintenant });
	await donnees.charger();
	return donnees.restrictions;
}

/** Zone visible : Pully et Lutry (le tracé par défaut traverse Pully). */
const ZONE: [number, number, number, number] = [6.65, 46.49, 6.75, 46.52];
const ids = (rs: { id: number }[]) => rs.map((r) => r.id);

describe('visibles', () => {
	describe('filtres', () => {
		const DGMR = {
			enCours: [
				restriction(1),
				restriction(2, { RESTRICTION: 'Déviation' }),
				restriction(3, { RESTRICTION: 'Feux' }),
				restriction(4, { RESTRICTION: 'Manifestation' })
			],
			aVenir: [restriction(5, { DATE_DEBUT: heureLocale('2026-10-25'), DATE_FIN: heureLocale('2026-11-06') })]
		};

		it.each<[string, Partial<Filtres>, number[]]>([
			['toutes les sortes, en cours et à venir', {}, [1, 2, 3, 4, 5]],
			['les fermetures seulement', { sortes: ['fermeture'] }, [1, 5]],
			['les déviations et les feux', { sortes: ['deviation', 'feux'] }, [2, 3]],
			['« Autre » pour une sorte inconnue', { sortes: ['autre'] }, [4]],
			['aucune sorte', { sortes: [] }, []],
			['l’en cours seulement', { etats: ['en_cours'] }, [1, 2, 3, 4]],
			['l’à venir seulement', { etats: ['a_venir'] }, [5]],
			['les fermetures à venir', { sortes: ['fermeture'], etats: ['a_venir'] }, [5]],
			['ni en cours ni à venir', { etats: [] }, []]
		])('%s', async (_, filtres, attendus) => {
			const rs = await lues(DGMR);
			expect(ids(visibles(rs, { ...FILTRES_INITIAUX, ...filtres }, ZONE)).sort((a, b) => a - b)).toEqual(attendus);
		});
	});

	describe('zone visible', () => {
		type Cas = [string, [number, number][] | [number, number][][], boolean];
		it.each<Cas>([
			['un tracé dans la zone', [[6.67, 46.5], [6.68, 46.5]], true],
			['un tracé loin de la zone', [[6.9, 46.6], [6.95, 46.6]], false],
			[
				'un tracé qui coupe la zone sans que son milieu ni aucun de ses sommets y soit',
				[[6.6, 46.5], [6.8, 46.5], [6.8, 46.7], [6.8, 47]],
				true
			],
			['un tracé qui passe au coin de la zone, sans y entrer', [[6.74, 46.54], [6.77, 46.51]], false],
			['un tracé qui entre dans la zone par un coin', [[6.74, 46.53], [6.76, 46.51]], true],
			['une MultiLineString dont un seul morceau est dans la zone', [[[6.9, 46.6], [6.95, 46.6]], [[6.7, 46.5], [6.71, 46.5]]], true],
			['une MultiLineString dont aucun morceau n’est dans la zone', [[[6.9, 46.6], [6.95, 46.6]], [[6.6, 46.4], [6.6, 46.45]]], false]
		])('%s', async (_, trace, dedans) => {
			const rs = await lues({ enCours: [restriction(1, {}, trace)] });
			expect(ids(visibles(rs, FILTRES_INITIAUX, ZONE))).toEqual(dedans ? [1] : []);
		});

		it('ne montre rien tant que la zone visible est inconnue', async () => {
			const rs = await lues({ enCours: [restriction(1)] });
			expect(visibles(rs, FILTRES_INITIAUX, null)).toEqual([]);
		});
	});

	it('range l’en cours par fin la plus proche, puis l’à venir par jour de début, sorte et numéro n’y changeant rien', async () => {
		const fin = (jour: string) => ({ DATE_FIN: heureLocale(jour) });
		const debut = (jour: string) => ({ DATE_DEBUT: heureLocale(jour), DATE_FIN: heureLocale('2026-11-06') });
		const rs = await lues({
			enCours: [
				restriction(1, fin('2026-10-23')),
				restriction(2, { RESTRICTION: 'Déviation', ...fin('2026-10-20') }),
				restriction(3, { RESTRICTION: 'Feux', ...fin('2026-11-30') }),
				restriction(4, fin('2026-10-19'))
			],
			aVenir: [
				restriction(5, debut('2026-10-28')),
				restriction(6, { RESTRICTION: 'Feux', ...debut('2026-10-21') }),
				restriction(7, debut('2026-10-25'))
			]
		});
		expect(ids(visibles(rs, FILTRES_INITIAUX, ZONE))).toEqual([4, 2, 1, 3, 6, 7, 5]);
	});
});

describe('puces des sortes', () => {
	it('suivent l’ordre de la légende, sans « Autre » tant qu’aucune restriction n’en est', async () => {
		const rs = await lues({ enCours: [restriction(1, { RESTRICTION: 'Feux' })] });
		expect(sortesDesPuces(rs)).toEqual(['fermeture', 'deviation', 'feux', 'particuliere']);
		expect(sortesDesPuces([])).toEqual(['fermeture', 'deviation', 'feux', 'particuliere']);
	});

	it('montrent « Autre » dès qu’une restriction d’une sorte inconnue est chargée, en cours ou à venir', async () => {
		const autre = restriction(2, { RESTRICTION: 'Manifestation', DATE_DEBUT: heureLocale('2026-10-25') });
		const rs = await lues({ enCours: [restriction(1)], aVenir: [autre] });
		expect(sortesDesPuces(rs)).toEqual(['fermeture', 'deviation', 'feux', 'particuliere', 'autre']);
	});
});
