import { describe, expect, it } from 'vitest';
import { messageNonCouvert, nomOnglet, sourcesDeLOnglet } from './onglet.js';
import { coucheConseils } from '#lib/couches/conseils/index.js';
import { couchePermis } from '#lib/couches/permis/index.js';
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import type { CoucheInscrite } from './types.js';
import { commune } from '#tests/faux-canton.js';
import { avecSources, sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';
import { libelleBadge } from '#lib/fraicheur.js';
import { dernierImport } from '#lib/imports-conseils.js';

const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
const BUSSIGNY = commune(5624, 'Bussigny', [6.53, 46.54, 6.57, 46.57]);

const noms = (couche: CoucheInscrite, bfs: number | null, sources: readonly Source[] = SOURCES) =>
	sourcesDeLOnglet(couche, sources, bfs).map((s) => s.nom_court);

describe('badges sous le nom d’un onglet', () => {
	it('à Lausanne, le conseil de la commune puis le Grand Conseil, qui porte sur le canton', () => {
		expect(noms(coucheConseils, LAUSANNE.bfs)).toEqual(['Conseil de Lausanne', 'Grand Conseil']);
	});

	it('à Bussigny, que le conseil couvert ne concerne pas, seulement le Grand Conseil', () => {
		expect(noms(coucheConseils, BUSSIGNY.bfs)).toEqual(['Grand Conseil']);
	});

	it('pour Permis, la source qui couvre tout le canton, partout', () => {
		expect(noms(couchePermis, LAUSANNE.bfs)).toEqual(['CAMAC']);
		expect(noms(couchePermis, BUSSIGNY.bfs)).toEqual(['CAMAC']);
	});

	it('écarte une source dont la Couverture ne compte pas la commune', () => {
		const source = (id: string, couverture: Source['couverture']): Source => ({
			...SOURCES[0],
			id,
			nom_court: id,
			couverture
		});
		const sources = [source('a', { communes: [5590], mode: 'scrape' }), source('b', { communes: 'canton', mode: 'api' })];
		const couche = { ...couchePermis, sources: ['a', 'b'] };

		expect(noms(couche, 5590, sources)).toEqual(['a', 'b']);
		expect(noms(couche, 5586, sources)).toEqual(['b']);
	});

	it('dans une commune scrapée, le site de la commune, importé comme un conseil d’OpenParlData', () => {
		const site = sourceSite();
		const sources = avecSources(SOURCES, site);
		const couche = { ...coucheConseils, sources: [...new Set([...coucheConseils.sources, site.id])] };
		const imports = { version: 1 as const, genere: '2026-10-23T05:17:00Z', conseils: { '5643': '2026-10-23T05:17:00Z' } };
		const maintenant = new Date('2026-10-23T11:30:00Z');

		const badges = sourcesDeLOnglet(couche, sources, 5643).map((s) =>
			libelleBadge(s, { derniere: dernierImport(imports, s), erreur: null }, maintenant)
		);

		expect(badges).toEqual(['mis à jour il y a 6 h · Site de Préverenges', 'dernière mise à jour inconnue · Grand Conseil']);
	});

	it('dans une commune non couverte, pas de badge pour la source qui la déclare non couverte', () => {
		const nonCouverte = sourceNonCouverte();
		const couche = { ...coucheConseils, sources: [...new Set([...coucheConseils.sources, nonCouverte.id])] };

		expect(noms(couche, 5568, avecSources(SOURCES, nonCouverte))).toEqual(['Grand Conseil']);
	});

	it('dans une fiche propre, seulement les sources qui portent sur tout le canton', () => {
		expect(noms(coucheConseils, null)).toEqual(['Grand Conseil']);
		expect(noms(couchePermis, null)).toEqual(['CAMAC']);
	});
});

describe('message en tête de l’onglet d’une commune non couverte', () => {
	it('dit qu’il n’y a pas encore de données, puis ce qui manque dans les mots de la couche, sans lien', () => {
		const couche = { ...couchePermis, nonCouvert: () => 'la commune ne publie pas ses permis.' };

		expect(messageNonCouvert(couche, BUSSIGNY)).toEqual({
			texte: 'Pas encore de données Permis de construire pour cette commune\u00a0: la commune ne publie pas ses permis.'
		});
	});

	it('avec un lien, quand la couche en donne un', () => {
		const couche = {
			...couchePermis,
			nonCouvert: () => ({
				texte: 'la commune publie ses permis sur son site.',
				lien: { texte: 'Les permis sur le site de la commune ›', url: 'https://www.exemple-vd.ch/permis' }
			})
		};

		expect(messageNonCouvert(couche, BUSSIGNY)).toEqual({
			texte: 'Pas encore de données Permis de construire pour cette commune\u00a0: la commune publie ses permis sur son site.',
			lien: { texte: 'Les permis sur le site de la commune ›', url: 'https://www.exemple-vd.ch/permis' }
		});
	});

	it('sinon, qu’il n’y a pas encore de données pour cette commune', () => {
		expect(messageNonCouvert(couchePermis, BUSSIGNY)).toEqual({
			texte: 'Pas encore de données Permis de construire pour cette commune.'
		});
	});
});

describe('nom d’un onglet et du fil d’Ariane', () => {
	it('est le nom de la rubrique de la couche, comme au sommaire et dans la liste', () => {
		expect(nomOnglet(couchePermis)).toBe('Permis de construire');
		expect(nomOnglet(coucheConseils)).toBe('Conseils communaux');
	});

	it('est, dans une fiche propre, le nom de la rubrique qui l’ouvre', () => {
		expect(nomOnglet(coucheConseils, 'grand-conseil')).toBe('Grand Conseil');
	});

	it('est à défaut le nom de la couche', () => {
		expect(nomOnglet({ nom: 'Trains' })).toBe('Trains');
	});
});
