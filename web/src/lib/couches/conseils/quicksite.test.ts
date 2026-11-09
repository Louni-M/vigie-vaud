import { describe, expect, it } from 'vitest';
import { mentionNonPublies, noteDeNiveau, piedDeFiche } from './source.js';
import { conseilsCouverts, phraseSitesLus, PLATEFORMES, SOURCES, source } from '#lib/sources.js';
import { objet } from '#tests/faux-conseils.js';

// Ce que l'étape Quicksite de J3 apporte à l'interface, sur les déclarations réelles de `sources.json` : rien de
// propre à la plateforme, la couche Conseils lisant tout de `sources.json`.
describe('communes Quicksite de sources.json', () => {
	it('« Conseils couverts » compte les communes lues par plateforme, sans les non couvertes', () => {
		expect(phraseSitesLus(conseilsCouverts(SOURCES, PLATEFORMES).sites)).toBe(
			'et 46 communes dont Vigie Vaud lit le site : i-web (19), Quicksite (27)'
		);
	});

	it('Vevey, en séances seulement, a sa note vers la page de ses Séances sur le site de la Ville', () => {
		expect(noteDeNiveau(source('site-5890'))).toEqual({
			niveau: 'Séances seulement',
			suite: 'les objets sont sur le site de la commune ›',
			lien: 'https://www.vevey.ch/vie-politique/conseil-communal/seances-passees-et-videos'
		});
	});

	it('Montreux, en objets et séances, n’a pas de note, et ses Objets sans auteur·e n’ont pas de mention', () => {
		expect(noteDeNiveau(source('site-5886'))).toBeNull();
		expect(mentionNonPublies('5886', objet({ statut: null, contributeurs: [] }))).toBeNull();
	});

	it('un préavis de Founex, en séances et préavis, dit que statut et auteur·e·s ne sont pas publiés', () => {
		expect(mentionNonPublies('5717', objet({ statut: null, contributeurs: [] }))).toBe(
			'Statut et auteur·e·s : non publiés par le site de la commune'
		);
	});

	it('le pied de fiche de Montreux renvoie au site de son conseil', () => {
		expect(piedDeFiche('5886')).toEqual({
			texte: 'Source : site de la commune de Montreux',
			lien: 'https://www.conseilmontreux.ch/'
		});
	});
});
