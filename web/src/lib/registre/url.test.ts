import { describe, expect, it } from 'vitest';
import { ecrireUrl, lireUrl, SOMMAIRE, type EtatUrl } from './url.js';
import type { Codec, CoucheInscrite, Rubrique } from './types.js';

/** Codec factice : un seul paramètre `x`, vide par défaut. */
const codecX: Codec<{ x: string }> = {
	cles: ['x'],
	lire: (p) => ({ x: p.get('x') ?? '' }),
	ecrire: ({ x }) => (x ? [['x', x]] : [])
};

const couche = (id: string, champs: Partial<CoucheInscrite> = {}): CoucheInscrite => ({
	id,
	nom: id,
	sources: [],
	permanente: false,
	composants: { Carte: () => Promise.reject(new Error('non chargé')) },
	...champs
});

const rubrique = (id: string, champs: Partial<Rubrique> = {}): Rubrique => ({
	id,
	nom: id,
	phrase: '',
	rang: 0,
	unite: { un: '', plusieurs: '' },
	portee: 'zone',
	compteur: () => Promise.reject(new Error('non chargé')),
	...champs
});

const onglet = () => Promise.reject(new Error('non chargé'));

/**
 * Registre factice : `a`, avec codec et éléments (`?d=`), a une rubrique à volet ; `b` a un onglet et deux rubriques,
 * la sienne à volet et une fiche propre `f`, où vont ses éléments (`?e=`) commençant par « f » ; `h` est permanente,
 * sans rubrique.
 */
const COUCHES = [
	couche('a', { codec: codecX, cleElement: 'd', rubriques: [rubrique('a')] }),
	couche('b', {
		cleElement: 'e',
		composants: { Carte: onglet, Onglet: onglet },
		rubriques: [rubrique('b'), rubrique('f', { fiche: 'f' })],
		rubriqueDe: (element) => (element.startsWith('f') ? 'f' : 'b')
	}),
	couche('h', { permanente: true })
];

const DEFAUTS: EtatUrl = {
	vue: null,
	ouvert: null,
	parametres: { a: { x: '' } },
	panneau: SOMMAIRE,
	affichage: null,
	onglet: null
};

const lire = (q: string) => lireUrl(COUCHES, new URLSearchParams(q));

describe('adresse du registre', () => {
	it('n’écrit rien pour l’état par défaut : le sommaire, sans élément ouvert', () => {
		expect(ecrireUrl(COUCHES, DEFAUTS)).toBe('');
		expect(lire('')).toEqual(DEFAUTS);
	});

	it.each<[string, Partial<EtatUrl>, string]>([
		['vue', { vue: { lat: 46.51965, lon: 6.63229, zoom: 14.5 } }, '?vue=46.51965,6.63229,14.50'],
		['élément ouvert dans sa rubrique', { ouvert: { couche: 'a', element: '248845' }, panneau: 'a' }, '?d=248845'],
		['élément ouvert au sommaire', { ouvert: { couche: 'a', element: '7' } }, '?d=7&volet=sommaire'],
		['élément ouvert dans une autre rubrique', { ouvert: { couche: 'a', element: '7' }, panneau: 'b' }, '?d=7&volet=b'],
		['élément d’une rubrique sans volet, au sommaire', { ouvert: { couche: 'b', element: 'f1' } }, '?e=f1'],
		['paramètres d’une couche', { parametres: { a: { x: 'oui' } } }, '?x=oui'],
		['rubrique ouverte', { panneau: 'b' }, '?volet=b'],
		['vue du téléphone', { affichage: 'carte' }, '?affichage=carte'],
		['onglet de la fiche', { onglet: 'b' }, '?onglet=b'],
		[
			'élément, rubrique, vue et onglet ensemble',
			{ ouvert: { couche: 'a', element: '7' }, panneau: 'b', affichage: 'carte', onglet: 'b' },
			'?d=7&volet=b&affichage=carte&onglet=b'
		]
	])('aller-retour : %s', (_, changes, attendu) => {
		const e = { ...DEFAUTS, ...changes };
		expect(ecrireUrl(COUCHES, e)).toBe(attendu);
		expect(lire(attendu.slice(1))).toEqual(e);
	});

	it('ouvre la rubrique de l’élément que l’adresse ouvre, quand elle n’en nomme aucune', () => {
		expect(lire('d=255360')).toMatchObject({ ouvert: { couche: 'a', element: '255360' }, panneau: 'a' });
		expect(lire('e=12').panneau).toBe('b');
		expect(lire('e=f1').panneau).toBe(SOMMAIRE);
	});

	it('préfère la rubrique que nomme l’adresse à celle de l’élément', () => {
		expect(lire('d=7&volet=b').panneau).toBe('b');
		expect(lire('d=7&volet=sommaire').panneau).toBe(SOMMAIRE);
	});

	it.each(['fil', 'h', '', 'zzz', 'f', 'sommaire'])('donne le sommaire pour volet=%s', (volet) => {
		expect(lire(`volet=${volet}`).panneau).toBe(SOMMAIRE);
	});

	it('lit les anciennes adresses à couches= sans les écrire', () => {
		expect(lire('couches=a,b')).toEqual(DEFAUTS);
		expect(lire('couches=&volet=a')).toEqual({ ...DEFAUTS, panneau: 'a' });
	});

	it('écrit en clair la barre oblique d’une clé d’élément (`?c=5586/POS25-115`)', () => {
		const couches = [...COUCHES, couche('c', { cleElement: 'c' })];
		const e = { ...DEFAUTS, ouvert: { couche: 'c', element: '5586/POS25-115' } };

		expect(ecrireUrl(couches, e)).toBe('?c=5586/POS25-115');
		expect(lireUrl(couches, new URLSearchParams('c=5586/POS25-115'))).toEqual(e);
		expect(lireUrl(couches, new URLSearchParams('c=5586%2FPOS25-115')).ouvert).toEqual(e.ouvert);
	});

	it('ignore une vue invalide, une vue du téléphone ou un onglet inconnus', () => {
		expect(lire('vue=46.5,abc,12&affichage=plan&onglet=zzz')).toEqual(DEFAUTS);
	});

	it('n’accepte comme onglet qu’une couche qui en a un', () => {
		expect(lire('onglet=a').onglet).toBeNull();
		expect(lire('onglet=b').onglet).toBe('b');
	});
});
