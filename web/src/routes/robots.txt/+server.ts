import { SITE } from '#lib/config.js';
import { robots } from '#lib/indexation.js';
import type { RequestHandler } from './$types';

// Généré à la construction : l'adresse du sitemap suit l'adresse publique en configuration.
export const prerender = true;

export const GET: RequestHandler = () =>
	new Response(robots(SITE), { headers: { 'content-type': 'text/plain; charset=utf-8' } });
