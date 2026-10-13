import { browser } from '$app/env';

/**
 * Client minimal du service ArcGIS du canton (couche « vd.demande_permis_construire », CAMAC).
 *
 * Le site ne stocke ni ne rediffuse aucune donnée CAMAC : c'est le navigateur du visiteur qui interroge
 * directement ogc.vd.ch. Ce module refuse donc de s'exécuter ailleurs que dans le navigateur
 * (pré-génération, serveur de développement).
 */

export const SERVICE = 'https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer/537';
/** Limite du serveur par réponse (`maxRecordCount`). */
const PAGE = 2000;
/** Requêtes simultanées au plus vers le canton : par politesse, et les navigateurs en limitent le nombre. */
const SIMULTANEES = 6;
const DELAI_MS = 20_000;
/** Au-delà, la requête part en POST (polygone d'une commune, longue liste de numéros). */
const URL_MAX = 1800;

export type Attributs = Record<string, string | number | null>;
export interface Entite {
	attributes: Attributs;
	geometry?: { x: number; y: number };
}
export interface Requete {
	where: string;
	outFields?: string;
	returnGeometry?: boolean;
	orderByFields?: string;
	resultRecordCount?: number;
	/**
	 * Emprise [ouest, sud, est, nord] en WGS84. Pas de polygone : avec un polygone, ce serveur tronque
	 * les résultats (limite de 2000 appliquée avant le filtre spatial) et ses comptages divergent.
	 */
	enveloppe?: [number, number, number, number];
}

export class ErreurApi extends Error {
	constructor(
		message: string,
		readonly hors_ligne = false
	) {
		super(message);
	}
}

/* ---- File d'attente : au plus SIMULTANEES requêtes en vol. ---- */

let enVol = 0;
const attente: (() => void)[] = [];
async function tour<T>(f: () => Promise<T>): Promise<T> {
	if (enVol >= SIMULTANEES) await new Promise<void>((r) => attente.push(r));
	enVol++;
	try {
		return await f();
	} finally {
		enVol--;
		attente.shift()?.();
	}
}

function parametres(q: Requete & Record<string, unknown>): URLSearchParams {
	const p = new URLSearchParams({ f: 'json' });
	for (const [k, v] of Object.entries(q)) {
		if (v == null || k === 'enveloppe') continue;
		p.set(k, typeof v === 'string' ? v : JSON.stringify(v));
	}
	if (q.returnGeometry !== false) {
		p.set('outSR', '4326');
		p.set('geometryPrecision', '5');
	}
	if (q.enveloppe) {
		p.set('geometry', q.enveloppe.join(','));
		p.set('geometryType', 'esriGeometryEnvelope');
		p.set('inSR', '4326');
		p.set('spatialRel', 'esriSpatialRelIntersects');
	}
	return p;
}

/** Un appel `/query`, avec délai d'attente ; la réponse d'erreur ArcGIS (HTTP 200) devient une exception. */
async function appel<T>(p: URLSearchParams): Promise<T> {
	if (!browser) throw new Error('API cantonale : appel réservé au navigateur.');
	return tour(async () => {
		const corps = p.toString();
		const get = SERVICE.length + corps.length + 8 < URL_MAX;
		let r: Response;
		try {
			r = await fetch(get ? `${SERVICE}/query?${corps}` : `${SERVICE}/query`, {
				method: get ? 'GET' : 'POST',
				// Formulaire simple : pas de requête CORS préalable (OPTIONS).
				headers: get ? undefined : { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: get ? undefined : corps,
				signal: AbortSignal.timeout(DELAI_MS)
			});
		} catch (e) {
			const delai = e instanceof DOMException && e.name === 'TimeoutError';
			throw new ErreurApi(
				delai ? 'Le service du canton ne répond pas.' : 'Le service du canton est injoignable.',
				!delai && !navigator.onLine
			);
		}
		if (!r.ok) throw new ErreurApi(`Le service du canton a répondu ${r.status}.`);
		const json = await r.json().catch(() => {
			throw new ErreurApi('Réponse illisible du service du canton.');
		});
		if (json.error) throw new ErreurApi(`Erreur du service du canton : ${json.error.message ?? 'inconnue'}.`);
		return json as T;
	});
}

/* ---- Cache mémoire : une même requête n'est envoyée qu'une fois par visite ; les échecs sont oubliés. ---- */

const cache = new Map<string, Promise<unknown>>();
function enCache<T>(cle: string, f: () => Promise<T>): Promise<T> {
	let p = cache.get(cle) as Promise<T> | undefined;
	if (!p) {
		p = f();
		cache.set(cle, p);
		p.catch(() => cache.delete(cle));
	}
	return p;
}

/** Rejette dès que `signal` est interrompu ; la requête sous-jacente continue et reste en cache. */
export function annulable<T>(p: Promise<T>, signal?: AbortSignal): Promise<T> {
	if (!signal) return p;
	if (signal.aborted) return Promise.reject(signal.reason);
	return new Promise<T>((ok, ko) => {
		const stop = () => ko(signal.reason);
		signal.addEventListener('abort', stop, { once: true });
		p.then(ok, ko).finally(() => signal.removeEventListener('abort', stop));
	});
}

export function compter(q: Requete): Promise<number> {
	const p = parametres({ ...q, returnCountOnly: true, returnGeometry: false });
	return enCache(`n:${p}`, () => appel<{ count: number }>(p).then((r) => r.count));
}

/**
 * Toutes les entités d'une requête : le nombre total et la première page partent ensemble,
 * puis les pages restantes en parallèle. `resultRecordCount` limite le total (une seule page).
 */
export function chercher(q: Requete): Promise<Entite[]> {
	const base = { orderByFields: 'OBJECTID', ...q };
	return enCache(`q:${parametres(base)}`, async () => {
		const page = (offset: number, n = PAGE) =>
			appel<{ features: Entite[]; exceededTransferLimit?: boolean }>(
				parametres({ ...base, resultOffset: offset, resultRecordCount: n })
			);
		if (q.resultRecordCount) return (await page(0, q.resultRecordCount)).features;
		const [total, premiere] = await Promise.all([compter(q), page(0)]);
		if (!premiere.exceededTransferLimit && premiere.features.length < PAGE) return premiere.features;
		const suite = [];
		for (let o = PAGE; o < total; o += PAGE) suite.push(page(o));
		return [premiere, ...(await Promise.all(suite))].flatMap((r) => r.features);
	});
}

/** Chaîne SQL échappée. */
export const sql = (s: string) => `'${s.replace(/'/g, "''")}'`;
