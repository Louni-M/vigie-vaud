import { getCommunes, getMeta } from '#lib/data.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({
	communes: await getCommunes(fetch),
	meta: await getMeta(fetch)
});
