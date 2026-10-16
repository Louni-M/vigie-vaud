import { afterEach, describe, expect, it, vi } from 'vitest';
import { couchePermis } from './index.js';
import { entite, fauxCanton } from '#tests/faux-canton.js';

// Le client du canton refuse de partir ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

// Horloge fixée avant l'import : le module de données partagé lit la date du jour à sa création.
vi.hoisted(() => vi.useFakeTimers({ now: new Date('2026-10-16T10:00:00Z'), toFake: ['Date'] }));

afterEach(() => vi.unstubAllGlobals());

describe('couche Permis', () => {
	it('titre un dossier ouvert par son n° et le nom de la fiche où il est ouvert', () => {
		expect(couchePermis.titre?.('248845', 'Lutry')).toBe('Dossier n° 248845 – Lutry – Vigie Vaud');
	});

	it('localise un dossier dans la seule fiche de sa commune, à son point', async () => {
		vi.stubGlobal('fetch', fauxCanton([entite(248845, {}, [6.72, 46.5])]).fetch);

		expect(await couchePermis.localiser?.('248845')).toEqual({
			fiches: [{ commune: 'lutry' }],
			position: [6.72, 46.5]
		});
	});

	it('donne au fil les nouveaux dossiers : enquête débutée depuis `depuis`, quel que soit leur statut', async () => {
		vi.stubGlobal(
			'fetch',
			fauxCanton([
				entite(250001, { DATE_ENQUETE: 'Du 05.10.2026 au 04.11.2026', DESCRIPTION: 'Villa de 2 logements' }),
				entite(
					250002,
					{ DATE_ENQUETE: 'Du 02.10.2026 au 01.11.2026', ETAT: 'Procédure en cours', NATURE: 'Transformation' },
					[6.72, 46.5]
				),
				entite(250003, { DATE_ENQUETE: 'Du 01.10.2026 au 31.10.2026' })
			]).fetch
		);

		expect(couchePermis.fil?.types.map((t) => [t.id, t.nom, t.signe])).toEqual([
			['nouveaux', 'Nouveaux dossiers', 'P']
		]);
		expect(await couchePermis.fil?.entrees('2026-10-02')).toEqual([
			{
				element: '250001',
				type: 'nouveaux',
				date: '2026-10-05',
				sorte: 'Construction nouvelle',
				qui: 'Pully',
				titre: 'Villa de 2 logements',
				communes: ['pully'],
				position: [6.67, 46.5]
			},
			{
				element: '250002',
				type: 'nouveaux',
				date: '2026-10-02',
				sorte: 'Transformation',
				qui: 'Lutry',
				titre: 'Transformation',
				communes: ['lutry'],
				position: [6.72, 46.5]
			}
		]);
	});

	it('ne donne pas au fil un dossier dont l’enquête ne commence que demain (« À venir » : les Séances annoncées)', async () => {
		vi.stubGlobal(
			'fetch',
			fauxCanton([
				entite(250010, { DATE_ENQUETE: 'Du 16.10.2026 au 15.11.2026' }),
				entite(250011, { DATE_ENQUETE: 'Du 17.10.2026 au 16.11.2026' })
			]).fetch
		);
		// Les dossiers en cours se chargent une fois par visite : une visite neuve, sans ceux du test précédent.
		vi.resetModules();
		const { couchePermis: neuve } = await import('./index.js');

		expect((await neuve.fil?.entrees('2026-10-02'))?.map((e) => [e.element, e.date])).toEqual([
			['250010', '2026-10-16']
		]);
	});

	it('ne localise pas un n° inconnu du canton', async () => {
		vi.stubGlobal('fetch', fauxCanton([]).fetch);

		expect(await couchePermis.localiser?.('999999')).toBeNull();
		expect(await couchePermis.localiser?.('abc')).toBeNull();
	});
});
