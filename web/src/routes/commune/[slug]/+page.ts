import { error } from '@sveltejs/kit';
import { getCommunes } from '#lib/socle/communes.js';
import type { PageLoad } from './$types';

// Seuls le nom et les limites de la commune (swisstopo) sont intégrés à la page pré-générée ;
// les dossiers sont lus en direct sur le service du canton, dans le navigateur.
export const load: PageLoad = async ({ fetch, params }) => {
	const commune = (await getCommunes(fetch)).find((c) => c.slug === params.slug);
	if (!commune) error(404, 'Commune introuvable');
	return { commune };
};
