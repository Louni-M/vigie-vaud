import { readFileSync } from 'node:fs';
import { test as base, expect, type BrowserContext, type Page, type Route } from '@playwright/test';
import { entite, fauxCanton } from '../tests/faux-canton.js';
import { DONNEES, GENERE, filConseils, fauxDepotConseils, indexConseils } from '../tests/faux-conseils.js';
import { fauxDgmr } from '../tests/faux-dgmr.js';

/*
 * Banc d'essai de la suite Playwright : chaque page parle à des services factices, interceptés dans le navigateur
 * (`context.route`), jamais copiés dans le site construit. Toute autre requête vers une autre machine est refusée,
 * et fait échouer le scénario.
 *
 * Réponses fabriquées, jamais enregistrées : la norme DCG 8401 interdit de rediffuser les données CAMAC et DGMR.
 */

/** Adresse des Pages du dépôt de données, que le site lit (`config.json`). */
const DEPOT_DONNEES: string = JSON.parse(readFileSync(new URL('../../config.json', import.meta.url), 'utf8')).donnees;

/** Machines locales : le site construit, servi par `vite preview`. */
const LOCALES = new Set(['localhost', '127.0.0.1', '[::1]']);

/** Une image PNG d'un pixel, pour chaque tuile du fond aérien. */
const TUILE = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
	'base64'
);

/** Le fond de carte : un aplat, sans tuiles vectorielles, ni glyphes, ni icônes. */
const STYLE = {
	version: 8,
	name: 'Fond factice',
	sources: {},
	layers: [{ id: 'fond', type: 'background', paint: { 'background-color': '#ebe7dc' } }]
};

/** « 19.10.2026 », comme le canton écrit ses dates. */
function dateCamac(decalageJours: number): string {
	const d = new Date(Date.now() + decalageJours * 86_400_000);
	const deux = (n: number) => String(n).padStart(2, '0');
	return `${deux(d.getDate())}.${deux(d.getMonth() + 1)}.${d.getFullYear()}`;
}
const periode = (debut: number, fin: number) => `Du ${dateCamac(debut)} au ${dateCamac(fin)}`;

/**
 * Trois dossiers à Pully, autour de son hôtel de ville (6,6616 E ; 46,5093 N) : deux à l'enquête, un dont l'enquête
 * est finie et la décision attendue.
 */
export const DOSSIERS = [
	entite(260101, { DATE_ENQUETE: periode(-5, 25), DESCRIPTION: 'Agrandissement d’une villa' }, [6.658, 46.508]),
	entite(260102, { DATE_ENQUETE: periode(-2, 28), DESCRIPTION: 'Pose de panneaux solaires' }, [6.664, 46.511]),
	entite(
		260103,
		{ DATE_ENQUETE: periode(-60, -30), ETAT: 'Procédure en cours', DESCRIPTION: 'Démolition d’un garage' },
		[6.661, 46.507]
	)
];

/** Une adresse swisstopo de Pully, telle que la Recherche l'affiche : le faux la propose pour toute saisie. */
export const ADRESSE = 'Avenue de l’Essai 1 1009 Pully';
const LIEUX = {
	results: [
		{
			attrs: {
				origin: 'address',
				label: 'Avenue de l’Essai 1 <b>1009 Pully</b>',
				detail: 'avenue de l essai 1 1009 pully 5590 pully ch vd',
				lat: 46.5101,
				lon: 6.6602
			}
		}
	]
};

const json = (corps: unknown) => ({ status: 200, contentType: 'application/json', body: JSON.stringify(corps) });

/** Les requêtes du site vont à d'autres origines : la réponse factice doit les y autoriser. */
const CORS = { 'Access-Control-Allow-Origin': '*' };

/** Répond à la requête interceptée par un faux service écrit comme un `fetch` (ceux de `web/tests/`). */
async function servir(route: Route, faux: typeof fetch, adresse = route.request().url()) {
	const requete = route.request();
	const reponse = await faux(adresse, { method: requete.method(), body: requete.postData() ?? undefined });
	await route.fulfill({
		status: reponse.status,
		headers: { ...Object.fromEntries(reponse.headers), ...CORS },
		body: Buffer.from(await reponse.arrayBuffer())
	});
}

async function installerServices(context: BrowserContext) {
	const canton = fauxCanton(DOSSIERS);
	const dgmr = fauxDgmr({});
	const depot = fauxDepotConseils({
		'conseils/index.json': indexConseils(),
		'conseils/fil.json': filConseils([]),
		'conseils/import.json': { version: 1, genere: GENERE, conseils: {} },
		'etat-sources.json': { version: 1, genere: GENERE, sources: {} }
	});

	// Fond de carte swisstopo (style vectoriel) et image aérienne SWISSIMAGE.
	await context.route('https://vectortiles.geo.admin.ch/**', (r) => r.fulfill({ ...json(STYLE), headers: CORS }));
	await context.route('https://wmts.geo.admin.ch/**', (r) =>
		r.fulfill({ status: 200, contentType: 'image/png', headers: CORS, body: TUILE })
	);
	// Recherche d'adresses swisstopo.
	await context.route('https://api3.geo.admin.ch/rest/services/api/SearchServer?**', (r) =>
		r.fulfill({ ...json(LIEUX), headers: CORS })
	);
	// Service du canton : permis CAMAC (537), restrictions de la DGMR en cours (596) et à venir (595).
	await context.route(/^https:\/\/www\.ogc\.vd\.ch\/.*\/MapServer\/537\/query/, (r) => servir(r, canton.fetch));
	await context.route(/^https:\/\/www\.ogc\.vd\.ch\/.*\/MapServer\/59[56]\/query/, (r) => servir(r, dgmr.fetch));
	// Dépôt de données : l'index des trois conseils couverts, un fil vide, des états sans rien ; tout autre fichier est
	// absent (404).
	await context.route(`${DEPOT_DONNEES}/**`, (r) =>
		servir(r, depot.fetch, r.request().url().replace(DEPOT_DONNEES, DONNEES))
	);
}

/**
 * Arrive sur `adresse` et attend que la page réponde : les pages sont pré-générées, et un clic avant que Svelte ait
 * repris la main (hydratation) serait perdu. Le canevas de la carte n'existe qu'après ; caché quand la vue du
 * téléphone n'est pas la carte, il est là. MapLibre peut être lent à démarrer quand plusieurs pages dessinent en
 * WebGL sans carte graphique : d'où le délai.
 */
export async function arriver(page: Page, adresse: string) {
	await page.goto(adresse);
	await expect(page.locator('#carte canvas')).toBeAttached({ timeout: 30_000 });
}

export interface Reseau {
	/** Requêtes vers une autre machine qu'aucun service factice n'a prises : refusées, elles font échouer le scénario. */
	inattendues: string[];
}

export const test = base.extend<{ reseau: Reseau; sansErreur: void }>({
	// Une exception non rattrapée dans la page fait échouer le scénario, même si ce qu'il vérifie s'affiche.
	sansErreur: [
		async ({ context }, use) => {
			const erreurs: string[] = [];
			context.on('weberror', (e) => erreurs.push(e.error().message));
			await use();
			expect(erreurs, 'exceptions non rattrapées dans la page').toEqual([]);
		},
		{ auto: true }
	],
	reseau: [
		async ({ context }, use) => {
			const reseau: Reseau = { inattendues: [] };
			// Enregistrée en premier, la garde passe en dernier (Playwright essaie les routes de la plus récente à la plus
			// ancienne) : elle ne voit que ce qu'aucun service factice n'a pris.
			await context.route('**/*', (route) => {
				const url = new URL(route.request().url());
				if (LOCALES.has(url.hostname)) return route.continue();
				reseau.inattendues.push(`${route.request().method()} ${url.href}`);
				return route.abort('blockedbyclient');
			});
			await installerServices(context);
			await use(reseau);
			expect(reseau.inattendues, 'requêtes vers une autre machine, non interceptées').toEqual([]);
		},
		{ auto: true }
	]
});

export { expect };
