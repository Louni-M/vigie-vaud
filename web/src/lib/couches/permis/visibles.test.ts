import { describe, expect, it } from 'vitest';
import { visibles, type Parametres } from './donnees.svelte.js';
import type { Dossier, PointHisto, Zone } from '#lib/types.js';

/** Zone visible : Lausanne et environs. */
const ZONE: Zone = [6.5, 46.4, 6.8, 46.6];

const EN_COURS: Parametres = {
	statuts: ['enquete', 'procedure'],
	nature: '',
	historique: false,
	depuis: 2024,
	tri: 'recent'
};

function dossier(id: number, champs: Partial<Dossier> = {}): Dossier {
	return {
		id,
		statut: 'enquete',
		nature: 'construction',
		debut: '2026-09-01',
		fin: '2026-09-30',
		lon: 6.63,
		lat: 46.52,
		bfs: 5586,
		commune: 'Lausanne',
		slug: 'lausanne',
		...champs
	};
}

function point(id: number, champs: Partial<PointHisto> = {}): PointHisto {
	return { id, statut: 'delivre', nature: 'construction', debut: '2025-03-01', fin: '2025-03-30', lon: 6.63, lat: 46.52, ...champs };
}

const ids = (ds: { id: number }[]) => ds.map((d) => d.id);

describe('visibles', () => {
	it('ne garde que les dossiers dans la zone visible', () => {
		const actifs = [dossier(1), dossier(2, { lon: 7.2, lat: 46.1 }), dossier(3, { lat: 46.6 })];
		expect(ids(visibles(ZONE, EN_COURS, { actifs, histo: [] }))).toEqual([3, 1]);
	});

	it('ne garde que les statuts choisis', () => {
		const actifs = [dossier(1), dossier(2, { statut: 'procedure' })];
		expect(ids(visibles(ZONE, { ...EN_COURS, statuts: ['procedure'] }, { actifs, histo: [] }))).toEqual([2]);
		expect(visibles(ZONE, { ...EN_COURS, statuts: [] }, { actifs, histo: [] })).toEqual([]);
	});

	it('ne garde que la nature choisie, ou toutes si aucune', () => {
		const actifs = [dossier(1), dossier(2, { nature: 'demolition' })];
		expect(ids(visibles(ZONE, { ...EN_COURS, nature: 'demolition' }, { actifs, histo: [] }))).toEqual([2]);
		expect(ids(visibles(ZONE, { ...EN_COURS, nature: '' }, { actifs, histo: [] }))).toEqual([2, 1]);
	});

	describe('tri', () => {
		const actifs = [
			dossier(1, { statut: 'procedure', debut: '2026-09-20', fin: '2026-10-01' }),
			dossier(2, { debut: '2026-09-01', fin: '2026-10-20' }),
			dossier(3, { debut: '2026-09-10', fin: '2026-10-10' }),
			dossier(4, { debut: '2026-09-10', fin: '2026-10-30' })
		];

		it('récent : publication la plus récente d’abord, puis le n° le plus grand', () => {
			expect(ids(visibles(ZONE, EN_COURS, { actifs, histo: [] }))).toEqual([1, 4, 3, 2]);
		});

		it('fin : enquêtes en cours d’abord, la plus proche de sa fin en tête, puis par publication', () => {
			expect(ids(visibles(ZONE, { ...EN_COURS, tri: 'fin' }, { actifs, histo: [] }))).toEqual([3, 2, 4, 1]);
		});
	});

	describe('historique', () => {
		const TOUS: Parametres = {
			...EN_COURS,
			statuts: ['enquete', 'procedure', 'delivre', 'realise', 'abandonne'],
			historique: true,
			depuis: 2024
		};
		const actifs = [dossier(1, { debut: '2026-09-01' })];
		const histo = [
			point(1, { statut: 'enquete', debut: '2026-09-01' }),
			point(2, { debut: '2025-03-01' }),
			point(3, { debut: '2024-01-15' }),
			point(4, { debut: '2023-12-31' }),
			point(5, { debut: '2025-06-01', lon: 7.5 })
		];

		it('n’ajoute les points de l’historique que si l’historique est affiché', () => {
			expect(ids(visibles(ZONE, { ...TOUS, historique: false }, { actifs, histo }))).toEqual([1]);
		});

		it('ajoute les points depuis l’année choisie, sans doublon avec les dossiers en cours', () => {
			expect(ids(visibles(ZONE, TOUS, { actifs, histo }))).toEqual([1, 2, 3]);
			expect(ids(visibles(ZONE, { ...TOUS, depuis: 2025 }, { actifs, histo }))).toEqual([1, 2]);
		});

		it('ne filtre pas les dossiers en cours par année', () => {
			const anciens = [dossier(7, { statut: 'procedure', debut: '2023-11-02' })];
			expect(ids(visibles(ZONE, { ...TOUS, depuis: 2026 }, { actifs: anciens, histo: [] }))).toEqual([7]);
		});

		it('applique les statuts aux points de l’historique', () => {
			const p = { ...TOUS, statuts: ['enquete'] as Parametres['statuts'] };
			expect(ids(visibles(ZONE, p, { actifs, histo }))).toEqual([1]);
		});
	});

	it('ne montre rien tant que la zone visible est inconnue', () => {
		expect(visibles(null, EN_COURS, { actifs: [dossier(1)], histo: [] })).toEqual([]);
	});
});
