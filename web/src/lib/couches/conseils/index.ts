import type { Couche } from '#lib/registre/types.js';
import { SOURCES } from '#lib/sources.js';
import { resumeConseils } from './resume.js';

/** Sarcelle : la couleur de la couche, de son marqueur et des pastilles de ses Objets et Séances. */
export const COULEUR_CONSEILS = '#0b7285';

/** Le Parlement vaudois, place du Château 6 à Lausanne (lon, lat) : le marqueur du Grand Conseil. */
export const PARLEMENT: [number, number] = [6.63596, 46.52358];

/**
 * La couche Conseils : le Grand Conseil et les conseils communaux couverts, lus dans les fichiers que le cron publie
 * sur les Pages du dépôt de données (`donnees.ts`). Sur la carte, seulement le marqueur du Grand Conseil ; les
 * conseils communaux sont dans la fiche de leur commune. Une seule clé d'élément, `c`, pour les Objets comme pour
 * les Séances.
 */
export const coucheConseils: Couche<undefined> = {
	id: 'conseils',
	nom: 'Conseils',
	sources: ['openparldata-vd', 'openparldata-5586', 'openparldata-5938'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'C', couleur: COULEUR_CONSEILS },
	cleElement: 'c',
	resume: resumeConseils(SOURCES),
	nonCouvert: (commune) => `OpenParlData ne donne pas le conseil communal de ${commune.nom}.`,
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte')
	}
};
