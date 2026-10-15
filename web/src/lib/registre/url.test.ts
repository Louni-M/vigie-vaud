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

/** Registre factice : `a` active par défaut avec codec et éléments, `b` inactive, `h` permanente. */
const COUCHES = [
	couche('a', { activeParDefaut: true, codec: codecX, cleElement: 'd' }),
	couche('b'),
	couche('h', { permanente: true, activeParDefaut: true })
];

const DEFAUTS: EtatUrl = { actives: ['a', 'h'], vue: null, ouvert: null, parametres: { a: { x: '' } } };

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
		['paramètres d’une couche', { parametres: { a: { x: 'oui' } } }, '?x=oui']
	])('aller-retour : %s', (_, changes, attendu) => {
		const e = { ...DEFAUTS, ...changes };
		expect(ecrireUrl(COUCHES, e)).toBe(attendu);
		expect(lire(attendu.slice(1))).toEqual(e);
	});

	it('garde toujours une couche permanente, sans l’écrire', () => {
		expect(lire('couches=b').actives).toEqual(['b', 'h']);
		expect(ecrireUrl(COUCHES, { ...DEFAUTS, actives: ['a'] })).toBe('');
	});

	it('ignore les couches inconnues et une vue invalide', () => {
		expect(lire('couches=b,zzz&vue=46.5,abc,12')).toEqual({ ...DEFAUTS, actives: ['b', 'h'] });
	});
});
