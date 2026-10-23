import { describe, expect, it } from 'vitest';
import { coucheConseils } from './index.js';
import { noteDeNiveau, nonCouvertConseils, piedDeFiche, sourcesDeLaCouche } from './source.js';
import { messageNonCouvert } from '#lib/registre/onglet.js';
import { SOURCES } from '#lib/sources.js';
import { commune } from '#tests/faux-canton.js';
import { sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';

// Les sources réelles de `sources.json`, et une commune i-web en séances seules (Préverenges).
const AVEC_SITE = [...SOURCES, sourceSite()];

describe('pied de la fiche d’un Objet ou d’une Séance', () => {
	it('nomme le site de la commune d’un conseil scrapé, avec le lien de son attribution', () => {
		expect(piedDeFiche('5643', AVEC_SITE)).toEqual({
			texte: 'Source : site de la commune de Préverenges',
			lien: 'https://www.preverenges.ch/conseil'
		});
	});

	it.each(['vd', '5586', '5938'])('reprend l’attribution d’OpenParlData déclarée pour le conseil %s', (conseil) => {
		expect(piedDeFiche(conseil, AVEC_SITE)).toEqual({ texte: 'Source: OpenParlData.ch', lien: 'https://openparldata.ch' });
	});

	it('ne dit rien d’un conseil que sources.json ne déclare pas', () => {
		expect(piedDeFiche('9999', AVEC_SITE)).toBeNull();
	});
});

describe('note de niveau sous le nom du conseil', () => {
	it('dit qu’une commune scrapée en séances seulement a ses objets sur son site, avec la page de liste des Séances', () => {
		expect(noteDeNiveau(sourceSite())).toEqual({
			niveau: 'Séances seulement',
			suite: 'les objets sont sur le site de la commune ›',
			lien: 'https://www.preverenges.ch/sitzung'
		});
	});

	it('donne la même note à Yverdon, avec la page de son conseil', () => {
		expect(noteDeNiveau(SOURCES.find((s) => s.id === 'openparldata-5938')!)).toEqual({
			niveau: 'Séances seulement',
			suite: 'les objets sont sur le site de la commune ›',
			lien: 'https://www.yverdon-les-bains.ch/vie-politique/conseil-communal'
		});
	});

	it.each(['openparldata-5586', 'openparldata-vd'])('ne dit rien d’un conseil qui donne tout (%s)', (id) => {
		expect(noteDeNiveau(SOURCES.find((s) => s.id === id)!)).toBeNull();
	});
});

describe('sources de la couche Conseils', () => {
	it('déclare chaque conseil et chaque commune non couverte d’une plateforme retenue, dans l’ordre de sources.json', () => {
		const sources = [...SOURCES, sourceSite(), sourceNonCouverte()];

		expect(sourcesDeLaCouche(sources)).toEqual([
			'openparldata-vd',
			'openparldata-5586',
			'openparldata-5938',
			'site-5643',
			'site-5568'
		]);
	});
});

describe('message « Non couvert » d’une commune', () => {
	const SAINTE_CROIX = commune(5568, 'Sainte-Croix', [6.45, 46.8, 6.55, 46.85]);
	const BUSSIGNY = commune(5624, 'Bussigny', [6.53, 46.54, 6.57, 46.57]);
	const LIEN = { texte: 'Le conseil sur le site de la commune ›', url: 'https://www.sainte-croix.ch/conseil-communal' };

	it.each([
		['preavis_seuls', 'le site de Sainte-Croix ne publie que des préavis.'],
		['rien_en_ligne', 'le site de Sainte-Croix ne publie pas les séances de son conseil.'],
		['demande_commune', 'la commune de Sainte-Croix a demandé que son site ne soit plus lu.'],
		['refus_robots', 'le site de Sainte-Croix refuse les robots.'],
		['nouveau_site', 'le nouveau site de Sainte-Croix n’est pas encore lu.']
	] as const)('d’une plateforme retenue, en %s : la raison et le lien vers le conseil', (raison, texte) => {
		const sources = [...SOURCES, sourceNonCouverte(raison)];

		expect(nonCouvertConseils(SAINTE_CROIX, sources)).toEqual({ texte, lien: LIEN });
	});

	it('élide « de » devant une voyelle', () => {
		const aigle = { bfs: 5401, nom: 'Aigle', site: 'https://www.aigle.ch' };
		const sources = [...SOURCES, sourceNonCouverte('refus_robots', aigle)];

		expect(nonCouvertConseils(commune(5401, 'Aigle', [6.9, 46.3, 7, 46.35]), sources).texte).toBe(
			'le site d’Aigle refuse les robots.'
		);
	});

	it('hors de J3, sans lien : Vigie Vaud ne lit pas encore le site de la commune', () => {
		const sources = [...SOURCES, sourceNonCouverte()];

		expect(nonCouvertConseils(BUSSIGNY, sources)).toEqual({
			texte: 'Vigie Vaud ne lit pas encore le site de cette commune.'
		});
	});

	it('est celui que le registre met en tête de l’onglet Conseil', () => {
		expect(messageNonCouvert(coucheConseils, BUSSIGNY)).toEqual({
			texte: 'Vigie Vaud ne lit pas encore le site de cette commune.'
		});
	});
});
