import { describe, expect, it } from 'vitest';
import { creerDonneesConseils } from './donnees.js';
import type { ListeObjets, ListeSeances } from '#lib/schema.js';
import {
	DONNEES,
	GENERE,
	conseilLausanne,
	conseilYverdon,
	entreeFil,
	fauxDepotConseils,
	filConseils,
	grandConseil,
	indexConseils,
	ligneObjet,
	objet,
	rattachementsCommune,
	seance
} from '#tests/faux-conseils.js';
import { LUTRY, PULLY, commune } from '#tests/faux-canton.js';

describe('index des conseils', () => {
	it('lit les conseils couverts dans conseils/index.json, à l’adresse des Pages du dépôt de données', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': indexConseils() });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		const index = await conseils.index();

		expect(index.conseils.map((c) => c.nom)).toEqual([
			'Grand Conseil',
			'Conseil communal de Lausanne',
			'Conseil communal d’Yverdon-les-Bains'
		]);
		expect(depot.requetes).toEqual(['conseils/index.json']);
	});

	it('refuse un index d’une version inconnue', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': { ...indexConseils(), version: 2 } });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		await expect(conseils.index()).rejects.toThrow(/version inconnue/);
	});

	it('refuse un index absent ou injoignable', async () => {
		const depot = fauxDepotConseils();
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });
		await expect(conseils.index()).rejects.toThrow(/404/);

		depot.horsLigne(true);
		await expect(conseils.index()).rejects.toThrow();
	});

	it('ne lit l’index qu’une fois par visite', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': indexConseils() });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		await conseils.index();
		await conseils.index();

		expect(depot.requetes).toEqual(['conseils/index.json']);
	});

	it('relit l’index à la demande suivante après un échec', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': indexConseils() });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });
		depot.panne(503);
		await expect(conseils.index()).rejects.toThrow(/503/);

		depot.panne(null);
		const index = await conseils.index();

		expect(index.conseils).toHaveLength(3);
		expect(depot.requetes).toEqual(['conseils/index.json', 'conseils/index.json']);
	});
});

/** `conseils/<cle>/objets-<année>.json` avec `n` Objets, du plus récent au plus ancien. */
function listeObjets(cle: string, annee: number, n: number): ListeObjets {
	const aa = annee % 100;
	return {
		version: 1,
		genere: GENERE,
		conseil: cle,
		annee,
		objets: Array.from({ length: n }, (_, i) =>
			ligneObjet({ cle: `${cle}/POS${aa}-${String(n - i).padStart(3, '0')}`, numero: `POS${aa}/${n - i}` })
		)
	};
}

describe('Objets d’un conseil, par année', () => {
	const lausanne = (parAnnee: Record<string, number>) =>
		conseilLausanne({ objets_par_annee: parAnnee, objets: Object.values(parAnnee).reduce((a, b) => a + b, 0) });

	it('lit la liste de l’année la plus récente, et s’en contente si elle a au moins 8 Objets', async () => {
		const depot = fauxDepotConseils({ 'conseils/5586/objets-2026.json': listeObjets('5586', 2026, 9) });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		const page = await conseils.objetsRecents(lausanne({ '2025': 40, '2026': 9 }));

		expect(page.objets).toHaveLength(9);
		expect(page.objets[0].numero).toBe('POS26/9');
		expect(page.suivante).toBe(2025);
		expect(depot.requetes).toEqual(['conseils/5586/objets-2026.json']);
	});

	it('lit aussi l’année précédente quand la plus récente a moins de 8 Objets', async () => {
		const depot = fauxDepotConseils({
			'conseils/5586/objets-2026.json': listeObjets('5586', 2026, 3),
			'conseils/5586/objets-2025.json': listeObjets('5586', 2025, 40)
		});
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		const page = await conseils.objetsRecents(lausanne({ '2024': 12, '2025': 40, '2026': 3 }));

		expect(page.objets).toHaveLength(43);
		expect(page.objets.map((o) => o.numero).slice(2, 4)).toEqual(['POS26/1', 'POS25/40']);
		expect(page.suivante).toBe(2024);
		expect(depot.requetes).toEqual(['conseils/5586/objets-2026.json', 'conseils/5586/objets-2025.json']);
	});

	it('charge ensuite une année à la fois, jusqu’à la dernière, en sautant les années sans Objets', async () => {
		const depot = fauxDepotConseils({
			'conseils/5586/objets-2026.json': listeObjets('5586', 2026, 10),
			'conseils/5586/objets-2025.json': listeObjets('5586', 2025, 4),
			'conseils/5586/objets-2023.json': listeObjets('5586', 2023, 2)
		});
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });
		const conseil = lausanne({ '2023': 2, '2025': 4, '2026': 10 });

		const premiere = await conseils.objetsRecents(conseil);
		const deuxieme = await conseils.objetsSuivants(conseil, premiere);
		const troisieme = await conseils.objetsSuivants(conseil, deuxieme);

		expect(deuxieme.objets).toHaveLength(14);
		expect(deuxieme.suivante).toBe(2023);
		expect(troisieme.objets).toHaveLength(16);
		expect(troisieme.objets.at(-1)?.numero).toBe('POS23/1');
		expect(troisieme.suivante).toBeNull();
		expect(depot.requetes).toEqual([
			'conseils/5586/objets-2026.json',
			'conseils/5586/objets-2025.json',
			'conseils/5586/objets-2023.json'
		]);
	});

	it('ne lit rien pour un conseil sans Objets', async () => {
		const depot = fauxDepotConseils();
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		const page = await conseils.objetsRecents(conseilYverdon());

		expect(page).toEqual({ objets: [], suivante: null });
		expect(depot.requetes).toEqual([]);
	});

	it('rejette si une liste manque, et la relit à la demande suivante', async () => {
		const depot = fauxDepotConseils();
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });
		const conseil = lausanne({ '2026': 9 });
		await expect(conseils.objetsRecents(conseil)).rejects.toThrow(/404/);

		depot.poser('conseils/5586/objets-2026.json', listeObjets('5586', 2026, 9));

		expect((await conseils.objetsRecents(conseil)).objets).toHaveLength(9);
	});
});

describe('Séances d’un conseil', () => {
	it('lit la liste des Séances et, une fois, le fichier d’archive d’une Séance', async () => {
		const liste: ListeSeances = {
			version: 1,
			genere: GENERE,
			conseil: '5586',
			seances: [{ cle: '5586/2026-10-06', date: '2026-10-06T19:30', points: 2 }]
		};
		const depot = fauxDepotConseils({
			'conseils/5586/seances.json': liste,
			'conseils/5586/seances/2026-10-06.json': seance({ date: '2026-10-06T19:30' })
		});
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		expect((await conseils.seances('5586')).seances).toHaveLength(1);
		expect((await conseils.seance('5586/2026-10-06')).ordre_du_jour).toHaveLength(2);
		await conseils.seance('5586/2026-10-06');

		expect(depot.requetes).toEqual(['conseils/5586/seances.json', 'conseils/5586/seances/2026-10-06.json']);
	});
});

const LAUSANNE = commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]);
const YVERDON = { ...commune(5938, 'Yverdon-les-Bains', [6.6, 46.75, 6.68, 46.8]), slug: 'yverdon-les-bains' };

/** Les données des conseils sur ce faux dépôt, avec un index des communes réduit. */
function donneesSur(fichiers: Record<string, unknown>) {
	const depot = fauxDepotConseils(fichiers);
	const communes = async () => [PULLY, LUTRY, LAUSANNE, YVERDON];
	return { depot, conseils: creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES, communes }) };
}

describe('localiser un Objet ou une Séance', () => {
	it('ouvre un Objet d’un conseil communal dans la seule fiche de sa commune, sans position, après avoir lu son archive', async () => {
		const { depot, conseils } = donneesSur({
			'conseils/5586/objets/POS25-115.json': objet({ numero: 'POS25/115', type: 'Postulat' })
		});

		expect(await conseils.localiser('5586/POS25-115')).toEqual({ fiches: [{ commune: 'lausanne' }] });
		expect(depot.requetes).toEqual(['conseils/5586/objets/POS25-115.json']);
	});

	it('ouvre une Séance d’un conseil communal dans la fiche de sa commune', async () => {
		const { depot, conseils } = donneesSur({
			'conseils/5938/seances/2026-10-01.json': seance({ date: '2026-10-01T20:00' })
		});

		expect(await conseils.localiser('5938/2026-10-01')).toEqual({ fiches: [{ commune: 'yverdon-les-bains' }] });
		expect(depot.requetes).toEqual(['conseils/5938/seances/2026-10-01.json']);
	});

	it('ouvre une Séance du Grand Conseil et un Objet sans commune dans la seule fiche du Grand Conseil', async () => {
		const { conseils } = donneesSur({
			'conseils/vd/seances/2026-10-06.json': seance(),
			'conseils/vd/objets/26_INT_140.json': objet()
		});

		expect(await conseils.localiser('vd/2026-10-06')).toEqual({ fiches: [{ fiche: 'grand-conseil' }] });
		expect(await conseils.localiser('vd/26_INT_140')).toEqual({ fiches: [{ fiche: 'grand-conseil' }] });
	});

	it('ouvre un Objet du Grand Conseil dans ses communes rattachées, dans leur ordre, puis dans la fiche du Grand Conseil', async () => {
		const rattache = objet({
			communes: [
				{ ofs: 5606, origine: 'titre' },
				{ ofs: 5590, origine: 'document' }
			]
		});
		const { conseils } = donneesSur({ 'conseils/vd/objets/26_INT_140.json': rattache });

		expect(await conseils.localiser('vd/26_INT_140')).toEqual({
			fiches: [{ commune: 'lutry' }, { commune: 'pully' }, { fiche: 'grand-conseil' }]
		});
	});

	it('ne trouve pas une clé absente du dépôt, et ne demande rien pour une clé qui n’est pas celle d’un conseil', async () => {
		const { depot, conseils } = donneesSur({});

		expect(await conseils.localiser('5586/POS25-999')).toBeNull();
		expect(await conseils.localiser('9999/POS25-115')).toBeNull();
		expect(await conseils.localiser('POS25-115')).toBeNull();
		expect(await conseils.localiser('5586/../index')).toBeNull();
		expect(depot.requetes).toEqual(['conseils/5586/objets/POS25-999.json']);
	});

	it('rejette quand l’archive n’a pas pu être lue, et la relit à la demande suivante', async () => {
		const { depot, conseils } = donneesSur({ 'conseils/5586/objets/POS25-115.json': objet() });
		depot.horsLigne(true);
		await expect(conseils.localiser('5586/POS25-115')).rejects.toThrow();
		depot.horsLigne(false);
		depot.panne(503);
		await expect(conseils.localiser('5586/POS25-115')).rejects.toThrow(/503/);

		depot.panne(null);
		expect(await conseils.localiser('5586/POS25-115')).toEqual({ fiches: [{ commune: 'lausanne' }] });
	});

	it('donne le fichier d’archive de l’élément ouvert', async () => {
		const { conseils } = donneesSur({
			'conseils/5586/objets/POS25-115.json': objet({ numero: 'POS25/115' }),
			'conseils/5586/seances/2026-10-06.json': seance()
		});

		expect(await conseils.element('5586/POS25-115')).toMatchObject({ numero: 'POS25/115' });
		expect(await conseils.element('5586/2026-10-06')).toMatchObject({ date: '2026-10-06' });
		expect(await conseils.element('5586/POS25-999')).toBeNull();
	});
});

describe('entrées du fil cantonal', () => {
	const MORGES = commune(5642, 'Morges', [6.47, 46.49, 6.52, 46.53]);
	/** Les données des conseils sur un faux dépôt qui ne sert que ce `conseils/fil.json`. */
	function filSur(entrees: Parameters<typeof filConseils>[0]) {
		const depot = fauxDepotConseils({ 'conseils/fil.json': filConseils(entrees) });
		const communes = async () => [PULLY, LUTRY, LAUSANNE, YVERDON, MORGES];
		return { depot, conseils: creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES, communes }) };
	}

	it('donne un Objet d’un conseil communal : son type brut, le nom de son conseil, son titre et sa commune', async () => {
		const { depot, conseils } = filSur([
			entreeFil({
				cle: '5586/POS26-012',
				conseil: '5586',
				type: 'Postulat',
				date: '2026-10-07',
				titre: 'Pour des préaux ouverts le week-end',
				communes: [5586]
			})
		]);

		expect(await conseils.entreesFil('2026-10-02')).toEqual([
			{
				element: '5586/POS26-012',
				type: 'objets',
				date: '2026-10-07',
				sorte: 'Postulat',
				qui: 'Conseil communal de Lausanne',
				titre: 'Pour des préaux ouverts le week-end',
				communes: ['lausanne']
			}
		]);
		expect(depot.requetes).toEqual(['conseils/fil.json']);
	});

	it('ne garde que les entrées datées au moins de `depuis`, et les Séances à venir', async () => {
		const { conseils } = filSur([
			entreeFil({ cle: 'vd/26_INT_140', date: '2026-10-02' }),
			entreeFil({ cle: 'vd/26_INT_120', date: '2026-10-01' }),
			entreeFil({ cle: 'vd/26_MOT_009', date: '2026-09-20' }),
			entreeFil({ cle: 'vd/2026-11-03', sorte: 'seance', type: null, date: '2026-11-03', points: 0 })
		]);

		const entrees = await conseils.entreesFil('2026-10-02');

		expect(entrees.map((e) => e.element)).toEqual(['vd/26_INT_140', 'vd/2026-11-03']);
	});

	it('donne un Objet du Grand Conseil avec ses communes rattachées dans leur ordre, ou sans commune', async () => {
		const { conseils } = filSur([
			entreeFil({ cle: 'vd/26_INT_140', communes: [5642, 5586] }),
			entreeFil({ cle: 'vd/26_INT_141', communes: [] })
		]);

		const [nommant, sans] = await conseils.entreesFil('2026-10-02');

		expect(nommant).toMatchObject({ sorte: 'Interpellation', qui: 'Grand Conseil', communes: ['morges', 'lausanne'] });
		expect(sans).toMatchObject({ qui: 'Grand Conseil', communes: [] });
		expect(nommant.position).toBeUndefined();
	});

	it('donne une Séance : son nom composé et son nombre de points, sa commune ou aucune pour le Grand Conseil', async () => {
		const { conseils } = filSur([
			entreeFil({
				cle: '5586/2026-10-06',
				conseil: '5586',
				sorte: 'seance',
				type: null,
				date: '2026-10-06T18:00',
				titre: 'Séance du Conseil communal',
				communes: [5586],
				points: 12
			}),
			entreeFil({ cle: 'vd/2026-10-20', sorte: 'seance', type: null, date: '2026-10-20', communes: [], points: 1 }),
			entreeFil({ cle: 'vd/2026-11-03', sorte: 'seance', type: null, date: '2026-11-03', communes: [], points: 0 })
		]);

		expect(await conseils.entreesFil('2026-10-02')).toEqual([
			{
				element: '5586/2026-10-06',
				type: 'seances',
				date: '2026-10-06',
				sorte: 'Séance',
				qui: 'Conseil communal de Lausanne',
				titre: 'Séance du mardi 6 octobre 2026 à 18 h · 12 points',
				communes: ['lausanne']
			},
			{
				element: 'vd/2026-10-20',
				type: 'seances',
				date: '2026-10-20',
				sorte: 'Séance',
				qui: 'Grand Conseil',
				titre: 'Séance du mardi 20 octobre 2026 · 1 point',
				communes: []
			},
			{
				element: 'vd/2026-11-03',
				type: 'seances',
				date: '2026-11-03',
				sorte: 'Séance',
				qui: 'Grand Conseil',
				titre: 'Séance du mardi 3 novembre 2026',
				communes: []
			}
		]);
	});

	it('rejette quand conseils/fil.json n’a pas pu être lu, et le relit à la demande suivante', async () => {
		const { depot, conseils } = filSur([entreeFil()]);
		depot.panne(503);
		await expect(conseils.entreesFil('2026-10-02')).rejects.toThrow(/503/);

		depot.panne(null);
		expect(await conseils.entreesFil('2026-10-02')).toHaveLength(1);
	});
});

describe('« Au Grand Conseil » d’une commune', () => {
	const nommantPully = [
		ligneObjet({ cle: 'vd/26_INT_140', communes: [{ ofs: PULLY.bfs, origine: 'titre' }] }),
		ligneObjet({
			cle: 'vd/26_MOT_012',
			numero: '26_MOT_012',
			communes: [
				{ ofs: LUTRY.bfs, origine: 'titre' },
				{ ofs: PULLY.bfs, origine: 'document' }
			]
		})
	];

	it('lit les Objets rattachés dans conseils/communes/<ofs>.json quand l’index en annonce', async () => {
		const depot = fauxDepotConseils({
			'conseils/index.json': indexConseils({ communes: { [PULLY.bfs]: 2 } }),
			'conseils/communes/5590.json': rattachementsCommune(nommantPully)
		});
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		const objets = await conseils.auGrandConseil(PULLY.bfs);

		expect(objets.map((o) => o.cle)).toEqual(['vd/26_INT_140', 'vd/26_MOT_012']);
		expect(depot.requetes).toEqual(['conseils/index.json', 'conseils/communes/5590.json']);
	});

	it('ne demande rien de plus que l’index pour une commune qu’aucun Objet ne nomme', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': indexConseils({ communes: { [PULLY.bfs]: 2 } }) });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		expect(await conseils.auGrandConseil(LUTRY.bfs)).toEqual([]);
		expect(depot.requetes).toEqual(['conseils/index.json']);
	});

	it('rejette si le fichier annoncé par l’index manque, plutôt que de dire la commune sans Objets', async () => {
		const depot = fauxDepotConseils({ 'conseils/index.json': indexConseils({ communes: { [PULLY.bfs]: 2 } }) });
		const conseils = creerDonneesConseils({ fetch: depot.fetch, donnees: DONNEES });

		await expect(conseils.auGrandConseil(PULLY.bfs)).rejects.toThrow(/404/);
	});
});
