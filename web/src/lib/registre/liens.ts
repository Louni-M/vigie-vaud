import { resolve } from '$app/paths';
import type { Centre } from '#lib/types.js';
import { COUCHES } from './couches.js';
import { fichePropre } from './fiches.js';
import type { CoucheInscrite, Fiche } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';

/*
 * Constructeurs de liens du registre : seul le registre sait écrire l'adresse de la carte.
 */

/** La fiche d'une commune. */
export const lienCommune = (slug: string) => resolve('/(carte)/commune/[slug]', { slug });

/**
 * Chemin d'une fiche, sans la requête : celle d'une commune, ou la page d'une fiche propre que déclare l'une des
 * `couches` (`grand-conseil` → « /grand-conseil »). Lève si aucune ne la déclare.
 */
export function cheminFiche(couches: readonly CoucheInscrite[], f: Fiche): string {
	if ('commune' in f) return lienCommune(f.commune);
	const declaree = fichePropre(couches, f.fiche);
	if (!declaree) throw new Error(`Aucune couche ne déclare la fiche « ${f.fiche} »`);
	return resolve('/(carte)/[fiche]', { fiche: declaree.fiche.chemin.slice(1) });
}

/** La page d'une fiche propre, par son identifiant (`grand-conseil` → « /grand-conseil »). */
export const lienFiche = (id: string) => cheminFiche(COUCHES, { fiche: id });

/** La carte, avec ce qui diffère de l'état par défaut. */
export function lienCarte(etat: Partial<EtatUrl> = {}): string {
	const defaut = lireUrl(COUCHES, new URLSearchParams());
	return `${resolve('/(carte)')}${ecrireUrl(COUCHES, { ...defaut, ...etat })}`;
}

/** La carte centrée sur une vue. */
export const lienVue = (vue: Centre) => lienCarte({ vue });

/** Un élément d'une couche ouvert sur la carte (un dossier : `lienElement('permis', '248845')`). */
export const lienElement = (couche: string, element: string) => lienCarte({ ouvert: { couche, element } });
