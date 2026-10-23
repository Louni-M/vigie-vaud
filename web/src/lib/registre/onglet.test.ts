import { describe, expect, it } from 'vitest';
import { messageNonCouvert, nomOnglet, sourcesDeLOnglet } from './onglet.js';
import { coucheConseils } from '#lib/couches/conseils/index.js';
import { couchePermis } from '#lib/couches/permis/index.js';
import type { Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import type { CoucheInscrite } from './types.js';
import { commune } from '#tests/faux-canton.js';
import { sourceSite } from '#tests/faux-conseils.js';
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
		const sources = [...SOURCES, site];
		const couche = { ...coucheConseils, sources: [...coucheConseils.sources, site.id] };
		const imports = { version: 1 as const, genere: '2026-10-23T05:17:00Z', conseils: { '5643': '2026-10-23T05:17:00Z' } };
		const maintenant = new Date('2026-10-23T11:30:00Z');

		const badges = sourcesDeLOnglet(couche, sources, 5643).map((s) =>
			libelleBadge(s, { derniere: dernierImport(imports, s), erreur: null }, maintenant)
		);

		expect(badges).toEqual(['importé il y a 6 h · Site de Préverenges', 'dernier import inconnu · Grand Conseil']);
	});

	it('dans une fiche propre, seulement les sources qui portent sur tout le canton', () => {
		expect(noms(coucheConseils, null)).toEqual(['Grand Conseil']);
		expect(noms(couchePermis, null)).toEqual(['CAMAC']);
	});
});

describe('« Non couvert » en tête de l’onglet', () => {
	it('dit ce qui manque, dans les mots de la couche, sans lien', () => {
		const couche = { ...couchePermis, nonCouvert: () => 'la commune ne publie pas ses permis.' };

		expect(messageNonCouvert(couche, BUSSIGNY)).toEqual({ texte: 'la commune ne publie pas ses permis.' });
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
			texte: 'la commune publie ses permis sur son site.',
			lien: { texte: 'Les permis sur le site de la commune ›', url: 'https://www.exemple-vd.ch/permis' }
		});
	});

	it('sinon, que la couche n’a pas de source pour la commune', () => {
		expect(messageNonCouvert(couchePermis, BUSSIGNY)).toEqual({
			texte: 'la couche Permis n’a pas de source pour Bussigny.'
		});
	});
});

describe('nom d’un onglet et du fil d’Ariane', () => {
	it('est le libellé d’onglet de la couche : « Conseil », quand le volet et le rail disent « Conseils »', () => {
		expect([coucheConseils.nom, nomOnglet(coucheConseils)]).toEqual(['Conseils', 'Conseil']);
	});

	it('est à défaut le nom de la couche', () => {
		expect(nomOnglet(couchePermis)).toBe('Permis');
	});
});
