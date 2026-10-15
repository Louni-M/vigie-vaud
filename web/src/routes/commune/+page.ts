import { getCommunes } from '#lib/socle/communes.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ communes: await getCommunes(fetch) });
