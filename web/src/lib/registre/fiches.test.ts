import { describe, expect, it } from 'vitest';
import { COUCHES } from './couches.js';
import { ficheDuChemin, fichePropre, fichesPropres } from './fiches.js';
import { teteFiche, titreFiche } from './tete.js';
import { PAGES_FIXES } from '#lib/indexation.js';

describe('fiches propres des couches inscrites', () => {
	it('ont chacune un identifiant et un chemin d’un seul segment, uniques et libres', () => {
		const fiches = fichesPropres(COUCHES).map((f) => f.fiche);
		const pris = new Set<string>([...PAGES_FIXES, '/commune']);
		for (const f of fiches) {
			expect(f.chemin).toMatch(/^\/[a-z0-9-]+$/);
			expect(pris.has(f.chemin)).toBe(false);
			pris.add(f.chemin);
		}
		expect(new Set(fiches.map((f) => f.id)).size).toBe(fiches.length);
	});

	it('se retrouvent par leur identifiant et par leur chemin', () => {
		expect(fichePropre(COUCHES, 'grand-conseil')?.couche.id).toBe('conseils');
		expect(ficheDuChemin(COUCHES, '/grand-conseil')?.fiche.id).toBe('grand-conseil');
		expect(fichePropre(COUCHES, 'pully')).toBeNull();
		expect(ficheDuChemin(COUCHES, '/a-propos')).toBeNull();
	});
});

describe('<head> de /grand-conseil', () => {
	const gc = fichePropre(COUCHES, 'grand-conseil')!.fiche;

	it('porte le titre et la description du Grand Conseil', () => {
		expect(teteFiche(gc)).toEqual({
			titre: 'Grand Conseil – Vigie Vaud',
			description:
				'Les objets et les séances du Grand Conseil vaudois, importés chaque jour depuis OpenParlData, et les communes qu’ils nomment.'
		});
	});

	it('suit l’élément ouvert dans la fiche : « Objet 26_INT_140 – Grand Conseil – Vigie Vaud »', () => {
		expect(titreFiche(gc.nom, { couche: 'conseils', element: 'vd/26_INT_140' }, COUCHES)).toBe(
			'Objet 26_INT_140 – Grand Conseil – Vigie Vaud'
		);
		expect(titreFiche(gc.nom, { couche: 'conseils', element: 'vd/2026-10-06' }, COUCHES)).toBe(
			'Séance du 6 octobre 2026 – Grand Conseil – Vigie Vaud'
		);
	});
});
