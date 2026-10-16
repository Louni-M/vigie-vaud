import type { Centre } from '#lib/types.js';
import type { Fiche, Lieu, Ouvert } from './types.js';

/** Ce que l'adresse dit de la carte : la fiche du chemin (commune ou fiche propre), la vue et l'élément de la requête. */
export interface Adresse {
	fiche: Fiche | null;
	vue: Centre | null;
	ouvert: Ouvert | null;
}

/**
 * Ce que doit faire la carte : rétablir une vue, cadrer une fiche (la commune entière, ou la position d'une fiche
 * propre), montrer l'élément ouvert (une fois localisé par sa couche), revenir au canton, ou rien (`null`).
 */
export type Mouvement = { aller: Centre } | { cadrer: Fiche } | 'element' | 'canton' | null;

/** Les deux désignent le même élément ouvert. */
export const memeElement = (a: Ouvert | null, b: Ouvert | null) =>
	a !== null && b !== null && a.couche === b.couche && a.element === b.element;

/**
 * Mouvement de la carte quand l'adresse change sous le registre : arrivée sur le site (`initial`), lien suivi,
 * précédent ou suivant du navigateur. `avant` est ce que reflétait l'adresse précédente.
 *
 * Fermer un élément pour revenir à l'onglet de sa fiche ne bouge jamais la carte, et corriger le chemin de
 * l'élément ouvert non plus. Sinon la vue de l'adresse l'emporte ; à défaut, un élément qu'on vient d'ouvrir
 * est montré, une fiche qu'on vient d'ouvrir est cadrée, et l'adresse nue « / » ramène au canton.
 */
export function mouvement(avant: Pick<Adresse, 'fiche' | 'ouvert'>, apres: Adresse, initial: boolean): Mouvement {
	const memeFicheOuverte = avant.fiche === apres.fiche || memeFiche(avant.fiche, apres.fiche);
	if (avant.ouvert && !apres.ouvert && memeFicheOuverte) return null;
	if (memeElement(avant.ouvert, apres.ouvert)) return null;
	if (apres.vue) return { aller: apres.vue };
	if (apres.ouvert) return 'element';
	if (apres.fiche) return memeFicheOuverte ? null : { cadrer: apres.fiche };
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

/**
 * Les navigations vers une autre page que lance le registre (`goto`). Tant qu'une n'a pas abouti, réussie ou non,
 * `enCours` est vrai et l'état n'écrit pas l'adresse : la carte qui finit un déplacement réécrirait l'adresse de la
 * page qu'on quitte, et annulerait la navigation (ouvrir un élément dans une autre fiche).
 */
export function creerNavigations<O>(goto: (url: string, options: O) => Promise<void>) {
	let enRoute = 0;
	return {
		naviguer(url: string, options: O): Promise<void> {
			enRoute++;
			return goto(url, options).finally(() => enRoute--);
		},
		get enCours() {
			return enRoute > 0;
		}
	};
}
