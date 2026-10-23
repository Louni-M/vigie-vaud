import { describe, expect, it } from 'vitest';
import { carteConseil, noteAutresCommunes } from './cartes.js';
import { commune } from '#tests/faux-canton.js';
import { conseilLausanne, conseilYverdon, grandConseil, ligneObjet } from '#tests/faux-conseils.js';

const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
const YVERDON = { ...commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]), slug: 'yverdon-les-bains' };
const COMMUNES = [LAUSANNE, YVERDON];

describe('carte d’un conseil couvert, dans le volet Conseils', () => {
	it('dit ce que donne le conseil, ses Objets récents et sa prochaine Séance', () => {
		expect(carteConseil(conseilLausanne(), COMMUNES)).toEqual({
			nom: 'Conseil communal de Lausanne',
			donne: 'objets et séances',
			recents: '2 objets récents',
			seance: 'Prochaine séance : mar. 20 oct.',
			commune: 'lausanne'
		});
	});

	it('dit la dernière Séance quand aucune n’est annoncée, et n’a pas de commune pour le Grand Conseil', () => {
		expect(carteConseil(grandConseil(), COMMUNES)).toMatchObject({
			nom: 'Grand Conseil',
			recents: '1 objet récent',
			seance: 'Dernière séance : mar. 6 oct.',
			commune: null
		});
	});

	it('ne compte pas les Objets d’un conseil qui ne donne que ses Séances', () => {
		expect(carteConseil(conseilYverdon(), COMMUNES)).toMatchObject({
			donne: 'séances seulement',
			recents: null,
			seance: 'Dernière séance : jeu. 1 oct.',
			commune: 'yverdon-les-bains'
		});
	});

	it('compte les préavis récents d’une commune scrapée en séances et préavis', () => {
		const conseil = conseilLausanne({ donne: ['preavis', 'seances'], recents: [ligneObjet()] });
		expect(carteConseil(conseil, COMMUNES)).toMatchObject({ donne: 'séances et préavis', recents: '1 objet récent' });
	});

	it('dit l’absence d’Objet récent et de Séance connue', () => {
		const conseil = conseilLausanne({ recents: [], prochaine_seance: null, derniere_seance: null });
		expect(carteConseil(conseil, COMMUNES)).toMatchObject({ recents: 'aucun objet récent', seance: null });
		expect(carteConseil(conseilLausanne({ recents: [ligneObjet()] }), COMMUNES).recents).toBe('1 objet récent');
	});
});

describe('phrase sur les communes grisées, sous les cartes', () => {
	it('sur bureau, le grisage suit le volet ouvert', () => {
		expect(noteAutresCommunes(298, false)).toBe(
			'Les 298 autres communes : pas de conseil couvert, grisées tant que ce volet est ouvert. Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.'
		);
	});

	it('sur téléphone, il suit « Voir sur la carte »', () => {
		expect(noteAutresCommunes(298, true)).toBe(
			'Les 298 autres communes : pas de conseil couvert, grisées sur la carte par « Voir sur la carte ». Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.'
		);
	});
});
