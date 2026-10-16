import { describe, expect, it } from 'vitest';
import { teteCommune, teteFiche, titreFiche } from './tete.js';
import type { CoucheInscrite } from './types.js';
import { commune } from '#tests/faux-canton.js';
import type { AncienNom } from '#lib/types.js';

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

const PULLY = commune(5590, 'Pully', [6.62, 46.49, 6.69, 46.53]);

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

	it('demande son résumé à une couche dont le résumé dépend de la commune', () => {
		const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
		const conseils = couche('conseils', {
			resume: (c) => (c.bfs === 5586 ? 'les séances de son Conseil communal' : 'les objets du Grand Conseil qui la nomment')
		});
		const couches = [couche('permis', { resume: 'les permis' }), conseils];
		expect(teteCommune(LAUSANNE, couches).description).toBe(
			'Lausanne (VD) sur Vigie Vaud : les permis et les séances de son Conseil communal.'
		);
		expect(teteCommune(PULLY, couches).description).toBe(
			'Pully (VD) sur Vigie Vaud : les permis et les objets du Grand Conseil qui la nomment.'
		);
		expect(teteCommune(LAUSANNE, couches).titre).toBe('Lausanne – Vigie Vaud');
	});

	it('nomme les anciennes communes et les anciens noms', () => {
		const ancienne = (nom: string): AncienNom => ({ nom, slug: nom.toLowerCase(), type: 'Ancienne commune', annee: 2011 });
		const bel = {
			...commune(5613, 'Bourg-en-Lavaux', [6.68, 46.44, 6.76, 46.52]),
			anciens: ['Cully', 'Epesses', 'Grandvaux', 'Riex', 'Villette (Lavaux)'].map(ancienne)
		};
		const yverdon = {
			...commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]),
			anciens: [ancienne('Gressy'), { nom: 'Yverdon', slug: 'yverdon', type: 'Ancien nom' as const, annee: 1982 }]
		};
		const couches = [couche('permis', { resume: 'les permis' })];
		expect(teteCommune(bel, couches).description).toBe(
			'Bourg-en-Lavaux (VD) sur Vigie Vaud : les permis. Anciennes communes : Cully, Epesses, Grandvaux, Riex, Villette (Lavaux).'
		);
		expect(teteCommune(yverdon, couches).description).toBe(
			'Yverdon-les-Bains (VD) sur Vigie Vaud : les permis. Ancienne commune : Gressy. Ancien nom : Yverdon.'
		);
	});
});

describe('titre de la page, qui suit la fiche ouverte', () => {
	const permis = couche('permis', { titre: (element, commune) => `Dossier n° ${element} – ${commune} – Vigie Vaud` });
	const sansTitre = couche('routes');

	it('est celui de la fiche quand aucun élément n’est ouvert', () => {
		expect(titreFiche('Pully', null, [permis])).toBe('Pully – Vigie Vaud');
		expect(titreFiche('Parlement', null, [permis])).toBe('Parlement – Vigie Vaud');
	});
	it('est celui que la couche donne à l’élément ouvert, dans la fiche du chemin', () => {
		expect(titreFiche('Pully', { couche: 'permis', element: '248845' }, [permis])).toBe(
			'Dossier n° 248845 – Pully – Vigie Vaud'
		);
		expect(titreFiche('Parlement', { couche: 'permis', element: '248845' }, [permis])).toBe(
			'Dossier n° 248845 – Parlement – Vigie Vaud'
		);
	});
	it('reste celui de la fiche pour une couche qui ne titre pas ses éléments', () => {
		expect(titreFiche('Pully', { couche: 'routes', element: 'A9' }, [permis, sansTitre])).toBe('Pully – Vigie Vaud');
	});
});

describe('<head> d’une fiche propre', () => {
	const fiche = {
		id: 'parlement',
		chemin: '/parlement',
		nom: 'Parlement',
		sousTitre: 'place du Château',
		description: 'Ce que fait le parlement.',
		position: [6.6, 46.5] as [number, number]
	};

	it('porte le nom de la fiche et la description qu’elle déclare', () => {
		expect(teteFiche(fiche)).toEqual({ titre: 'Parlement – Vigie Vaud', description: 'Ce que fait le parlement.' });
	});
});
