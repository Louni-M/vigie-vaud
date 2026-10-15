import { describe, expect, it, vi } from 'vitest';
import { creerDonneesPermis } from './donnees.svelte.js';
import { entite, fauxCanton, PULLY } from './faux-canton.js';

// Le client du canton refuse de partir ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

/** Horloge fixée : 14 octobre 2026. Les « procédures en cours » comptent depuis le 14 octobre 2023. */
const maintenant = () => new Date('2026-10-14T10:00:00Z');
const A_LUTRY: [number, number] = [6.72, 46.5];

/** Nombre de n° demandés par chaque requête de fiches. */
const lots = (requetes: string[]) =>
	requetes.filter((w) => w.startsWith('NO_CAMAC IN')).map((w) => w.split(',').length);

describe('fiches', () => {
	const delivres = Array.from({ length: 650 }, (_, i) => entite(1000 + i, { ETAT: 'Permis délivré' }));

	it('charge les fiches demandées par lots de 300 n°, dans l’ordre demandé', async () => {
		const canton = fauxCanton(delivres);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });
		const ids = delivres.map((e) => Number(e.attributes.NO_CAMAC)).reverse();

		const fiches = await donnees.fiches(ids);

		expect(fiches.map((d) => d.id)).toEqual(ids);
		expect(fiches[0]).toMatchObject({ statut: 'delivre', commune: 'Pully' });
		expect(lots(canton.requetes).sort()).toEqual([300, 300, 50].sort());
	});

	it('ne redemande pas une fiche déjà chargée, ni un dossier en cours', async () => {
		const canton = fauxCanton([entite(1), ...delivres.slice(0, 3)]);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });
		await donnees.chargerActifs();
		await donnees.fiches([1000, 1001]);
		canton.requetes.length = 0;

		expect((await donnees.fiches([1, 1000, 1001, 1002])).map((d) => d.id)).toEqual([1, 1000, 1001, 1002]);
		expect((await donnees.fiche(1001))?.id).toBe(1001);
		expect(canton.requetes).toEqual(['NO_CAMAC IN (1002)']);
	});

	it('omet les n° inconnus du canton', async () => {
		const canton = fauxCanton(delivres.slice(0, 1));
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });

		expect(await donnees.fiche(999999)).toBeUndefined();
		expect((await donnees.fiches([999999, 1000])).map((d) => d.id)).toEqual([1000]);
	});
});

describe('historique', () => {
	const enquete = (jour: string) => `Du ${jour} au 01.01.2099`;
	const historique = [
		entite(1, { ETAT: 'Réalisé', DATE_ENQUETE: enquete('03.02.2026'), NATURE: 'Transformation' }),
		entite(2, { ETAT: 'Permis délivré', DATE_ENQUETE: enquete('10.05.2025') }),
		entite(3, { ETAT: 'Abandonné/refusé', DATE_ENQUETE: enquete('11.11.2024') }),
		entite(4, { ETAT: 'Permis délivré', DATE_ENQUETE: enquete('12.12.2023') })
	];
	const ids = (pts: { id: number }[]) => pts.map((p) => p.id).sort();
	const annees = (requetes: string[]) => requetes.map((w) => w.match(/= '(\d{4})'/)?.[1]);

	it('charge des points légers, de l’année en cours jusqu’à l’année choisie', async () => {
		const canton = fauxCanton(historique);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });

		const chargement = donnees.chargerHisto(2025);
		expect(donnees.histoChargement).toBe(true);
		await chargement;

		expect(donnees.histoChargement).toBe(false);
		expect(ids(donnees.histo)).toEqual([1, 2]);
		expect(donnees.histo.find((p) => p.id === 1)).toStrictEqual({
			id: 1,
			statut: 'realise',
			nature: 'transformation',
			debut: '2026-02-03',
			fin: '2099-01-01',
			lon: 6.67,
			lat: 46.5
		});
		expect(annees(canton.requetes).sort()).toEqual(['2025', '2026']);
	});

	it('ne charge que les années qui manquent quand on remonte plus loin', async () => {
		const canton = fauxCanton(historique);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });
		await donnees.chargerHisto(2025);
		canton.requetes.length = 0;

		await donnees.chargerHisto(2023);
		await donnees.chargerHisto(2024);

		expect(ids(donnees.histo)).toEqual([1, 2, 3, 4]);
		expect(annees(canton.requetes).sort()).toEqual(['2023', '2024']);
	});

	it('signale un historique partiel, et recharge les années manquées au nouvel essai', async () => {
		const canton = fauxCanton(historique);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });
		await donnees.chargerHisto(2026);
		canton.panne(503);

		await donnees.chargerHisto(2025);
		expect(donnees.histoEchec).toBe(true);
		expect(ids(donnees.histo)).toEqual([1]);

		canton.panne(null);
		await donnees.chargerHisto(2025);
		expect(donnees.histoEchec).toBe(false);
		expect(ids(donnees.histo)).toEqual([1, 2]);
	});
});

describe('chiffres d’une commune', () => {
	const du = (jour: string) => `Du ${jour} au 01.01.2099`;
	const canton = () =>
		fauxCanton([
			entite(1, { DATE_ENQUETE: du('19.09.2026') }),
			entite(2, { ETAT: 'Procédure en cours', DATE_ENQUETE: du('15.01.2024') }),
			entite(3, { ETAT: 'Procédure en cours', DATE_ENQUETE: du('15.01.2022') }),
			entite(4, { ETAT: 'Permis délivré', DATE_ENQUETE: du('01.04.2025') }),
			entite(5, { ETAT: 'Réalisé', DATE_ENQUETE: du('01.04.2025') }),
			entite(6, { ETAT: 'Abandonné/refusé', DATE_ENQUETE: du('30.06.2024') }),
			// Sur le lac, juste hors de Pully : rattaché à la commune la plus proche.
			entite(7, { ETAT: 'Permis délivré', DATE_ENQUETE: du('02.03.2023') }, [6.645, 46.5]),
			entite(8, { ETAT: 'Permis délivré', DATE_ENQUETE: du('02.03.2023') }, A_LUTRY)
		]);

	it('compte les dossiers rattachés à la commune, par statut et par année', async () => {
		const donnees = creerDonneesPermis({ fetch: canton().fetch, maintenant });

		const chiffres = await donnees.chiffres(PULLY);

		expect(chiffres.statuts).toEqual({ enquete: 1, procedure: 2, delivre: 2, realise: 1, abandonne: 1, autre: 0 });
		expect(chiffres.parAnnee).toEqual({ '2022': 1, '2023': 1, '2024': 2, '2025': 2, '2026': 1 });
	});

	it('liste l’historique hors dossiers en cours, publication la plus récente d’abord', async () => {
		const donnees = creerDonneesPermis({ fetch: canton().fetch, maintenant });

		const { historique } = await donnees.chiffres(PULLY);

		expect(historique.map((p) => p.id)).toEqual([5, 4, 6, 7, 3]);
	});
});

describe('dossiers en cours', () => {
	it('convertit les dossiers du canton, rattachés à leur commune, noms de particuliers masqués', async () => {
		const canton = fauxCanton([
			entite(101, {
				NO_FAO: 'P-2026-0412',
				DESCRIPTION: 'Construction d’une villa pour le compte de Dupont Jean',
				URL: 'https://www.camac.vd.ch/101'
			}),
			entite(102, { ETAT: 'Procédure en cours', DATE_ENQUETE: 'Du 01.11.2023 au 30.11.2023', NATURE: 'Démolition totale' }, A_LUTRY)
		]);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });

		const actifs = await donnees.chargerActifs();

		expect(actifs).toStrictEqual([
			{
				id: 101,
				statut: 'enquete',
				nature: 'construction',
				debut: '2026-09-19',
				fin: '2026-10-19',
				lon: 6.67,
				lat: 46.5,
				fao: 'P-2026-0412',
				description: 'Construction d’une villa pour le compte de [particulier]',
				url: 'https://www.camac.vd.ch/101',
				bfs: 5590,
				commune: 'Pully',
				slug: 'pully'
			},
			{
				id: 102,
				statut: 'procedure',
				nature: 'demolition',
				debut: '2023-11-01',
				fin: '2023-11-30',
				lon: 6.72,
				lat: 46.5,
				bfs: 5606,
				commune: 'Lutry',
				slug: 'lutry'
			}
		]);
		expect(donnees.actifs).toStrictEqual(actifs);
	});

	it('écarte les procédures commencées il y a plus de 3 ans et les dossiers clos, triés par n°', async () => {
		const canton = fauxCanton([
			entite(205),
			entite(203, { ETAT: 'Procédure en cours', DATE_ENQUETE: 'Du 13.10.2023 au 12.11.2023' }),
			entite(202, { ETAT: 'Procédure en cours', DATE_ENQUETE: 'Du 14.10.2023 au 13.11.2023' }),
			entite(204, { ETAT: 'Procédure en cours', DATE_ENQUETE: 'Du 01.06.2022 au 30.06.2022' }),
			entite(201, { ETAT: 'Permis délivré' }),
			entite(206, { ETAT: 'Enquête publique en cours', DATE_ENQUETE: 'Du 02.02.2019 au 03.03.2019' })
		]);
		const donnees = creerDonneesPermis({ fetch: canton.fetch, maintenant });

		expect((await donnees.chargerActifs()).map((d) => d.id)).toEqual([202, 205, 206]);
	});
});
