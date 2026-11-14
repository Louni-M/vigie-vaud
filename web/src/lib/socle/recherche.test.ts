import { afterEach, describe, expect, it, vi } from 'vitest';
import { ancienEtActuelle, avecAdresses, chercherAdresses, chercherCommunes, resultatsLocaux } from './recherche.js';
import { delaiDepasse } from '#lib/chargement.js';
import { delaiExpire, sansReponse } from '#tests/sans-reponse.js';
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

	it('coupe le libellé d’un ancien nom autour de sa flèche, pour la montrer sans la faire lire', () => {
		const [ancien, actuelle] = chercherCommunes([PULLY, BEL], 'cully').concat(chercherCommunes([PULLY], 'pully'));
		expect(ancienEtActuelle(ancien)).toEqual(['Cully', 'Bourg-en-Lavaux']);
		expect(ancienEtActuelle(actuelle)).toBeNull();
		expect(ancienEtActuelle({ type: 'adresse', categorie: 'Adresse', libelle: 'A → B', lon: 6.6, lat: 46.5 })).toBeNull();
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
		const locaux = resultatsLocaux([PULLY, GRANDSON], 'gr', (texte) => resultatsCouches(COUCHES, texte, [PULLY, GRANDSON]));
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

describe('adresses et lieux swisstopo', () => {
	afterEach(() => vi.restoreAllMocks());

	const reponse = (corps: unknown, status = 200) =>
		new Response(typeof corps === 'string' ? corps : JSON.stringify(corps), { status });
	const lieu = (origin: string, label: string, detail = '') => ({ attrs: { origin, label, detail, lon: 6.65, lat: 46.51 } });

	it('demande les adresses, NPA et lieux de la saisie, et ne garde que ceux du canton', async () => {
		const demandes: URL[] = [];
		const f = async (url: RequestInfo | URL) => (
			demandes.push(new URL(String(url))),
			reponse({
				results: [
					lieu('address', 'Avenue de Lavaux 1 <b>1009 Pully</b>', 'avenue de lavaux 1 1009 pully 5590 pully ch vd'),
					lieu('address', 'Rue du Lac 1 <b>1200 Genève</b>', 'rue du lac 1 1200 geneve ch ge'),
					lieu('gazetteer', '<i>Lieu</i> <b>Pully</b> (VD) - Pully'),
					lieu('zipcode', '<b>1009</b> - Pully')
				]
			})
		);
		const adresses = await chercherAdresses(f, 'avenue de lavaux', [PULLY]);
		expect(demandes[0].origin + demandes[0].pathname).toBe('https://api3.geo.admin.ch/rest/services/api/SearchServer');
		expect(demandes[0].searchParams.get('searchText')).toBe('avenue de lavaux');
		expect(adresses.map((r) => r.type === 'adresse' && [r.categorie, r.libelle])).toEqual([
			['Adresse', 'Avenue de Lavaux 1 1009 Pully'],
			['Lieu', 'Pully'],
			['NPA', '1009 - Pully']
		]);
	});

	it('rejette une réponse HTTP en erreur, au lieu de la lire comme une recherche vide', async () => {
		await expect(chercherAdresses(async () => reponse({ results: [] }, 500), 'pully', [PULLY])).rejects.toThrow('HTTP 500');
		await expect(chercherAdresses(async () => reponse('Too many requests', 429), 'pully', [PULLY])).rejects.toThrow(
			'HTTP 429'
		);
	});

	it('rejette quand swisstopo est injoignable ou ne répond pas à temps', async () => {
		await expect(chercherAdresses(() => Promise.reject(new TypeError('réseau')), 'pully', [PULLY])).rejects.toThrow(
			'réseau'
		);
		delaiExpire();
		await expect(chercherAdresses(sansReponse, 'pully', [PULLY])).rejects.toSatisfy(delaiDepasse);
	});
});
