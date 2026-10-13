import { getCommunes } from '#lib/data.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ communes: await getCommunes(fetch) });
