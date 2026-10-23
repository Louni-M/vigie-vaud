import { describe, expect, it } from 'vitest';
import { coucheConseils } from './index.js';
import { mentionNonPublies, noteDeNiveau, nonCouvertConseils, piedDeFiche, sourcesDeLaCouche } from './source.js';
import { messageNonCouvert } from '#lib/registre/onglet.js';
import type { DonneeConseil } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import { commune } from '#tests/faux-canton.js';
import { avecSources, objet, sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';

// Les sources réelles de `sources.json`, où Préverenges est une commune i-web en séances seules.
const AVEC_SITE = avecSources(SOURCES, sourceSite());

describe('pied de la fiche d’un Objet ou d’une Séance', () => {
	it('nomme le site de la commune d’un conseil scrapé, avec le lien de son attribution', () => {
		expect(piedDeFiche('5643', AVEC_SITE)).toEqual({
			texte: 'Source\u00a0: site de la commune de Préverenges',
			lien: 'https://www.preverenges.ch/conseil'
		});
	});

	it.each(['vd', '5586', '5938'])('nomme OpenParlData, « Source : » à l’espace insécable, pour le conseil %s', (conseil) => {
		expect(piedDeFiche(conseil, AVEC_SITE)).toEqual({
			texte: 'Source\u00a0: OpenParlData.ch',
			lien: 'https://openparldata.ch'
		});
	});

	it('ne dit rien d’un conseil que sources.json ne déclare pas', () => {
		expect(piedDeFiche('9999', AVEC_SITE)).toBeNull();
	});

	it('nomme encore le site d’une commune passée non couverte, dont l’archive reste en ligne', () => {
		const sources = avecSources(SOURCES, sourceNonCouverte('demande_commune'));
		expect(piedDeFiche('5568', sources)).toEqual({
			texte: 'Source : site de la commune de Sainte-Croix',
			lien: 'https://www.sainte-croix.ch/conseil-communal'
		});
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

	it('dit qu’une commune scrapée en séances et préavis a ses autres objets sur son site', () => {
		const source = sourceSite({ conseil: { body_key: '5643', donne: ['preavis', 'seances'] } });
		expect(noteDeNiveau(source)).toEqual({
			niveau: 'Séances et préavis',
			suite: 'les autres objets sont sur le site de la commune ›',
			lien: 'https://www.preverenges.ch/sitzung'
		});
	});

	it('ne dit rien d’une commune scrapée qui donne ses objets et ses séances', () => {
		const source = sourceSite({ conseil: { body_key: '5643', donne: ['objets', 'seances'] } });
		expect(noteDeNiveau(source)).toBeNull();
	});
});

describe('mention du statut et des auteur·e·s dans la fiche d’un Objet', () => {
	const preverenges = (donne: [DonneeConseil, ...DonneeConseil[]]) => avecSources(SOURCES, sourceSite({ conseil: { body_key: '5643', donne } }));
	const preavis = objet({ numero: '12-2026', type: 'Préavis', statut: null, contributeurs: [], etapes: [] });

	it('dit qu’un préavis scrapé sans statut ni auteur·e n’en a pas parce que le site ne les publie pas', () => {
		expect(mentionNonPublies('5643', preavis, preverenges(['preavis', 'seances']))).toBe(
			'Statut et auteur·e·s : non publiés par le site de la commune'
		);
	});

	it('ne dit rien d’un Objet scrapé dont le site publie le statut ou les auteur·e·s', () => {
		// Puidoux publie un statut dans son tableau de préavis rédigé : il est montré, sans mention.
		const sources = preverenges(['preavis', 'seances']);
		expect(mentionNonPublies('5643', { ...preavis, statut: { libelle: 'Déposé', date: null } }, sources)).toBeNull();
		const auteur = { nom: 'Yann Exemple', parti: null, role: null, sorte: 'personne' as const };
		expect(mentionNonPublies('5643', { ...preavis, contributeurs: [auteur] }, sources)).toBeNull();
	});

	it('ne dit rien d’un Objet sans statut ni auteur·e d’un conseil scrapé qui publie statuts et auteur·e·s', () => {
		// Le module Objets d'i-web (Blonay - Saint-Légier) : un Objet sans statut n'en a pas, le site ne le cache pas.
		expect(mentionNonPublies('5643', preavis, preverenges(['objets', 'seances']))).toBeNull();
	});

	it.each([['seances'], ['preavis', 'seances']] as [DonneeConseil, ...DonneeConseil[]][])(
		'le dit pour un conseil scrapé en %s',
		(...donne) => {
			expect(mentionNonPublies('5643', preavis, preverenges(donne))).not.toBeNull();
		}
	);

	it('ne dit rien d’un Objet d’OpenParlData, même sans statut', () => {
		expect(mentionNonPublies('5586', preavis, preverenges(['seances']))).toBeNull();
	});
});

describe('sources de la couche Conseils', () => {
	it('déclare chaque conseil et chaque commune non couverte d’une plateforme retenue, dans l’ordre de sources.json', () => {
		const ids = sourcesDeLaCouche(SOURCES);

		expect(ids.slice(0, 7)).toEqual([
			'openparldata-vd',
			'openparldata-5586',
			'openparldata-5938',
			'site-5410',
			'site-5414',
			'site-5458',
			'site-5487' // Lussery-Villars, non couverte
		]);
		expect(ids).toHaveLength(3 + 28);
		expect(ids).toContain('site-5568');
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
		const sources = avecSources(SOURCES, sourceNonCouverte(raison));

		expect(nonCouvertConseils(SAINTE_CROIX, sources)).toEqual({ texte, lien: LIEN });
	});

	it('élide « de » devant une voyelle', () => {
		const aigle = { bfs: 5401, nom: 'Aigle', site: 'https://www.aigle.ch' };
		const sources = avecSources(SOURCES, sourceNonCouverte('refus_robots', aigle));

		expect(nonCouvertConseils(commune(5401, 'Aigle', [6.9, 46.3, 7, 46.35]), sources).texte).toBe(
			'le site d’Aigle refuse les robots.'
		);
	});

	it('hors de J3, sans lien : Vigie Vaud ne lit pas encore le site de la commune', () => {
		const sources = avecSources(SOURCES, sourceNonCouverte());

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
