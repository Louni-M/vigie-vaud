/*
 * PROTOTYPE (ticket « Couche Routes sur la carte, volet et onglet Routes ») : à jeter, sur la branche
 * `prototype/routes-couche` seulement. Trois variantes de la couche Routes sur les vraies routes de la carte,
 * choisies par `?variant=A|B|C` et la barre flottante en bas :
 *   A « Tracés »     : chaque restriction est un élément, couleur par sorte (fermeture, déviation, feux…) ;
 *   B « Groupes »    : la fermeture et sa déviation forment un seul élément, ouvert d'un clic ;
 *   C « Calendrier » : couleur par échéance (en cours, cette semaine, plus tard), tout rangé par date.
 */
import type { Codec, Couche } from '#lib/registre/types.js';
import { routes, SORTES, type Variante } from './donnees.svelte.js';

export interface Parametres {
	variant: Variante;
}

const codec: Codec<Parametres> = {
	cles: ['variant'],
	lire: (p) => ({ variant: (['A', 'B', 'C'] as const).find((v) => v === p.get('variant')) ?? 'A' }),
	ecrire: (p) => (p.variant === 'A' ? [] : [['variant', p.variant]])
};

export const coucheRoutesPrototype: Couche<Parametres> = {
	id: 'routes',
	nom: 'Routes',
	sources: ['dgmr-restrictions'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'R', couleur: SORTES.fermeture.couleur },
	codec,
	cleElement: 'r',
	async localiser(element) {
		const { getCommunes } = await import('#lib/socle/communes.js');
		await routes.charger(await getCommunes(fetch));
		const r = routes.restriction(Number(element));
		if (!r) return null;
		return { fiches: r.communes.map((p) => ({ commune: p.commune.slug })), position: r.milieu };
	},
	introuvable: (e) => `Aucune restriction de circulation n° ${e}.`,
	libelle: (e) => {
		const r = routes.restriction(Number(e));
		return r ? r.nom : `n° ${e}`;
	},
	resume: 'les restrictions de circulation sur les routes cantonales, en direct depuis le canton',
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte'),
		Apercu: () => import('./Apercu.svelte')
	}
};
