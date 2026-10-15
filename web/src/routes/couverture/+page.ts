import { getCommunes } from '#lib/socle/communes.js';
import type { PageLoad } from './$types';

// La page est pré-générée avec la liste des 300 communes (la Couverture déclarée est connue à la construction) ;
// seul l'état des sources est chargé à l'ouverture, dans le navigateur.
export const load: PageLoad = async ({ fetch }) => ({
	communes: (await getCommunes(fetch)).map(({ bfs, nom, slug }) => ({ bfs, nom, slug }))
});
