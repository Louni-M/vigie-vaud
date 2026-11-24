import { describe, expect, it } from 'vitest';
import { nombre } from '#lib/almanach/typographie.js';
import { COUCHES } from './couches.js';
import { phraseCompte, rubriqueDeLElement, rubriquesDuSommaire } from './rubriques.js';
import type { CoucheInscrite, Rubrique } from './types.js';

const ids = (couches: readonly CoucheInscrite[]) => rubriquesDuSommaire(couches).map(({ rubrique }) => rubrique.id);

const rubrique = (id: string, rang: number, champs: Partial<Rubrique> = {}): Rubrique => ({
	id,
	nom: id,
	phrase: '',
	rang,
	unite: { un: 'élément', plusieurs: 'éléments' },
	portee: 'zone',
	compteur: async () => () => ({ etat: 'chargement' }),
	...champs
});

const couche = (id: string, rubriques: Rubrique[]): CoucheInscrite => ({
	id,
	nom: id,
	sources: [],
	permanente: false,
	activeParDefaut: false,
	icone: { signe: '', couleur: '' },
	rubriques,
	composants: { Carte: async () => ({ default: () => ({}) }) }
});

describe('rubriques du sommaire', () => {
	it('sortent dans l’ordre Permis de construire, Routes, Conseils communaux, Grand Conseil', () => {
		expect(rubriquesDuSommaire(COUCHES).map(({ rubrique }) => rubrique.nom)).toEqual([
			'Permis de construire',
			'Routes',
			'Conseils communaux',
			'Grand Conseil'
		]);
	});

	it('suivent leur rang, pas l’ordre de dessin des couches', () => {
		expect(ids([couche('a', [rubrique('a', 3)]), couche('b', [rubrique('b', 1), rubrique('b2', 2)])])).toEqual([
			'b',
			'b2',
			'a'
		]);
	});

	it('accueillent la rubrique d’une couche nouvelle sans autre changement', () => {
		const trains = couche('trains', [rubrique('trains', 35)]);
		expect(ids([...COUCHES, trains])).toEqual(['permis', 'routes', 'conseils', 'trains', 'grand-conseil']);
	});

	it('portent l’identifiant de leur couche quand elles ouvrent son volet, au plus une par couche', () => {
		for (const c of COUCHES) {
			const aVolet = (c.rubriques ?? []).filter((r) => !r.fiche);
			expect(aVolet.length).toBeLessThanOrEqual(1);
			for (const r of aVolet) expect(r.id).toBe(c.id);
		}
	});

	it('n’ouvrent une fiche propre que si leur couche la déclare', () => {
		for (const c of COUCHES)
			for (const r of c.rubriques ?? []) if (r.fiche) expect(r.fiche).toBe(c.fiche?.id);
	});
});

describe('rubrique d’un élément', () => {
	it('est celle que sa couche nomme d’après sa clé', () => {
		expect(rubriqueDeLElement(COUCHES, { couche: 'conseils', element: 'vd/26_INT_140' })?.rubrique.id).toBe(
			'grand-conseil'
		);
		expect(rubriqueDeLElement(COUCHES, { couche: 'conseils', element: '5586/POS25-115' })?.rubrique.id).toBe(
			'conseils'
		);
	});

	it('est la première de sa couche sinon', () => {
		expect(rubriqueDeLElement(COUCHES, { couche: 'permis', element: '255360' })?.rubrique.id).toBe('permis');
		expect(rubriqueDeLElement(COUCHES, { couche: 'routes', element: '12' })?.rubrique.id).toBe('routes');
	});

	it('n’existe pas pour une couche sans rubrique', () => {
		expect(rubriqueDeLElement(COUCHES, { couche: 'hotels-de-ville', element: 'x' })).toBeNull();
		expect(rubriqueDeLElement(COUCHES, { couche: 'inconnue', element: 'x' })).toBeNull();
	});
});

describe('phrase du compte', () => {
	const permis = rubrique('permis', 1, { unite: { un: 'dossier en cours', plusieurs: 'dossiers en cours' } });
	const routes = rubrique('routes', 2, {
		unite: { un: 'restriction de circulation', plusieurs: 'restrictions de circulation', feminin: true }
	});
	const canton = rubrique('gc', 3, { unite: { un: 'texte déposé', plusieurs: 'textes déposés' }, portee: 'canton' });

	it('compte la zone affichée, au singulier comme au pluriel', () => {
		expect(phraseCompte(permis, 1)).toEqual({ nombre: '1', texte: '\u00a0dossier en cours dans la zone affichée' });
		expect(phraseCompte(permis, 1234)).toEqual({
			nombre: nombre.format(1234),
			texte: '\u00a0dossiers en cours dans la zone affichée'
		});
	});

	it('dit « aucun » ou « aucune » sans nombre pour zéro', () => {
		expect(phraseCompte(permis, 0)).toEqual({ nombre: null, texte: 'Aucun dossier en cours dans la zone affichée' });
		expect(phraseCompte(routes, 0)).toEqual({
			nombre: null,
			texte: 'Aucune restriction de circulation dans la zone affichée'
		});
	});

	it('dit qu’elle compte tout le canton', () => {
		expect(phraseCompte(canton, 230)).toEqual({ nombre: '230', texte: '\u00a0textes déposés, pour tout le canton' });
	});
});
