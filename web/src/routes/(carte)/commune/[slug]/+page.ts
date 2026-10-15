import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent, params }) => {
	const commune = (await parent()).communes.find((c) => c.slug === params.slug);
	if (!commune) error(404, 'Commune introuvable');
	return { commune };
};
