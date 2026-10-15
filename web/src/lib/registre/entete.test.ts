import { describe, expect, it } from 'vitest';
import { enteteFiche } from './entete.js';
import { commune } from '#tests/faux-canton.js';
import type { AncienNom } from '#lib/types.js';

const ancienne = (nom: string, annee = 2011): AncienNom => ({ nom, slug: nom.toLowerCase(), type: 'Ancienne commune', annee });
const ancienNom = (nom: string, annee = 1982): AncienNom => ({ nom, slug: nom.toLowerCase(), type: 'Ancien nom', annee });

describe('en-tête de la fiche commune', () => {
	it('donne l’adresse de l’hôtel de ville', () => {
		const pully = { ...commune(5590, 'Pully', [6.62, 46.49, 6.69, 46.53]), adresse: 'Avenue du Prieuré 2, 1009 Pully' };
		expect(enteteFiche(pully).siege).toBe('Avenue du Prieuré 2, 1009 Pully');
	});

	it('dit « position approximative » quand le marqueur n’est pas sur le siège', () => {
		const lutry = { ...commune(5606, 'Lutry', [6.67, 46.45, 6.72, 46.54]), adresse: '' };
		expect(enteteFiche(lutry).siege).toBeNull();
	});

	it('liste les anciennes communes, puis les anciens noms', () => {
		const bel = {
			...commune(5613, 'Bourg-en-Lavaux', [6.68, 46.44, 6.76, 46.52]),
			anciens: ['Cully', 'Epesses', 'Grandvaux', 'Riex', 'Villette (Lavaux)'].map((n) => ancienne(n))
		};
		const yverdon = {
			...commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]),
			anciens: [ancienne('Gressy'), ancienNom('Yverdon')]
		};
		expect(enteteFiche(bel).anciens).toEqual([
			'Anciennes communes : Cully, Epesses, Grandvaux, Riex, Villette (Lavaux)'
		]);
		expect(enteteFiche(yverdon).anciens).toEqual(['Ancienne commune : Gressy', 'Ancien nom : Yverdon']);
		expect(enteteFiche(commune(5511, 'Assens', [6.6, 46.6, 6.7, 46.7])).anciens).toEqual([]);
	});
});
