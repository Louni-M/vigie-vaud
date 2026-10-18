import { appelArcgis, aUneSuite, MAPSERVER, PAGE, type NomService, type ReponseArcgis } from '#lib/api.js';
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

const DGMR: NomService = { sujet: 'La DGMR', complement: 'de la DGMR' };

type Fetch = typeof fetch;

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
	async function chercher(etat: EtatRestriction, where: string): Promise<EntiteDgmr[]> {
		const toutes: EntiteDgmr[] = [];
		for (let offset = 0; ; offset += PAGE) {
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
			const r = await appelArcgis<ReponseArcgis<EntiteDgmr>>(f, DGMR, `${MAPSERVER}/${NUMEROS[etat]}/query?${p}`);
			toutes.push(...(r.features ?? []));
			if (!aUneSuite(r)) return toutes;
		}
	}

	return { chercher };
}
