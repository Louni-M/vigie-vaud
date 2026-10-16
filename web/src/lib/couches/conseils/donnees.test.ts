import { describe, expect, it } from 'vitest';
import { creerDonneesConseils } from './donnees.js';
import { DONNEES, conseilLausanne, fauxDepotConseils, grandConseil, indexConseils } from '#tests/faux-conseils.js';

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
