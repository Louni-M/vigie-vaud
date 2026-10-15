import type { Couche } from '#lib/registre/types.js';

/**
 * La couche Hôtels de ville : un marqueur par commune actuelle, sur le siège de son administration, ou en terre
 * ferme quand sa position est approximative (pipeline/communes.py). Permanente et dessinée au-dessus des autres ;
 * un clic ouvre la fiche de la commune. Ni onglet (donc pas de Couverture) ni codec.
 */
export const coucheHotelsDeVille: Couche<undefined> = {
	id: 'hotels-de-ville',
	nom: 'Hôtels de ville',
	sources: ['ucv-annuaire', 'swisstopo-adresses', 'swisstopo-lacs'],
	permanente: true,
	activeParDefaut: true,
	icone: { signe: 'H', couleur: '#1f3a5f' },
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte')
	}
};
