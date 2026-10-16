import type { Centre } from '#lib/types.js';
import type { Fiche, Lieu, Ouvert } from './types.js';

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

/** Les deux désignent la même fiche. */
export const memeFiche = (a: Fiche | null | undefined, b: Fiche | null | undefined) =>
	a != null &&
	b != null &&
	('commune' in a ? 'commune' in b && a.commune === b.commune : 'fiche' in b && a.fiche === b.fiche);

/**
 * Quand l'adresse porte un élément, son chemin porte toujours l'une de ses fiches. Règle unique : l'élément s'ouvre
 * dans la fiche du chemin si elle fait partie de celles que donne `localiser`, sinon dans la première. On garde donc
 * le chemin (`null`), on le mène à cette première fiche (`/?d=…`, `/commune/pully?d=…` → `/commune/<commune du
 * dossier>?d=…`), ou on retire l'élément que la couche ne trouve pas. `chemin` est la fiche du chemin.
 */
export function corrigerChemin(chemin: Fiche | null, lieu: Pick<Lieu, 'fiches'> | null): Fiche | 'retirer' | null {
	const premiere = lieu?.fiches[0];
	if (!premiere) return 'retirer';
	return lieu.fiches.some((f) => memeFiche(f, chemin)) ? null : premiere;
}

/**
 * Fermer un élément (« Permis » dans le fil) ramène à l'onglet de sa couche dans la fiche où il est ouvert. Si
 * l'application a poussé l'entrée d'historique depuis cette même fiche, on revient en arrière (`retour`) ; sinon
 * (lien direct, ou élément ouvert depuis la carte seule ou une autre fiche), revenir en arrière quitterait la fiche
 * ou le site : on remplace l'adresse par le chemin de la fiche, sans l'élément.
 */
export function fermeture(etat: App.PageState, fiche: Fiche | null): 'retour' | 'remplacer' {
	return etat.element && memeFiche(etat.element.depuis, fiche) ? 'retour' : 'remplacer';
}
