import { describe, expect, it, vi } from 'vitest';
import { creerChargementFil } from './chargement.svelte.js';
import type { CoucheInscrite, EntreeFil, Fil } from '#lib/registre/types.js';

const ENTREE: EntreeFil = {
	element: '1',
	type: 't',
	date: '2026-10-10',
	sorte: 'Sorte',
	qui: 'Qui',
	titre: 'Titre',
	communes: []
};

/** Une couche factice, désactivée : le fil la lit quand même. */
function couche(id: string, entrees?: Fil['entrees']) {
	return {
		id,
		nom: id,
		sources: [],
		permanente: false,
		activeParDefaut: false,
		icone: { signe: 'X', couleur: '#000' },
		...(entrees && { fil: { types: [{ id: 't', nom: 'T', signe: 'T', couleur: '#000' }], entrees } }),
		composants: { Carte: async () => ({ default: (() => {}) as never }) }
	} satisfies CoucheInscrite;
}

describe('chargement du fil', () => {
	it('demande une seule fois aux couches qui ont un fil leurs entrées depuis le premier jour du fil', async () => {
		const entrees = vi.fn(async () => [ENTREE]);
		const fil = creerChargementFil([couche('sans-fil'), couche('a', entrees)]);

		expect(fil.sources.map((s) => [s.couche, s.etat])).toEqual([['a', 'chargement']]);
		fil.charger('2026-10-16');
		fil.charger('2026-10-16');
		await vi.waitFor(() => expect(fil.sources[0].etat).toEqual({ entrees: [ENTREE] }));

		expect(entrees).toHaveBeenCalledOnce();
		expect(entrees).toHaveBeenCalledWith('2026-10-02');
	});

	it('met en panne la couche dont les entrées sont rejetées, et la réessaie à la demande', async () => {
		const entrees = vi.fn().mockRejectedValueOnce(new Error('CAMAC')).mockResolvedValueOnce([ENTREE]);
		const fil = creerChargementFil([couche('permis', entrees)]);

		fil.charger('2026-10-16');
		await vi.waitFor(() => expect(fil.sources[0].etat).toBe('panne'));
		fil.reessayer('permis');

		expect(fil.sources[0].etat).toBe('chargement');
		await vi.waitFor(() => expect(fil.sources[0].etat).toEqual({ entrees: [ENTREE] }));
		expect(entrees).toHaveBeenLastCalledWith('2026-10-02');
	});
});
