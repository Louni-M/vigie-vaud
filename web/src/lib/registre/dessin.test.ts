import { describe, expect, it } from 'vitest';
import { COUCHES } from './couches.js';
import { coucheDessinee, couchesSurLaCarte } from './dessin.js';
import { SOMMAIRE } from './url.js';

describe('couche dessinée', () => {
	it.each<[string, { panneau: string; ongletCommune: string | null }, string | null]>([
		['sommaire seul', { panneau: SOMMAIRE, ongletCommune: null }, null],
		['rubrique Routes', { panneau: 'routes', ongletCommune: null }, 'routes'],
		['rubrique Conseils communaux', { panneau: 'conseils', ongletCommune: null }, 'conseils'],
		['fiche commune sur son premier onglet', { panneau: SOMMAIRE, ongletCommune: 'permis' }, 'permis'],
		['fiche commune sur l’onglet Routes, rubrique Permis', { panneau: 'permis', ongletCommune: 'routes' }, 'routes'],
		['rubrique Routes, fiche du Grand Conseil (qui n’a pas d’onglet de commune)', { panneau: 'routes', ongletCommune: null }, 'routes'],
		['rubrique inconnue', { panneau: 'zzz', ongletCommune: null }, null]
	])('%s', (_, etat, attendue) => {
		expect(coucheDessinee(COUCHES, etat)).toBe(attendue);
	});
});

describe('couches sur la carte', () => {
	it('sont les hôtels de ville et la couche du marqueur du Grand Conseil, sans couche dessinée', () => {
		expect(couchesSurLaCarte(COUCHES, null)).toEqual(['conseils', 'hotels-de-ville']);
	});

	it('ajoutent la couche dessinée, dans l’ordre du registre', () => {
		expect(couchesSurLaCarte(COUCHES, 'routes')).toEqual(['conseils', 'routes', 'hotels-de-ville']);
		expect(couchesSurLaCarte(COUCHES, 'permis')).toEqual(['permis', 'conseils', 'hotels-de-ville']);
	});
});

