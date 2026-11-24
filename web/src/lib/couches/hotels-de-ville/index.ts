import type { Couche } from '#lib/registre/types.js';

/**
 * La couche Hôtels de ville : un marqueur par commune actuelle, sur le siège de son administration, ou en terre
 * ferme quand sa position est approximative (pipeline/communes.py). Permanente et dessinée au-dessus des autres ;
 * un clic ouvre la fiche de la commune, ce que dit son entrée de la légende. Ni rubrique, ni onglet (donc pas de
 * Couverture), ni codec.
 */
export const coucheHotelsDeVille: Couche<undefined> = {
	id: 'hotels-de-ville',
	nom: 'Hôtels de ville',
	sources: ['ucv-annuaire', 'swisstopo-adresses', 'swisstopo-lacs'],
	permanente: true,
	activeParDefaut: true,
	icone: { signe: 'H', couleur: '#1f3a5f' },
	legende: {
		toujours: [
			{
				signe: 'hotel',
				couleur: '#1f3a5f',
				texte:
					'Hôtel de ville\u00a0: un clic ouvre la fiche de la commune. Placé au siège de l’administration communale, ou sur un point de la commune quand son adresse n’est pas connue.'
			}
		]
	},
	composants: {
		Carte: () => import('./Carte.svelte')
	}
};
