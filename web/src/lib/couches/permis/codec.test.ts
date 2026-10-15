import { describe, expect, it } from 'vitest';
import { creerCodec } from './index.js';
import type { Parametres } from './donnees.svelte.js';

/** Codec d'une visite en 2026 : l'historique part par défaut de 2024. */
const codec = creerCodec(2026);

const DEFAUTS: Parametres = {
	statuts: ['enquete', 'procedure'],
	nature: '',
	historique: false,
	depuis: 2024,
	tri: 'recent'
};

const requete = (p: Parametres) => new URLSearchParams(codec.ecrire(p)).toString();
const lire = (q: string) => codec.lire(new URLSearchParams(q));

describe('codec Permis', () => {
	it('n’écrit rien pour les valeurs par défaut', () => {
		expect(codec.ecrire(DEFAUTS)).toEqual([]);
		expect(lire('')).toEqual(DEFAUTS);
	});

	it.each<[string, Partial<Parametres>, string]>([
		['nature', { nature: 'demolition' }, 'nature=demolition'],
		['tri', { tri: 'fin' }, 'tri=fin'],
		['statuts', { statuts: ['procedure'] }, 'statuts=procedure'],
		['aucun statut', { statuts: [] }, 'statuts='],
		['historique', { historique: true, statuts: ['enquete', 'procedure', 'delivre', 'realise', 'abandonne'] }, 'historique=1'],
		['historique filtré', { historique: true, statuts: ['enquete', 'delivre'] }, 'historique=1&statuts=enquete%2Cdelivre'],
		['depuis', { historique: true, depuis: 2010, statuts: ['enquete', 'procedure', 'delivre', 'realise', 'abandonne'] }, 'historique=1&depuis=2010']
	])('aller-retour : %s', (_, changes, attendu) => {
		const p = { ...DEFAUTS, ...changes };
		expect(requete(p)).toBe(attendu);
		expect(lire(attendu)).toEqual(p);
	});

	it('ramène une adresse invalide aux valeurs par défaut', () => {
		expect(lire('nature=piscine&tri=prix&depuis=abc')).toEqual(DEFAUTS);
	});

	it('ne garde que les statuts proposés, sans historique les seuls dossiers en cours', () => {
		expect(lire('statuts=delivre,procedure,inconnu').statuts).toEqual(['procedure']);
		expect(lire('historique=1&statuts=delivre,procedure').statuts).toEqual(['procedure', 'delivre']);
	});

	it('borne l’année de départ de l’historique entre 1999 et l’année en cours', () => {
		expect(lire('historique=1&depuis=1950').depuis).toBe(1999);
		expect(lire('historique=1&depuis=2040').depuis).toBe(2026);
	});
});
