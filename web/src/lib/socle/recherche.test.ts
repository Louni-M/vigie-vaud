import { describe, expect, it } from 'vitest';
import { chercherCommunes } from './recherche.js';
import { commune } from '#tests/faux-canton.js';
import type { AncienNom, Commune } from '#lib/types.js';

const ancienne = (nom: string, slug: string, annee = 2011): AncienNom => ({ nom, slug, type: 'Ancienne commune', annee });
const avec = (c: Commune, anciens: AncienNom[]): Commune => ({ ...c, anciens });

const BEL = avec(commune(5613, 'Bourg-en-Lavaux', [6.68, 46.44, 6.76, 46.52]), [
	ancienne('Cully', 'cully'),
	ancienne('Epesses', 'epesses'),
	ancienne('Villette (Lavaux)', 'villette-lavaux')
]);
const PULLY = commune(5590, 'Pully', [6.62, 46.49, 6.69, 46.53]);

const libelles = (communes: Commune[], saisie: string) => chercherCommunes(communes, saisie).map((r) => r.label);

describe('recherche des communes', () => {
	it('retrouve une ancienne commune et mène à la commune actuelle (« Cully → Bourg-en-Lavaux »)', () => {
		const [r] = chercherCommunes([PULLY, BEL], 'cully');
		expect(r.label).toBe('Cully → Bourg-en-Lavaux');
		expect(r.commune.slug).toBe('bourg-en-lavaux');
	});

	it('propose d’abord les communes actuelles qui correspondent, puis les anciennes communes', () => {
		const villars = commune(5649, 'Villars-Sainte-Croix', [6.55, 46.56, 6.58, 46.58]);
		expect(libelles([BEL, PULLY, villars], 'vill')).toEqual(['Villars-Sainte-Croix', 'Villette (Lavaux) → Bourg-en-Lavaux']);
	});

	it('ne repropose pas par un ancien nom une commune déjà proposée (« Yverdon »)', () => {
		const yverdon = avec(commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]), [
			{ nom: 'Yverdon', slug: 'yverdon', type: 'Ancien nom', annee: 1982 }
		]);
		expect(libelles([BEL, yverdon], 'yverdon')).toEqual(['Yverdon-les-Bains']);
	});

	it('ne cherche rien avant deux lettres', () => {
		expect(libelles([PULLY, BEL], 'c')).toEqual([]);
		expect(libelles([PULLY, BEL], ' c ')).toEqual([]);
	});

	it('garde au plus quatre communes actuelles et trois anciennes communes', () => {
		const communes = [
			...['Bex', 'Bexo', 'Bexon', 'Bexonne', 'Bexonnes'].map((n, i) => commune(i, n, [6, 46, 7, 47])),
			avec(commune(9, 'Ailleurs', [6, 46, 7, 47]), ['Lebex', 'Labex', 'Lobex', 'Lubex'].map((n) => ancienne(n, n.toLowerCase())))
		];
		expect(libelles(communes, 'bex')).toEqual([
			'Bex',
			'Bexo',
			'Bexon',
			'Bexonne',
			'Lebex → Ailleurs',
			'Labex → Ailleurs',
			'Lobex → Ailleurs'
		]);
	});
});
