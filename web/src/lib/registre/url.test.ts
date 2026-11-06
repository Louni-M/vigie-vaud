import { describe, expect, it } from 'vitest';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';
import type { Codec, CoucheInscrite } from './types.js';

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
	activeParDefaut: false,
	icone: { signe: id, couleur: '#000' },
	composants: { Carte: () => Promise.reject(new Error('non chargé')) },
	...champs
});

const onglet = () => Promise.reject(new Error('non chargé'));

/** Registre factice : `a` active par défaut avec codec et éléments, `b` inactive avec un onglet, `h` permanente. */
const COUCHES = [
	couche('a', { activeParDefaut: true, codec: codecX, cleElement: 'd' }),
	couche('b', { composants: { Carte: onglet, Onglet: onglet } }),
	couche('h', { permanente: true, activeParDefaut: true })
];

const DEFAUTS: EtatUrl = {
	actives: ['a', 'h'],
	vue: null,
	ouvert: null,
	parametres: { a: { x: '' } },
	volet: 'fil',
	affichage: null,
	onglet: null
};

const lire = (q: string) => lireUrl(COUCHES, new URLSearchParams(q));

describe('adresse du registre', () => {
	it('n’écrit rien pour l’état par défaut', () => {
		expect(ecrireUrl(COUCHES, DEFAUTS)).toBe('');
		expect(lire('')).toEqual(DEFAUTS);
	});

	it.each<[string, Partial<EtatUrl>, string]>([
		['couche activée', { actives: ['a', 'b', 'h'] }, '?couches=a,b'],
		['couche désactivée', { actives: ['h'] }, '?couches='],
		['vue', { vue: { lat: 46.51965, lon: 6.63229, zoom: 14.5 } }, '?vue=46.51965,6.63229,14.50'],
		['élément ouvert', { ouvert: { couche: 'a', element: '248845' } }, '?d=248845'],
		['paramètres d’une couche', { parametres: { a: { x: 'oui' } } }, '?x=oui'],
		['volet d’une couche', { volet: 'b' }, '?volet=b'],
		['aucun volet', { volet: null }, '?volet='],
		['vue du téléphone', { affichage: 'couches' }, '?affichage=couches'],
		['onglet de la fiche', { onglet: 'b' }, '?onglet=b'],
		[
			'élément, volet, vue et onglet ensemble',
			{ ouvert: { couche: 'a', element: '7' }, volet: null, affichage: 'carte', onglet: 'b' },
			'?d=7&volet=&affichage=carte&onglet=b'
		]
	])('aller-retour : %s', (_, changes, attendu) => {
		const e = { ...DEFAUTS, ...changes };
		expect(ecrireUrl(COUCHES, e)).toBe(attendu);
		expect(lire(attendu.slice(1))).toEqual(e);
	});

	it('écrit en clair la barre oblique d’une clé d’élément (`?c=5586/POS25-115`)', () => {
		const couches = [...COUCHES, couche('c', { activeParDefaut: true, cleElement: 'c' })];
		const e = { ...DEFAUTS, actives: ['a', 'h', 'c'], ouvert: { couche: 'c', element: '5586/POS25-115' } };

		expect(ecrireUrl(couches, e)).toBe('?c=5586/POS25-115');
		expect(lireUrl(couches, new URLSearchParams('c=5586/POS25-115'))).toEqual(e);
		expect(lireUrl(couches, new URLSearchParams('c=5586%2FPOS25-115')).ouvert).toEqual(e.ouvert);
	});

	it('garde toujours une couche permanente, sans l’écrire', () => {
		expect(lire('couches=b').actives).toEqual(['b', 'h']);
		expect(ecrireUrl(COUCHES, { ...DEFAUTS, actives: ['a'] })).toBe('');
	});

	it('ignore les couches inconnues et une vue invalide', () => {
		expect(lire('couches=b,zzz&vue=46.5,abc,12')).toEqual({ ...DEFAUTS, actives: ['b', 'h'] });
	});

	it('garde le fil ouvert pour un volet inconnu, et ignore une vue du téléphone ou un onglet inconnus', () => {
		expect(lire('volet=zzz&affichage=plan&onglet=zzz')).toEqual(DEFAUTS);
	});

	it('n’accepte comme onglet qu’une couche qui en a un', () => {
		expect(lire('onglet=a').onglet).toBeNull();
		expect(lire('onglet=b').onglet).toBe('b');
	});

	it('accepte le fil comme volet sans l’écrire', () => {
		expect(lire('volet=fil').volet).toBe('fil');
		expect(ecrireUrl(COUCHES, { ...DEFAUTS, volet: 'fil' })).toBe('');
	});
});
