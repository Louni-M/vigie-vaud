import { describe, expect, it } from 'vitest';
import { COUCHES } from './couches.js';
import { coucheDessinee, couchesSurLaCarte, entreesLegende } from './dessin.js';
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

describe('légende de la carte', () => {
	const textes = (dessinee: string | null) => entreesLegende(COUCHES, dessinee).map((e) => e.texte);

	it('nomme au sommaire l’hôtel de ville, ce qu’ouvre un clic, et le Grand Conseil', () => {
		const t = textes(null);
		expect(t).toHaveLength(2);
		expect(t[0]).toMatch(/^Hôtel de ville.*un clic ouvre la fiche de la commune/);
		expect(t[1]).toMatch(/^Grand Conseil/);
	});

	it('ajoute après eux ce que dessine la rubrique Routes', () => {
		expect(textes('routes').slice(2)).toEqual(['Fermeture', 'Déviation', 'Feux', 'Restriction particulière']);
	});

	it('montre les statuts des permis quand la carte les dessine', () => {
		expect(textes('permis').slice(2)).toEqual(['À l’enquête', 'Décision attendue']);
	});

	it('dit ce que grise la rubrique Conseils communaux', () => {
		expect(textes('conseils').slice(2)).toEqual([expect.stringMatching(/^Commune grisée/)]);
	});
});
