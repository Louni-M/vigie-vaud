import { resolve } from '$app/paths';
import type { Centre } from '#lib/types.js';
import { COUCHES } from './couches.js';
import { fichePropre } from './fiches.js';
import type { CoucheInscrite, Fiche } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';

/*
 * Constructeurs de liens du registre : seul le registre sait écrire l'adresse de la carte.
 */

/**
 * Un clic simple sur un lien de la carte, que l'application ouvre sur place (l'appelant fait alors `preventDefault`) ;
 * avec une touche (Cmd, Ctrl, Maj, Alt) ou un autre bouton, le navigateur suit le lien, dans un autre onglet.
 */
export const clicSimple = (e: MouseEvent) => !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0);

/**
 * La fiche d'une commune ; `onglet` : ouverte sur l'onglet de cette couche (`?onglet=conseils`), comme le fait un
 * clic simple qui l'ouvre par le registre.
 */
export const lienCommune = (slug: string, onglet?: string) =>
	`${resolve('/(carte)/commune/[slug]', { slug })}${onglet ? `?${new URLSearchParams({ onglet })}` : ''}`;

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
