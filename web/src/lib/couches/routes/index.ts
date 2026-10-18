import type { Couche } from '#lib/registre/types.js';
import { SORTES } from './sortes.js';

/**
 * La couche Routes : les restrictions de circulation de la DGMR, en cours et à venir, lues en direct sur le service
 * du canton pour tout le canton (sans emprise). Ses composants partagent le module de données `donnees.svelte.ts`,
 * que la description n'importe pas : elle reste légère.
 */
export const coucheRoutes: Couche<undefined> = {
	id: 'routes',
	nom: 'Routes',
	nomOnglet: 'Routes',
	sources: ['dgmr-restrictions'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'R', couleur: SORTES.fermeture.couleur },
	// Une phrase fixe : la page de la commune est pré-générée, les restrictions lues en direct.
	resume: 'les restrictions de circulation en cours et à venir',
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte')
	}
};
