import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { delaiDepasse } from '#lib/chargement.js';
import { delaiExpire, sansReponse } from '#tests/sans-reponse.js';
import { LUTRY, PULLY } from '#tests/faux-canton.js';
// Importé dès la collecte, hors du délai des tests : sa première transformation par Vite, qui prend des secondes sur
// une machine chargée, est faite ; le module neuf de chaque test (`neuf`) n'est plus qu'évalué.
import './communes.js';

/** Le module neuf : son cache est celui de la visite. */
async function neuf() {
	vi.resetModules();
	return import('./communes.js');
}

/** Les fichiers des communes hébergés avec le site, et les requêtes reçues ; `panne` : ce qu'ils répondent sinon. */
function fauxSite() {
	const requetes: string[] = [];
	let panne: number | null = null;
	const fichiers: Record<string, unknown> = {
		'communes.json': [PULLY, LUTRY],
		'communes-limites.json': { 5590: [[[[6.65, 46.49], [6.7, 46.49], [6.7, 46.52], [6.65, 46.52], [6.65, 46.49]]]] }
	};
	const fetch = vi.fn(async (entree: RequestInfo | URL, _init?: RequestInit) => {
		const nom = String(entree).split('/').pop()!;
		requetes.push(nom);
		if (panne) return new Response('', { status: panne });
		return new Response(JSON.stringify(fichiers[nom]), { status: nom in fichiers ? 200 : 404 });
	});
	return { fetch, requetes, panne: (s: number | null) => (panne = s) };
}

describe('index et limites des communes', () => {
	let site: ReturnType<typeof fauxSite>;
	beforeEach(() => (site = fauxSite()));
	afterEach(() => vi.restoreAllMocks());

	it('ne lit communes.json qu’une fois par visite', async () => {
		const { getCommunes } = await neuf();
		expect(await getCommunes(site.fetch)).toEqual([PULLY, LUTRY]);
		await getCommunes(site.fetch);
		expect(site.requetes).toEqual(['communes.json']);
	});

	it('relit communes.json à la demande suivante après un échec', async () => {
		const { getCommunes } = await neuf();
		site.panne(503);
		await expect(getCommunes(site.fetch)).rejects.toThrow(/503/);
		site.panne(null);
		expect(await getCommunes(site.fetch)).toEqual([PULLY, LUTRY]);
		expect(site.requetes).toEqual(['communes.json', 'communes.json']);
	});

	it('rejette quand le site ne répond pas à temps, et relit à la demande suivante', async () => {
		const { getLimites } = await neuf();
		const delai = delaiExpire();
		const erreur = await getLimites(sansReponse).catch((e) => e);
		expect(delaiDepasse(erreur)).toBe(true);
		expect(delai).toHaveBeenCalledWith(20_000);
		vi.restoreAllMocks();
		expect(Object.keys(await getLimites(site.fetch))).toEqual(['5590']);
	});

	it('refait le rattachement à la demande suivante après un échec', async () => {
		const { getRattachement } = await neuf();
		site.panne(503);
		await expect(getRattachement(site.fetch)).rejects.toThrow();
		site.panne(null);
		const r = await getRattachement(site.fetch);
		expect(r.communeDe(6.67, 46.5)).toEqual(PULLY);
		expect(await getRattachement(site.fetch)).toBe(r);
	});
});
