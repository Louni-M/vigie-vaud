import { describe, expect, it, vi } from 'vitest';
import { creerRegistre } from './registre.svelte.js';
import type { Rubrique } from './types.js';
import { creerFauxNavigateur } from '#tests/faux-navigateur.svelte.js';

// La pré-génération des pages : le registre y est rendu hors du navigateur.
vi.mock('$app/env', () => ({ browser: false }));

describe('compte d’une rubrique à la pré-génération', () => {
	it('ne lance pas le compte, qui lirait une source pendant la construction du site', async () => {
		const compteur = vi.fn(async () => () => ({ etat: 'nombre' as const, nombre: 1 }));
		const rubrique: Rubrique = {
			id: 'a',
			nom: 'A',
			phrase: '',
			rang: 1,
			unite: { un: 'élément', plusieurs: 'éléments' },
			portee: 'zone',
			compteur
		};
		const nav = creerFauxNavigateur('/');
		const fin = $effect.root(() => {
			const registre = creerRegistre([], () => [], nav.navigateur);
			// Jamais résolue : la page pré-générée garde l'attente, que le navigateur remplace.
			void registre.compteur(rubrique);
		});
		await Promise.resolve();
		expect(compteur).not.toHaveBeenCalled();
		fin();
	});
});
