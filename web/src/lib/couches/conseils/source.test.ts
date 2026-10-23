import { describe, expect, it } from 'vitest';
import { mentionNonPublies, noteDeNiveau, piedDeFiche } from './source.js';
import type { DonneeConseil } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import { objet, sourceSite } from '#tests/faux-conseils.js';

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

	it('dit qu’une commune scrapée en séances et préavis a ses autres objets sur son site', () => {
		const source = sourceSite({ conseil: { body_key: '5643', donne: ['preavis', 'seances'] } });
		expect(noteDeNiveau(source)).toEqual({
			niveau: 'Séances et préavis',
			suite: 'les autres objets sont sur le site de la commune ›',
			lien: 'https://www.preverenges.ch/sitzung'
		});
	});

	it('ne dit rien d’une commune scrapée qui donne ses objets et ses séances', () => {
		const source = sourceSite({ conseil: { body_key: '5643', donne: ['objets', 'seances'] } });
		expect(noteDeNiveau(source)).toBeNull();
	});
});

describe('mention du statut et des auteur·e·s dans la fiche d’un Objet', () => {
	const preverenges = (donne: [DonneeConseil, ...DonneeConseil[]]) => [
		...SOURCES,
		sourceSite({ conseil: { body_key: '5643', donne } })
	];
	const preavis = objet({ numero: '12-2026', type: 'Préavis', statut: null, contributeurs: [], etapes: [] });

	it('dit qu’un préavis scrapé sans statut ni auteur·e n’en a pas parce que le site ne les publie pas', () => {
		expect(mentionNonPublies('5643', preavis, preverenges(['preavis', 'seances']))).toBe(
			'Statut et auteur·e·s : non publiés par le site de la commune'
		);
	});

	it('ne dit rien d’un Objet scrapé dont le site publie le statut ou les auteur·e·s', () => {
		const sources = preverenges(['objets', 'seances']);
		expect(mentionNonPublies('5643', { ...preavis, statut: { libelle: 'Déposé', date: null } }, sources)).toBeNull();
		const auteur = { nom: 'Yann Exemple', parti: null, role: null, sorte: 'personne' as const };
		expect(mentionNonPublies('5643', { ...preavis, contributeurs: [auteur] }, sources)).toBeNull();
	});

	it('ne dit rien d’un Objet d’OpenParlData, même sans statut', () => {
		expect(mentionNonPublies('5586', preavis, preverenges(['seances']))).toBeNull();
	});
});
