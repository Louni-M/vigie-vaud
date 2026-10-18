import type { EtatRestriction } from './donnees.svelte.js';
import type { Sorte } from './sortes.js';
import { FILTRES_INITIAUX, type Filtres } from './volet.js';

/**
 * Les puces du volet Routes, partagées par le volet (la liste) et la carte (ses filtres). Elles durent le temps de
 * la visite et ne vont pas dans l'adresse : toutes allumées à l'arrivée.
 */

let filtres = $state.raw<Filtres>(FILTRES_INITIAUX);

const basculer = <T>(liste: readonly T[], x: T): T[] => (liste.includes(x) ? liste.filter((y) => y !== x) : [...liste, x]);

export const puces = {
	get filtres(): Filtres {
		return filtres;
	},
	basculerSorte(s: Sorte) {
		filtres = { ...filtres, sortes: basculer(filtres.sortes, s) };
	},
	basculerEtat(e: EtatRestriction) {
		filtres = { ...filtres, etats: basculer(filtres.etats, e) };
	}
};
