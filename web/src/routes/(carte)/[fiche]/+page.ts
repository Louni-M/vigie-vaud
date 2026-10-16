import { error } from '@sveltejs/kit';
import { COUCHES } from '#lib/registre/couches.js';
import { ficheDuChemin, fichesPropres } from '#lib/registre/fiches.js';
import type { EntryGenerator, PageLoad } from './$types';

// Une page pré-générée par fiche propre que déclare une couche (`/grand-conseil`), comme les fiches commune. Toute
// autre adresse d'un seul segment est une page inconnue : 404, comme une commune inconnue. (Pas de `params` de route :
// SvelteKit les charge hors de Vite, sans accès aux couches.)
export const entries: EntryGenerator = () => fichesPropres(COUCHES).map((f) => ({ fiche: f.fiche.chemin.slice(1) }));

export const load: PageLoad = ({ params }) => {
	const declaree = ficheDuChemin(COUCHES, `/${params.fiche}`);
	if (!declaree) error(404, 'Page introuvable');
	return { fiche: declaree.fiche };
};
