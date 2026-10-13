import { getMeta } from '#lib/data.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => ({ meta: await getMeta(fetch) });
