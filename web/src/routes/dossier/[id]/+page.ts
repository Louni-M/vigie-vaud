import { error } from '@sveltejs/kit';
import { getDossier, getMeta } from '#lib/data.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const id = Number(params.id);
	const dossier = Number.isInteger(id) ? await getDossier(fetch, id) : undefined;
	if (!dossier) error(404, 'Dossier introuvable');
	return { dossier, meta: await getMeta(fetch) };
};
