import { browser } from '$app/env';
import type { CauseEchec } from './fraicheur.js';
import type { Emprise } from './types.js';

/**
 * Client minimal du service ArcGIS du canton (couche « vd.demande_permis_construire », CAMAC), et ce qu'il partage
 * avec celui des restrictions de circulation de la DGMR, sur le même MapServer : l'appel `/query`, la pagination,
 * la nouvelle tentative et la cause d'un échec.
 *
 * Le site ne stocke ni ne rediffuse aucune donnée CAMAC ni DGMR : c'est le navigateur du visiteur qui interroge
 * directement www.ogc.vd.ch. Ce module refuse donc de s'exécuter ailleurs que dans le navigateur
 * (pré-génération, serveur de développement).
 */

/** Le MapServer public de l'État de Vaud. Le nom d'hôte sans `www.` ne se résout pas. */
export const MAPSERVER = 'https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer';
export const SERVICE = `${MAPSERVER}/537`;
/** Limite du serveur par réponse (`maxRecordCount`). */
export const PAGE = 2000;
/** Requêtes simultanées au plus vers le canton : par politesse, et les navigateurs en limitent le nombre. */
const SIMULTANEES = 6;
const DELAI_MS = 20_000;
/** Délai avant l'unique nouvelle tentative automatique d'un chargement raté. */
const RETENTE_MS = 5_000;
/** Au-delà, la requête part en POST (polygone d'une commune, longue liste de numéros). */
const URL_MAX = 1800;

type Fetch = typeof fetch;

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
	enveloppe?: Emprise;
}

export class ErreurApi extends Error {
	constructor(
		message: string,
		readonly hors_ligne = false
	) {
		super(message);
	}
}

/** Un service, tel que le nomment ses messages d'erreur. */
export interface NomService {
	/** « Le service du canton », « La DGMR » : « … ne répond pas. » */
	sujet: string;
	/** « du service du canton », « de la DGMR » : « Réponse illisible … » */
	complement: string;
}

/** Une réponse `/query` d'ArcGIS, en JSON ou en GeoJSON. */
export interface ReponseArcgis<E> {
	features?: E[];
	/** ArcGIS le place à la racine ou, en GeoJSON, sous `properties` selon les versions. */
	exceededTransferLimit?: boolean;
	properties?: { exceededTransferLimit?: boolean };
	error?: { message?: string };
}

/**
 * Un appel `/query` à un service ArcGIS, depuis le navigateur seulement, avec délai d'attente. Service injoignable
 * ou trop lent, erreur HTTP, réponse illisible et réponse d'erreur ArcGIS (HTTP 200) rejettent par `ErreurApi`,
 * hors ligne si le navigateur le dit.
 */
export async function appelArcgis<R>(f: Fetch, nom: NomService, adresse: string, init: RequestInit = {}): Promise<R> {
	if (!browser) throw new Error(`${nom.sujet} : appel réservé au navigateur.`);
	let r: Response;
	try {
		r = await f(adresse, { ...init, signal: AbortSignal.timeout(DELAI_MS) });
	} catch (e) {
		const delai = e instanceof DOMException && e.name === 'TimeoutError';
		throw new ErreurApi(
			delai ? `${nom.sujet} ne répond pas.` : `${nom.sujet} est injoignable.`,
			!delai && globalThis.navigator?.onLine === false
		);
	}
	if (!r.ok) throw new ErreurApi(`${nom.sujet} a répondu ${r.status}.`);
	const json: R & Pick<ReponseArcgis<unknown>, 'error'> = await r.json().catch(() => {
		throw new ErreurApi(`Réponse illisible ${nom.complement}.`);
	});
	if (json.error) throw new ErreurApi(`Erreur ${nom.complement} : ${json.error.message ?? 'inconnue'}.`);
	return json;
}

/**
 * La réponse annonce-t-elle une page suivante ? Oui si ArcGIS le dit (`exceededTransferLimit`), ou si la page est
 * pleine ; jamais après une page vide.
 */
export function aUneSuite(r: ReponseArcgis<unknown>): boolean {
	const n = r.features?.length ?? 0;
	return n > 0 && (Boolean(r.exceededTransferLimit || r.properties?.exceededTransferLimit) || n >= PAGE);
}

/** `g()`, et s'il échoue, une seule nouvelle tentative automatique au bout d'environ 5 s. */
export function retenterUneFois<T>(g: () => Promise<T>): Promise<T> {
	return g().catch(async () => {
		await new Promise((ok) => setTimeout(ok, RETENTE_MS));
		return g();
	});
}

/** La cause d'un échec : hors ligne si le navigateur le dit (ou le client), sinon le service est indisponible. */
export const causeEchec = (e: unknown): CauseEchec =>
	(e instanceof ErreurApi && e.hors_ligne) || globalThis.navigator?.onLine === false ? 'hors_ligne' : 'indisponible';

export interface ClientCanton {
	compter(q: Requete): Promise<number>;
	/**
	 * Toutes les entités d'une requête : le nombre total et la première page partent ensemble,
	 * puis les pages restantes en parallèle. `resultRecordCount` limite le total (une seule page).
	 */
	chercher(q: Requete): Promise<Entite[]>;
}

const CANTON: NomService = { sujet: 'Le service du canton', complement: 'du service du canton' };

/**
 * Client du service du canton, à créer une seule fois : il tient la file d'attente (au plus SIMULTANEES
 * requêtes en vol) et le cache mémoire (une même requête n'est envoyée qu'une fois par visite ; les échecs
 * sont oubliés).
 */
export function creerClientCanton(f: Fetch): ClientCanton {
	/* ---- File d'attente : au plus SIMULTANEES requêtes en vol. ---- */

	let enVol = 0;
	const attente: (() => void)[] = [];
	async function tour<T>(g: () => Promise<T>): Promise<T> {
		if (enVol >= SIMULTANEES) await new Promise<void>((r) => attente.push(r));
		enVol++;
		try {
			return await g();
		} finally {
			enVol--;
			attente.shift()?.();
		}
	}

	/** Un appel `/query`, avec délai d'attente ; la réponse d'erreur ArcGIS (HTTP 200) devient une exception. */
	async function appel<T>(p: URLSearchParams): Promise<T> {
		return tour(() => {
			const corps = p.toString();
			const get = SERVICE.length + corps.length + 8 < URL_MAX;
			return appelArcgis<T>(f, CANTON, get ? `${SERVICE}/query?${corps}` : `${SERVICE}/query`, {
				method: get ? 'GET' : 'POST',
				// Formulaire simple : pas de requête CORS préalable (OPTIONS).
				headers: get ? undefined : { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: get ? undefined : corps
			});
		});
	}

	/* ---- Cache mémoire : une même requête n'est envoyée qu'une fois par visite ; les échecs sont oubliés. ---- */

	const cache = new Map<string, Promise<unknown>>();
	function enCache<T>(cle: string, g: () => Promise<T>): Promise<T> {
		let p = cache.get(cle) as Promise<T> | undefined;
		if (!p) {
			p = g();
			cache.set(cle, p);
			p.catch(() => cache.delete(cle));
		}
		return p;
	}

	function compter(q: Requete): Promise<number> {
		const p = parametres({ ...q, returnCountOnly: true, returnGeometry: false });
		return enCache(`n:${p}`, () => appel<{ count: number }>(p).then((r) => r.count));
	}

	function chercher(q: Requete): Promise<Entite[]> {
		const base = { orderByFields: 'OBJECTID', ...q };
		return enCache(`q:${parametres(base)}`, async () => {
			const page = (offset: number, n = PAGE) =>
				appel<ReponseArcgis<Entite>>(parametres({ ...base, resultOffset: offset, resultRecordCount: n }));
			if (q.resultRecordCount) return (await page(0, q.resultRecordCount)).features ?? [];
			const [total, premiere] = await Promise.all([compter(q), page(0)]);
			if (!aUneSuite(premiere)) return premiere.features ?? [];
			const suite = [];
			for (let o = PAGE; o < total; o += PAGE) suite.push(page(o));
			return [premiere, ...(await Promise.all(suite))].flatMap((r) => r.features ?? []);
		});
	}

	return { compter, chercher };
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

/** Chaîne SQL échappée. */
export const sql = (s: string) => `'${s.replace(/'/g, "''")}'`;
