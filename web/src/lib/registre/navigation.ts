import type { Centre } from '#lib/types.js';
import type { Ouvert } from './types.js';

/** Ce que l'adresse dit de la carte : la commune du chemin, la vue et l'élément de la requête. */
export interface Adresse {
	commune: string | null;
	vue: Centre | null;
	ouvert: Ouvert | null;
}

/**
 * Ce que doit faire la carte : rétablir une vue, cadrer une commune, montrer l'élément ouvert (une fois
 * localisé par sa couche), revenir au canton, ou rien (`null`).
 */
export type Mouvement = { aller: Centre } | { cadrer: string } | 'element' | 'canton' | null;

/** Les deux désignent le même élément ouvert. */
export const memeElement = (a: Ouvert | null, b: Ouvert | null) =>
	a !== null && b !== null && a.couche === b.couche && a.element === b.element;

/**
 * Mouvement de la carte quand l'adresse change sous le registre : arrivée sur le site (`initial`), lien suivi,
 * précédent ou suivant du navigateur. `avant` est ce que reflétait l'adresse précédente.
 *
 * Fermer un élément pour revenir à l'onglet de sa commune ne bouge jamais la carte, et corriger le chemin de
 * l'élément ouvert non plus. Sinon la vue de l'adresse l'emporte ; à défaut, un élément qu'on vient d'ouvrir
 * est montré, une commune qu'on vient d'ouvrir est cadrée, et l'adresse nue « / » ramène au canton.
 */
export function mouvement(avant: Pick<Adresse, 'commune' | 'ouvert'>, apres: Adresse, initial: boolean): Mouvement {
	if (avant.ouvert && !apres.ouvert && avant.commune === apres.commune) return null;
	if (memeElement(avant.ouvert, apres.ouvert)) return null;
	if (apres.vue) return { aller: apres.vue };
	if (apres.ouvert) return 'element';
	if (apres.commune) return apres.commune === avant.commune ? null : { cadrer: apres.commune };
	return initial ? null : 'canton';
}

/**
 * Quand l'adresse porte un élément, son chemin porte toujours la commune de l'élément. D'après `localiser`, on
 * mène l'adresse à cette commune (`/?d=…`, `/commune/pully?d=…` → `/commune/<commune du dossier>?d=…`), on la
 * garde (`null`), ou on retire l'élément que la couche ne trouve pas. `commune` est celle du chemin.
 */
export function corrigerChemin(
	commune: string | null,
	lieu: { commune: string } | null
): { commune: string } | 'retirer' | null {
	if (!lieu) return 'retirer';
	return lieu.commune === commune ? null : { commune: lieu.commune };
}

/**
 * Fermer un élément (« Permis » dans le fil) ramène à l'onglet de sa couche dans la fiche de sa commune. Si
 * l'application a poussé l'entrée d'historique depuis la fiche de cette même commune, on revient en arrière
 * (`retour`) ; sinon (lien direct, ou élément ouvert depuis la carte seule ou une autre commune), revenir en
 * arrière quitterait la fiche ou le site : on remplace l'adresse par le chemin de la commune, sans l'élément.
 */
export function fermeture(etat: App.PageState, commune: string | null): 'retour' | 'remplacer' {
	return etat.element && etat.element.depuis === commune ? 'retour' : 'remplacer';
}
