import { permis } from '#lib/couches/permis/donnees.svelte.js';
import type { PageLoad } from './$types';

// Fiche lue en direct sur le service du canton : jamais pré-générée ni rendue côté serveur.
export const prerender = false;
export const ssr = false;

export const load: PageLoad = ({ params }) => {
	const id = Number(params.id);
	// Promesse non attendue : la page s'affiche aussitôt, avec un squelette pendant le chargement.
	return { id, dossier: Number.isInteger(id) ? permis.fiche(id) : Promise.resolve(undefined) };
};
