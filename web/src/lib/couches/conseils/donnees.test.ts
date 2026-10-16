import { describe, expect, it } from 'vitest';
import { creerDonneesConseils } from './donnees.js';
import type { ListeObjets, ListeSeances } from '#lib/schema.js';
import {
	DONNEES,
	GENERE,
	conseilLausanne,
	conseilYverdon,
	fauxDepotConseils,
	grandConseil,
	indexConseils,
	ligneObjet,
	objet,
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
