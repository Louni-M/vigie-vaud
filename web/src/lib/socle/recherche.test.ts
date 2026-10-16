import { describe, expect, it } from 'vitest';
import { avecAdresses, chercherCommunes, resultatsLocaux } from './recherche.js';
import { commune } from '#tests/faux-canton.js';
import { COUCHES } from '#lib/registre/couches.js';
import { resultatsCouches } from '#lib/registre/recherche.js';
import type { AncienNom, Commune, Resultat } from '#lib/types.js';

const ancienne = (nom: string, slug: string, annee = 2011): AncienNom => ({ nom, slug, type: 'Ancienne commune', annee });
const avec = (c: Commune, anciens: AncienNom[]): Commune => ({ ...c, anciens });

const BEL = avec(commune(5613, 'Bourg-en-Lavaux', [6.68, 46.44, 6.76, 46.52]), [
	ancienne('Cully', 'cully'),
	ancienne('Epesses', 'epesses'),
	ancienne('Villette (Lavaux)', 'villette-lavaux')
]);
const PULLY = commune(5590, 'Pully', [6.62, 46.49, 6.69, 46.53]);

const libelles = (communes: Commune[], saisie: string) => chercherCommunes(communes, saisie).map((r) => r.libelle);

describe('recherche des communes', () => {
	it('retrouve une ancienne commune et mène à la commune actuelle (« Cully → Bourg-en-Lavaux »)', () => {
		const [r] = chercherCommunes([PULLY, BEL], 'cully');
		expect(r.libelle).toBe('Cully → Bourg-en-Lavaux');
		expect(r.commune.slug).toBe('bourg-en-lavaux');
	});

	it('propose d’abord les communes actuelles qui correspondent, puis les anciennes communes', () => {
		const villars = commune(5649, 'Villars-Sainte-Croix', [6.55, 46.56, 6.58, 46.58]);
		expect(libelles([BEL, PULLY, villars], 'vill')).toEqual(['Villars-Sainte-Croix', 'Villette (Lavaux) → Bourg-en-Lavaux']);
	});

	it('ne repropose pas par un ancien nom une commune déjà proposée (« Yverdon »)', () => {
		const yverdon = avec(commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]), [
			{ nom: 'Yverdon', slug: 'yverdon', type: 'Ancien nom', annee: 1982 }
		]);
		expect(libelles([BEL, yverdon], 'yverdon')).toEqual(['Yverdon-les-Bains']);
	});

	it('ne cherche rien avant deux lettres', () => {
		expect(libelles([PULLY, BEL], 'c')).toEqual([]);
		expect(libelles([PULLY, BEL], ' c ')).toEqual([]);
	});

	it('garde au plus quatre communes actuelles et trois anciennes communes', () => {
		const communes = [
			...['Bex', 'Bexo', 'Bexon', 'Bexonne', 'Bexonnes'].map((n, i) => commune(i, n, [6, 46, 7, 47])),
			avec(commune(9, 'Ailleurs', [6, 46, 7, 47]), ['Lebex', 'Labex', 'Lobex', 'Lubex'].map((n) => ancienne(n, n.toLowerCase())))
		];
		expect(libelles(communes, 'bex')).toEqual([
			'Bex',
			'Bexo',
			'Bexon',
			'Bexonne',
			'Lebex → Ailleurs',
			'Labex → Ailleurs',
			'Lobex → Ailleurs'
		]);
	});
});

describe('ordre des résultats de la recherche', () => {
	const GRANDSON = commune(5561, 'Grandson', [6.6, 46.8, 6.7, 46.85]);
	const adresse = (libelle: string): Resultat => ({ type: 'adresse', categorie: 'Adresse', libelle, lon: 6.6, lat: 46.5 });

	it('donne les communes, puis les fiches propres, puis les éléments des couches, puis les adresses et lieux', () => {
		const locaux = resultatsLocaux([PULLY, GRANDSON], 'gr', (texte) => resultatsCouches(COUCHES, texte));
		const tous = avecAdresses(locaux, [adresse('Grand-Rue 1, 1095 Lutry')]);
		expect(tous.map((r) => [r.type, r.libelle])).toEqual([
			['commune', 'Grandson'],
			['fiche', 'Grand Conseil'],
			['adresse', 'Grand-Rue 1, 1095 Lutry']
		]);
	});

	it('met un élément d’une couche après les communes et avant les adresses, qui ne répètent pas un libellé', () => {
		const element: Resultat = { type: 'element', nomCouche: 'Permis', libelle: 'Dossier', couche: 'permis', element: '1' };
		const locaux = resultatsLocaux([PULLY], 'pully', () => [element]);
		expect(avecAdresses(locaux, [adresse('Pully'), adresse('Pully')]).map((r) => r.type)).toEqual(['commune', 'element']);
	});
});
