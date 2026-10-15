import { describe, expect, it } from 'vitest';
import { teteCommune } from './tete.js';
import type { CoucheInscrite } from './types.js';
import type { Commune } from '#lib/types.js';

const couche = (id: string, champs: Partial<CoucheInscrite> = {}): CoucheInscrite => ({
	id,
	nom: id,
	sources: [],
	permanente: false,
	activeParDefaut: false,
	icone: { signe: id, couleur: '#000' },
	composants: { Carte: () => Promise.reject(new Error('non chargé')) },
	...champs
});

const PULLY: Commune = { bfs: 5590, nom: 'Pully', slug: 'pully', habitants: 18900, bbox: [6.62, 46.49, 6.69, 46.53] };

describe('<head> d’une commune', () => {
	it('porte le titre « Pully – Vigie Vaud »', () => {
		expect(teteCommune(PULLY, []).titre).toBe('Pully – Vigie Vaud');
	});

	it('décrit la commune par ce que montrent les couches inscrites', () => {
		const couches = [couche('permis', { resume: 'les permis de construire à l’enquête, en direct depuis le canton' })];
		expect(teteCommune(PULLY, couches).description).toBe(
			'Pully (VD) sur Vigie Vaud : les permis de construire à l’enquête, en direct depuis le canton.'
		);
	});

	it('énumère les couches dans l’ordre du registre, et ignore celles qui ne résument rien', () => {
		const couches = [
			couche('a', { resume: 'les permis' }),
			couche('h'),
			couche('b', { resume: 'les routes' }),
			couche('c', { resume: 'les trains' })
		];
		expect(teteCommune(PULLY, couches).description).toBe('Pully (VD) sur Vigie Vaud : les permis, les routes et les trains.');
	});
});
