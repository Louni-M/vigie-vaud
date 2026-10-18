import { browser } from '$app/env';
import { ErreurApi } from '#lib/api.js';
import type { EtatRestriction } from './etats.js';
import type { Geometrie } from './trace.js';

/**
 * Client minimal des restrictions de circulation de la DGMR, sur le MapServer de l'État de Vaud : 596 (en cours) et
 * 595 (à venir), deux filtres par date d'une même table.
 *
 * Le site ne stocke ni ne rediffuse aucune donnée de la DGMR (norme DCG 8401) : c'est le navigateur du visiteur
 * qui interroge directement www.ogc.vd.ch. Ce module refuse donc de s'exécuter ailleurs que dans le navigateur
 * (pré-génération, serveur de développement). Aucune requête ne porte d'emprise : l'État de Vaud ne reçoit pas la
 * zone affichée.
 */

/** Le nom d'hôte sans `www.` ne se résout pas. */
export const SERVICE = 'https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer';

/** Le numéro des restrictions de chaque état dans le MapServer : 596 en cours, 595 à venir. */
const NUMEROS: Record<EtatRestriction, number> = { en_cours: 596, a_venir: 595 };

/** Les 11 champs que lit le site (ceux que vérifie la sonde de `sources.json`). Ni `ENTITE` ni `ARRDT`. */
export const CHAMPS = [
	'OBJECTID',
	'NOM',
	'RESTRICTION',
	'RHRC',
	'DATE_DEBUT',
	'DATE_FIN',
	'HEURE_DEBUT',
	'HEURE_FIN',
	'WEEK_END',
	'TYPE',
	'REMARQUE'
] as const;

export type AttributsDgmr = Record<(typeof CHAMPS)[number], string | number | null>;

/** Une restriction telle que la DGMR la renvoie en GeoJSON. */
export interface EntiteDgmr {
	properties: AttributsDgmr;
	geometry: Geometrie | null;
}

/** Limite du serveur par réponse (`maxRecordCount`). */
const PAGE = 2000;
const DELAI_MS = 20_000;

type Fetch = typeof fetch;

interface Reponse {
	features?: EntiteDgmr[];
	/** ArcGIS le place à la racine ou, en GeoJSON, sous `properties` selon les versions. */
	exceededTransferLimit?: boolean;
	properties?: { exceededTransferLimit?: boolean };
	error?: { message?: string };
}

export interface ClientDgmr {
	/**
	 * Toutes les restrictions de l'état `etat` (la 596 en cours, la 595 à venir) qui répondent à `where` (SQL
	 * ArcGIS : `1=1`, `OBJECTID IN (…)`, `DATE_DEBUT >= DATE 'AAAA-MM-JJ'`), en WGS84, pages de 2000 suivies jusqu'au
	 * bout. Rejette par `ErreurApi`.
	 * Le service compare `DATE '…'` à la date telle qu'écrite, minuit compris, sans conversion de fuseau (vérifié
	 * sur la 596 le 18.10.2026).
	 */
	chercher(etat: EtatRestriction, where: string): Promise<EntiteDgmr[]>;
}

export function creerClientDgmr(f: Fetch): ClientDgmr {
	async function page(etat: EtatRestriction, where: string, offset: number): Promise<Reponse> {
		if (!browser) throw new Error('DGMR : appel réservé au navigateur.');
		const p = new URLSearchParams({
			where,
			outFields: CHAMPS.join(','),
			orderByFields: 'OBJECTID',
			outSR: '4326',
			geometryPrecision: '6',
			resultOffset: String(offset),
			resultRecordCount: String(PAGE),
			f: 'geojson'
		});
		let r: Response;
		try {
			r = await f(`${SERVICE}/${NUMEROS[etat]}/query?${p}`, { signal: AbortSignal.timeout(DELAI_MS) });
		} catch (e) {
			const delai = e instanceof DOMException && e.name === 'TimeoutError';
			throw new ErreurApi(
				delai ? 'La DGMR ne répond pas.' : 'La DGMR est injoignable.',
				!delai && globalThis.navigator?.onLine === false
			);
		}
		if (!r.ok) throw new ErreurApi(`La DGMR a répondu ${r.status}.`);
		const json: Reponse = await r.json().catch(() => {
			throw new ErreurApi('Réponse illisible de la DGMR.');
		});
		if (json.error) throw new ErreurApi(`Erreur de la DGMR : ${json.error.message ?? 'inconnue'}.`);
		return json;
	}

	async function chercher(etat: EtatRestriction, where: string): Promise<EntiteDgmr[]> {
		const toutes: EntiteDgmr[] = [];
		for (let offset = 0; ; offset += PAGE) {
			const r = await page(etat, where, offset);
			const features = r.features ?? [];
			toutes.push(...features);
			const suite = r.exceededTransferLimit || r.properties?.exceededTransferLimit;
			if (!features.length || (!suite && features.length < PAGE)) return toutes;
		}
	}

	return { chercher };
}
