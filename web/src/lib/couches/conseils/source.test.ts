import { describe, expect, it } from 'vitest';
import { noteDeNiveau, piedDeFiche } from './source.js';
import { SOURCES } from '#lib/sources.js';
import { sourceSite } from '#tests/faux-conseils.js';

// Les sources réelles de `sources.json`, et une commune i-web en séances seules (Préverenges).
const AVEC_SITE = [...SOURCES, sourceSite()];

describe('pied de la fiche d’un Objet ou d’une Séance', () => {
	it('nomme le site de la commune d’un conseil scrapé, avec le lien de son attribution', () => {
		expect(piedDeFiche('5643', AVEC_SITE)).toEqual({
			texte: 'Source : site de la commune de Préverenges',
			lien: 'https://www.preverenges.ch/conseil'
		});
	});

	it.each(['vd', '5586', '5938'])('reprend l’attribution d’OpenParlData déclarée pour le conseil %s', (conseil) => {
		expect(piedDeFiche(conseil, AVEC_SITE)).toEqual({ texte: 'Source: OpenParlData.ch', lien: 'https://openparldata.ch' });
	});

	it('ne dit rien d’un conseil que sources.json ne déclare pas', () => {
		expect(piedDeFiche('9999', AVEC_SITE)).toBeNull();
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
});
