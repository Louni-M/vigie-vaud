import { describe, expect, it } from 'vitest';
import { teteCommune, titreFiche } from './tete.js';
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

describe('titre de la page, qui suit la fiche ouverte', () => {
	const permis = couche('permis', { titre: (element, commune) => `Dossier n° ${element} – ${commune} – Vigie Vaud` });
	const sansTitre = couche('routes');

	it('est celui de la commune quand aucun élément n’est ouvert', () => {
		expect(titreFiche(PULLY, null, [permis])).toBe('Pully – Vigie Vaud');
	});
	it('est celui que la couche donne à l’élément ouvert, dans la commune du chemin', () => {
		expect(titreFiche(PULLY, { couche: 'permis', element: '248845' }, [permis])).toBe(
			'Dossier n° 248845 – Pully – Vigie Vaud'
		);
	});
	it('reste celui de la commune pour une couche qui ne titre pas ses éléments', () => {
		expect(titreFiche(PULLY, { couche: 'routes', element: 'A9' }, [permis, sansTitre])).toBe('Pully – Vigie Vaud');
	});
});
