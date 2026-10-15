import { SITE } from '#lib/config.js';
import { sitemap } from '#lib/indexation.js';
import { getCommunes } from '#lib/socle/communes.js';
import type { RequestHandler } from './$types';

// Généré à la construction depuis l'adresse publique en configuration et l'index des communes (ADR 0012).
export const prerender = true;

export const GET: RequestHandler = async ({ fetch }) => {
	const slugs = (await getCommunes(fetch)).map((c) => c.slug);
	return new Response(sitemap(SITE, slugs), { headers: { 'content-type': 'application/xml' } });
};
