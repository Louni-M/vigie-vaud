import { describe, expect, it } from 'vitest';
import { carteConseil, compteConseils, compteGrandConseil, lignesConseils, noteAutresCommunes } from './cartes.js';
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
			recents: '2 objets récents',
			seance: 'Prochaine séance : mar. 20 oct.',
			commune: 'lausanne'
		});
	});

	it('dit la dernière Séance quand aucune n’est annoncée, et n’a pas de commune pour le Grand Conseil', () => {
		expect(carteConseil(grandConseil(), COMMUNES)).toMatchObject({
			nom: 'Grand Conseil',
			recents: '1 objet récent',
			seance: 'Dernière séance : mar. 6 oct.',
			commune: null
		});
	});

	it('ne compte pas les Objets d’un conseil qui ne donne que ses Séances', () => {
		expect(carteConseil(conseilYverdon(), COMMUNES)).toMatchObject({
			donne: 'séances seulement',
			recents: null,
			seance: 'Dernière séance : jeu. 1 oct.',
			commune: 'yverdon-les-bains'
		});
	});

	it('compte les préavis récents d’une commune scrapée en séances et préavis', () => {
		const conseil = conseilLausanne({ donne: ['preavis', 'seances'], recents: [ligneObjet()] });
		expect(carteConseil(conseil, COMMUNES)).toMatchObject({ donne: 'séances et préavis', recents: '1 objet récent' });
	});

	it('dit l’absence d’Objet récent et de Séance connue', () => {
		const conseil = conseilLausanne({ recents: [], prochaine_seance: null, derniere_seance: null });
		expect(carteConseil(conseil, COMMUNES)).toMatchObject({ recents: 'aucun objet récent', seance: null });
		expect(carteConseil(conseilLausanne({ recents: [ligneObjet()] }), COMMUNES).recents).toBe('1 objet récent');
	});
});

describe('phrase sur les communes grisées, sous les communes suivies', () => {
	it('dit qu’elles sont grisées sur la carte', () => {
		expect(noteAutresCommunes(298)).toBe(
			'Les 298 autres communes\u00a0: pas de conseil suivi, grisées sur la carte. Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.'
		);
	});
});

describe('lignes des conseils communaux, dans le volet Conseils', () => {
	const conseils = [grandConseil(), conseilYverdon(), conseilLausanne()];

	it('donne une ligne par conseil communal, par nom de commune, sans le Grand Conseil', () => {
		expect(lignesConseils(conseils, COMMUNES, null)).toEqual([
			{
				cle: conseilLausanne().cle,
				commune: 'Lausanne',
				slug: 'lausanne',
				detail: 'objets et séances · prochaine séance mar. 20 oct.'
			},
			{
				cle: conseilYverdon().cle,
				commune: 'Yverdon-les-Bains',
				slug: 'yverdon-les-bains',
				detail: 'séances seulement · dernière séance jeu. 1 oct.'
			}
		]);
	});

	it('ne garde que les communes dont l’hôtel de ville est dans la zone affichée', () => {
		const autourDeLausanne: [number, number, number, number] = [6.5, 46.45, 6.8, 46.65];
		expect(lignesConseils(conseils, COMMUNES, autourDeLausanne).map((l) => l.commune)).toEqual(['Lausanne']);
	});
});

describe('comptes des rubriques Conseils communaux et Grand Conseil', () => {
	const conseils = [grandConseil({ objets: 1234 }), conseilLausanne(), conseilYverdon()];

	it('Conseils communaux compte les communes suivies de la zone, comme la liste du volet', () => {
		const autourDeLausanne: [number, number, number, number] = [6.5, 46.45, 6.8, 46.65];
		expect(compteConseils(conseils, COMMUNES, autourDeLausanne)).toEqual({ etat: 'nombre', nombre: 1 });
		expect(compteConseils(conseils, COMMUNES, [7.0, 46.0, 7.1, 46.1])).toEqual({ etat: 'nombre', nombre: 0 });
	});

	it('Grand Conseil compte tous ses Objets, pour tout le canton, pas les Objets récents', () => {
		expect(compteGrandConseil(conseils)).toEqual({ etat: 'nombre', nombre: 1234 });
	});
});
