import { resolve } from '$app/paths';
import type { Centre } from '#lib/types.js';
import { COUCHES } from './couches.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';

/*
 * Constructeurs de liens du registre : seul le registre sait écrire l'adresse de la carte.
 */

/** La fiche d'une commune. */
export const lienCommune = (slug: string) => resolve('/(carte)/commune/[slug]', { slug });

/** La carte, avec ce qui diffère de l'état par défaut. */
export function lienCarte(etat: Partial<EtatUrl> = {}): string {
	const defaut = lireUrl(COUCHES, new URLSearchParams());
	return `${resolve('/(carte)')}${ecrireUrl(COUCHES, { ...defaut, ...etat })}`;
}

/** La carte centrée sur une vue. */
export const lienVue = (vue: Centre) => lienCarte({ vue });

/** Un élément d'une couche ouvert sur la carte (un dossier : `lienElement('permis', '248845')`). */
export const lienElement = (couche: string, element: string) => lienCarte({ ouvert: { couche, element } });
