import { getDossier } from '#lib/data.js';
import type { PageLoad } from './$types';

// Fiche lue en direct sur le service du canton : jamais pré-générée ni rendue côté serveur.
export const prerender = false;
export const ssr = false;

export const load: PageLoad = ({ fetch, params }) => {
	const id = Number(params.id);
	// Promesse non attendue : la page s'affiche aussitôt, avec un squelette pendant le chargement.
	return { id, dossier: Number.isInteger(id) ? getDossier(fetch, id) : Promise.resolve(undefined) };
};
