import { describe, expect, it } from 'vitest';
import { LUTRY, PULLY } from '#tests/faux-canton.js';
import { ligneObjet } from '#tests/faux-conseils.js';
import { communesNommees, origineDans, signalement } from './rattachements.js';

const communes = [PULLY, LUTRY];

describe('communes nommées d’un Objet du Grand Conseil', () => {
	it('donne leurs noms dans l’ordre du rattachement', () => {
		const rattachees = [
			{ ofs: LUTRY.bfs, origine: 'titre' as const },
			{ ofs: PULLY.bfs, origine: 'document' as const }
		];

		expect(communesNommees(rattachees, communes)).toEqual(['Lutry', 'Pully']);
	});

	it('passe une commune que l’index du site ne connaît plus, et ne nomme rien pour un Objet sans commune', () => {
		expect(communesNommees([{ ofs: 9999, origine: 'titre' }, { ofs: PULLY.bfs, origine: 'titre' }], communes)).toEqual([
			'Pully'
		]);
		expect(communesNommees([], communes)).toEqual([]);
	});
});

describe('origine du rattachement à une commune', () => {
	const objet = ligneObjet({
		communes: [
			{ ofs: LUTRY.bfs, origine: 'titre' },
			{ ofs: PULLY.bfs, origine: 'document' },
			{ ofs: 5586, origine: 'correction' }
		]
	});

	it('dit si la commune est nommée dans le titre ou citée dans un document', () => {
		expect(origineDans(objet, LUTRY.bfs)).toBe('nommée dans le titre');
		expect(origineDans(objet, PULLY.bfs)).toBe('citée dans un document');
	});

	it('dit d’une correction qu’elle est rattachée à la main, et ne dit rien d’une commune qui n’est pas rattachée', () => {
		expect(origineDans(objet, 5586)).toBe('rattachée à la main');
		expect(origineDans(objet, 5624)).toBeNull();
	});
});

describe('signaler une erreur de rattachement', () => {
	const lire = (lien: string) => {
		const [adresse, requete] = lien.split('?');
		const params = new URLSearchParams(requete);
		return { adresse, objet: params.get('subject'), corps: params.get('body') };
	};

	it('ouvre un courriel pré-rempli : « Rattachement 26_INT_140 », la clé et les communes nommées dans le corps', () => {
		const lien = signalement('vd/26_INT_140', ['Pully', 'Lutry'], 'contact@vigie.test');
		const { adresse, objet, corps } = lire(lien);

		expect(adresse).toBe('mailto:contact@vigie.test');
		expect(objet).toBe('Rattachement 26_INT_140');
		expect(corps).toContain('Clé : vd/26_INT_140');
		expect(corps).toContain('Communes nommées : Pully, Lutry');
	});

	it('dit « aucune » quand l’Objet ne nomme aucune commune, et encode les espaces en %20, pas en +', () => {
		const lien = signalement('vd/26_INT_140', [], 'contact@vigie.test');

		expect(lire(lien).corps).toContain('Communes nommées : aucune');
		expect(lien).not.toContain('+');
		expect(lien).toContain('subject=Rattachement%2026_INT_140');
	});
});
