import { describe, expect, it } from 'vitest';
import { calculerFil, depuisFil, zoneDuFil, type ReglagesFil, type SourceFil } from './fil.js';
import type { EntreeFil } from '#lib/registre/types.js';
import type { Zone } from '#lib/types.js';
import { LUTRY, PULLY } from '#tests/faux-canton.js';

/** Une entrée factice : rattachée à Pully, le 10 octobre, sans position. */
function entree(element: string, e: Partial<EntreeFil> = {}): EntreeFil {
	return {
		element,
		type: 'a',
		date: '2026-10-10',
		sorte: 'Sorte',
		qui: 'Qui',
		titre: `Titre ${element}`,
		communes: ['pully'],
		...e
	};
}

/** Une couche factice dont les entrées sont chargées. */
function source(couche: string, entrees: EntreeFil[], types = ['a', 'b']): SourceFil {
	return {
		couche,
		nom: couche[0].toUpperCase() + couche.slice(1),
		types: types.map((id) => ({
			id,
			nom: `Type ${id}`,
			signe: id.toUpperCase(),
			couleur: '#000'
		})),
		etat: { entrees }
	};
}

const REGLAGES: ReglagesFil = { masques: [], portee: 'canton' };
const CONTEXTE = {
	aujourdhui: '2026-10-16',
	zone: null,
	communes: [PULLY, LUTRY]
};

/** Les éléments de chaque jour, sous la forme couche:element. */
const jours = (v: ReturnType<typeof calculerFil>) =>
	v.jours.map((j) => [j.date, j.entrees.map((e) => `${e.couche}:${e.element}`)]);

describe('fil cantonal', () => {
	it('fusionne les entrées de plusieurs couches, groupées par jour, le plus récent d’abord', () => {
		const v = calculerFil(
			[
				source('permis', [entree('1', { date: '2026-10-12' }), entree('2', { date: '2026-10-14' })]),
				source('conseils', [entree('o1', { date: '2026-10-12' })])
			],
			REGLAGES,
			CONTEXTE
		);

		expect(jours(v)).toEqual([
			['2026-10-14', ['permis:2']],
			['2026-10-12', ['permis:1', 'conseils:o1']]
		]);
	});

	it('garde les 14 derniers jours, et met en tête « À venir » ce qui est daté du futur, le plus proche d’abord', () => {
		expect(depuisFil('2026-10-16')).toBe('2026-10-02');
		expect(depuisFil('2026-03-05')).toBe('2026-02-19');

		const v = calculerFil(
			[
				source('conseils', [
					entree('trop-vieux', { date: '2026-10-01' }),
					entree('premier-jour', { date: '2026-10-02' }),
					entree('aujourdhui', { date: '2026-10-16' }),
					entree('apres-demain', { date: '2026-10-18' }),
					entree('demain', { date: '2026-10-17' })
				])
			],
			REGLAGES,
			CONTEXTE
		);

		expect(v.avenir.map((e) => e.element)).toEqual(['demain', 'apres-demain']);
		expect(jours(v)).toEqual([
			['2026-10-16', ['conseils:aujourdhui']],
			['2026-10-02', ['conseils:premier-jour']]
		]);
	});

	it('range un jour dans l’ordre des couches du rail, puis dans l’ordre des types déclarés', () => {
		const v = calculerFil(
			[
				source(
					'conseils',
					[
						entree('seance', { type: 'seance' }),
						entree('objet-1', { type: 'objet' }),
						entree('objet-2', { type: 'objet' })
					],
					['objet', 'seance']
				),
				source('permis', [entree('1', { type: 'nouveaux' })], ['nouveaux'])
			],
			REGLAGES,
			CONTEXTE
		);

		expect(jours(v)).toEqual([['2026-10-10', ['conseils:objet-1', 'conseils:objet-2', 'conseils:seance', 'permis:1']]]);
	});

	describe('zone visible', () => {
		const sources = [
			source('couche', [
				entree('point-a-lutry', {
					position: [6.72, 46.5],
					communes: ['pully']
				}),
				entree('point-a-pully', {
					position: [6.67, 46.5],
					communes: ['lutry']
				}),
				entree('pully-et-lutry', { communes: ['pully', 'lutry'] }),
				entree('pully', { communes: ['pully'] }),
				entree('a-venir-a-lutry', { date: '2026-10-20', communes: ['lutry'] })
			])
		];
		const elements = (v: ReturnType<typeof calculerFil>) => [
			...v.avenir.map((e) => e.element),
			...v.jours.flatMap((j) => j.entrees.map((e) => e.element))
		];

		it('garde une entrée par sa position, sinon par l’hôtel de ville de l’une de ses communes, et les compte', () => {
			const v = calculerFil(sources, { masques: [], portee: 'zone' }, { ...CONTEXTE, zone: LUTRY.bbox });

			expect(elements(v)).toEqual(['a-venir-a-lutry', 'point-a-lutry', 'pully-et-lutry']);
			expect(v.compteur).toBe(3);
		});

		it('garde tout avec « Tout le canton », ou tant que la carte n’a rien affiché', () => {
			const canton = calculerFil(sources, REGLAGES, {
				...CONTEXTE,
				zone: LUTRY.bbox
			});
			const sansZone = calculerFil(sources, { masques: [], portee: 'zone' }, CONTEXTE);

			expect(canton.compteur).toBe(5);
			expect(sansZone.compteur).toBe(5);
		});
	});

	it('met à part, quelle que soit la zone et hors compteur, les entrées sans commune, à venir d’abord', () => {
		const v = calculerFil(
			[
				source('conseils', [
					entree('objet', { communes: [], date: '2026-10-12' }),
					entree('seance-tenue', { communes: [], date: '2026-10-14' }),
					entree('seance-annoncee', { communes: [], date: '2026-10-21' }),
					entree('a-lutry', { communes: ['lutry'] })
				])
			],
			{ masques: [], portee: 'zone' },
			{ ...CONTEXTE, zone: PULLY.bbox }
		);

		expect(v.sansCommune.map((e) => e.element)).toEqual(['seance-annoncee', 'seance-tenue', 'objet']);
		expect(v.avenir).toEqual([]);
		expect(v.jours).toEqual([]);
		expect(v.compteur).toBe(0);
	});

	it('a une puce par type déclaré, avant même les données, et une puce éteinte retire ses entrées partout', () => {
		const conseils = source(
			'conseils',
			[
				entree('objet', { type: 'objet' }),
				entree('objet-sans-commune', { type: 'objet', communes: [] }),
				entree('seance', { type: 'seance' }),
				entree('seance-sans-commune', { type: 'seance', communes: [] })
			],
			['objet', 'seance']
		);
		const permis: SourceFil = {
			...source('permis', [], ['nouveaux']),
			etat: 'chargement'
		};

		const v = calculerFil([conseils, permis], { masques: ['conseils:objet'], portee: 'canton' }, CONTEXTE);

		expect(v.puces.map((p) => [p.cle, p.nom, p.active])).toEqual([
			['conseils:objet', 'Type objet', false],
			['conseils:seance', 'Type seance', true],
			['permis:nouveaux', 'Type nouveaux', true]
		]);
		expect(jours(v)).toEqual([['2026-10-10', ['conseils:seance']]]);
		expect(v.sansCommune.map((e) => e.element)).toEqual(['seance-sans-commune']);
		expect(v.compteur).toBe(1);
	});

	it('donne une ligne par couche en panne, et garde les entrées des autres', () => {
		const v = calculerFil(
			[
				{ ...source('permis', []), etat: 'panne' },
				source('conseils', [entree('o1')]),
				{ ...source('autre', []), etat: 'panne' },
				{ ...source('lente', []), etat: 'chargement' }
			],
			REGLAGES,
			CONTEXTE
		);

		expect(v.pannes).toEqual([
			{ couche: 'permis', nom: 'Permis' },
			{ couche: 'autre', nom: 'Autre' }
		]);
		expect(v.chargement).toBe(true);
		expect(jours(v)).toEqual([['2026-10-10', ['conseils:o1']]]);
	});
});

describe('zone du fil', () => {
	const CANTON: Zone = [5.9, 46.18, 7.25, 46.99];
	const AUTOUR_DU_DOSSIER: Zone = [6.719, 46.499, 6.721, 46.501];

	it('est la zone initiale à l’arrivée, puis celle du dernier déplacement fait par la personne', () => {
		let zone = zoneDuFil(null, CANTON, false);
		expect(zone).toEqual(CANTON);

		zone = zoneDuFil(zone, LUTRY.bbox, true);
		expect(zone).toEqual(LUTRY.bbox);
	});

	it('ne bouge pas quand la carte vole vers l’élément qu’on ouvre', () => {
		expect(zoneDuFil(LUTRY.bbox, AUTOUR_DU_DOSSIER, false)).toEqual(LUTRY.bbox);
	});
});
