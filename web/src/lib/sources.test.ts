import { describe, expect, it } from 'vitest';
import { cleConseil, communeDuConseil, grouperSources, listerConseils, nomDuConseil } from './sources.js';
import type { Conseil, Source } from './schema.js';

const source = (id: string): Source => ({
	id,
	nom: `Source ${id}`,
	nom_court: id,
	attribution: { texte: id, lien: `https://exemple.ch/${id}`, licence: 'libre' },
	voie_acces: 'direct',
	fraicheur: 'requete',
	couverture: { communes: 'canton', mode: 'api' }
});

const SOURCES = ['fond', 'permis', 'recherche', 'ucv', 'limites'].map(source);

/** Groupes réduits à leur titre et aux identifiants de leurs sources, pour la lecture. */
const ids = (groupes: ReturnType<typeof grouperSources>) =>
	groupes.map((g) => [g.titre, g.sources.map((s) => s.id)]);

describe('liste Sources d’À propos', () => {
	it('groupe les sources par couche, dans l’ordre du registre, puis les autres sous « Carte et communes »', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis'] },
			{ nom: 'Hôtels de ville', sources: ['ucv'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis']],
			['Hôtels de ville', ['ucv']],
			['Carte et communes', ['fond', 'recherche', 'limites']]
		]);
	});

	it('cite une source partagée sous chaque couche qui la déclare', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis', 'limites'] },
			{ nom: 'Hôtels de ville', sources: ['ucv', 'limites'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis', 'limites']],
			['Hôtels de ville', ['ucv', 'limites']],
			['Carte et communes', ['fond', 'recherche']]
		]);
	});

	it('n’affiche pas de groupe vide', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis'] },
			{ nom: 'Sans source', sources: [] },
			{ nom: 'Tout le reste', sources: ['fond', 'recherche', 'ucv', 'limites'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis']],
			['Tout le reste', ['fond', 'recherche', 'ucv', 'limites']]
		]);
	});
});

describe('conseils couverts, pour À propos', () => {
	const conseil = (id: string, nom: string, donne: Source['conseil']): Source => ({ ...source(id), nom, conseil: donne });
	const sources = [
		source('permis'),
		conseil('gc', 'Grand Conseil (OpenParlData)', { body_key: 'VD', donne: ['objets', 'seances'], groupe: 1965 }),
		source('fond'),
		conseil('yverdon', 'Conseil communal d’Yverdon-les-Bains (OpenParlData)', { body_key: '5938', donne: ['seances'] }),
		conseil('objets', 'Conseil qui ne donne que ses objets', { body_key: '1', donne: ['objets'] })
	];

	it('liste les sources qui ont un bloc conseil, dans l’ordre de sources.json, avec ce que chacune donne', () => {
		expect(listerConseils(sources).map((c) => [c.source.id, c.donne])).toEqual([
			['gc', 'objets et séances'],
			['yverdon', 'séances seulement'],
			['objets', 'objets seulement']
		]);
	});

	it('dit les trois niveaux d’une commune scrapée', () => {
		const niveaux = (['objets', 'preavis'] as const).map((d) =>
			conseil(`site-${d}`, 'Conseil communal (site de la commune)', { body_key: '1', donne: [d, 'seances'] })
		);
		const seules = conseil('site-seances', 'Conseil communal (site de la commune)', { body_key: '2', donne: ['seances'] });
		expect(listerConseils([...niveaux, seules]).map((c) => c.donne)).toEqual([
			'objets et séances',
			'séances et préavis',
			'séances seulement'
		]);
	});

	it('ne liste rien sans bloc conseil', () => {
		expect(listerConseils([source('permis'), source('fond')])).toEqual([]);
	});
});

describe('clé, commune et nom d’un conseil, comme le cron', () => {
	it.each([
		['VD', 'vd', null],
		['5586', '5586', 5586],
		['5938', '5938', 5938]
	])('body_key %s : clé %s, commune %s', (body_key, cle, commune) => {
		const conseil: Conseil = { body_key, donne: ['objets'] };
		expect([cleConseil(conseil), communeDuConseil(conseil)]).toEqual([cle, commune]);
	});

	// Les mêmes cas que `nom_du_conseil` du cron (`pipeline/tests/test_sources.py`), qui écrit le nom de l'index :
	// un cas ajouté d'un côté s'ajoute de l'autre.
	it.each([
		['Grand Conseil (OpenParlData)', 'Grand Conseil'],
		['Conseil communal de Lausanne (OpenParlData)', 'Conseil communal de Lausanne'],
		["Conseil communal d'Yverdon-les-Bains (OpenParlData)", 'Conseil communal d’Yverdon-les-Bains'],
		['Conseil général de Nyon (OpenParlData, essai)', 'Conseil général de Nyon'],
		['Conseil communal (CC) de Morges', 'Conseil communal (CC) de Morges'],
		['Conseil communal de Pully', 'Conseil communal de Pully']
	])('« %s » → « %s »', (nomSource, nom) => {
		expect(nomDuConseil(nomSource)).toBe(nom);
	});
});
