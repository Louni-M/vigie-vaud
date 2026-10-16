import { SITE } from '#lib/config.js';
import { sitemap } from '#lib/indexation.js';
import { COUCHES } from '#lib/registre/couches.js';
import { fichesPropres } from '#lib/registre/fiches.js';
import { getCommunes } from '#lib/socle/communes.js';
import type { RequestHandler } from './$types';

// Généré à la construction depuis l'adresse publique en configuration, les fiches propres des couches et l'index
// des communes (ADR 0012).
export const prerender = true;

export const GET: RequestHandler = async ({ fetch }) => {
	const slugs = (await getCommunes(fetch)).map((c) => c.slug);
	const fiches = fichesPropres(COUCHES).map((f) => f.fiche.chemin);
	return new Response(sitemap(SITE, slugs, fiches), { headers: { 'content-type': 'application/xml' } });
};
