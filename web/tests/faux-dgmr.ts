import type { Commune } from '#lib/types.js';
import { carre, LUTRY, PULLY } from './faux-canton.js';

/**
 * Faux service de la DGMR (MapServer/596 en cours, 595 à venir) et fichiers des communes, pour les tests : un
 * `fetch` qui répond aux seules requêtes du module de données Routes, en GeoJSON, et garde la trace de chacune.
 *
 * Réponses fabriquées, jamais enregistrées : la norme DCG 8401 interdit de rediffuser les données de la DGMR, et
 * le dépôt est public. Les cas pièges de la recherche (`docs/recherche/source-dgmr.md`) sont recopiés à la main,
 * avec des noms et des numéros inventés.
 */

/** Les numéros des restrictions dans le MapServer de la DGMR : 596 celles en cours, 595 celles à venir. */
export type NumeroDgmr = 596 | 595;

export type Point = [number, number];
/** Un tracé : une ligne (`LineString`) ou plusieurs (`MultiLineString`), en WGS84. */
export type Trace = Point[] | Point[][];

/** Les 11 champs que lit le site, et deux codes internes qu'il ignore. */
export interface AttributsDgmr {
	OBJECTID: number;
	NOM: string | null;
	RESTRICTION: string | null;
	RHRC: string | null;
	/** Millisecondes : l'heure locale codée comme de l'UTC (voir `heureLocale`). */
	DATE_DEBUT: number;
	DATE_FIN: number;
	/** « HH:MM », seulement pour une plage quotidienne (fermeture de nuit). */
	HEURE_DEBUT: string | null;
	HEURE_FIN: string | null;
	/** Casse libre : « Oui », « oui », « Non », « non » ou vide. */
	WEEK_END: string | null;
	TYPE: string | null;
	REMARQUE: string | null;
	ENTITE: string | null;
	ARRDT: string | null;
}

export interface RestrictionDgmr {
	type: 'Feature';
	id: number;
	geometry: { type: 'LineString'; coordinates: Point[] } | { type: 'MultiLineString'; coordinates: Point[][] };
	properties: AttributsDgmr;
}

/**
 * Une heure de Lausanne telle que la DGMR l'écrit : ses composantes codées comme de l'UTC, sans conversion.
 * `heureLocale('2026-10-19T07:30')` vaut `Date.UTC(2026, 9, 19, 7, 30)`.
 */
export function heureLocale(iso: string): number {
	const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?$/);
	if (!m) throw new Error(`Heure illisible : ${iso}`);
	const [, a, mo, j, h = '0', mi = '0'] = m;
	return Date.UTC(Number(a), Number(mo) - 1, Number(j), Number(h), Number(mi));
}

/** Un tracé d'est en ouest au milieu de Pully, sur 0,01° de longitude (environ 770 m). */
export const TRACE_PULLY: Point[] = [
	[6.67, 46.5],
	[6.68, 46.5]
];

/**
 * Une restriction telle que la renvoie la DGMR en GeoJSON ; par défaut, une fermeture jour et nuit à Pully,
 * du 12 au 23 octobre 2026.
 */
export function restriction(objectid: number, attributs: Partial<AttributsDgmr> = {}, trace: Trace = TRACE_PULLY): RestrictionDgmr {
	const multi = Array.isArray(trace[0]?.[0]);
	return {
		type: 'Feature',
		id: objectid,
		geometry: multi
			? { type: 'MultiLineString', coordinates: trace as Point[][] }
			: { type: 'LineString', coordinates: trace as Point[] },
		properties: {
			OBJECTID: objectid,
			NOM: 'Pully, Chemin des Exemples',
			RESTRICTION: 'Fermeture',
			RHRC: '701-B-P',
			DATE_DEBUT: heureLocale('2026-10-12'),
			DATE_FIN: heureLocale('2026-10-23'),
			HEURE_DEBUT: null,
			HEURE_FIN: null,
			WEEK_END: 'Oui',
			TYPE: 'Revêtement',
			REMARQUE: null,
			ENTITE: 'Exemple',
			ARRDT: '1',
			...attributs
		}
	};
}

/**
 * Cas pièges de la recherche, recopiés à la main (numéros et noms inventés). Tous à venir sauf mention, comme dans
 * les vraies données : les plages quotidiennes n'y concernent que des fermetures de nuit à venir.
 */
export const PIEGES = {
	/** `HEURE_FIN` 05:30 contredit l'heure 23:59 de `DATE_FIN` : `HEURE_*` donne la plage, `DATE_*` les jours. */
	nuitFinContredite: restriction(9001, {
		NOM: 'Lutry, Route des Essais nuit',
		DATE_DEBUT: heureLocale('2026-10-26T19:30'),
		DATE_FIN: heureLocale('2026-10-29T23:59'),
		HEURE_DEBUT: '19:30',
		HEURE_FIN: '05:30',
		WEEK_END: 'non'
	}, [[6.71, 46.5], [6.72, 46.5]]),
	/** `DATE_FIN` à 00:00 (jour entier) mais `HEURE_FIN` 05:30 : de nouveau, `HEURE_*` donne la plage. */
	nuitFinMinuit: restriction(9002, {
		NOM: 'Lutry, Route des Essais nuit',
		DATE_DEBUT: heureLocale('2026-10-26'),
		DATE_FIN: heureLocale('2026-10-30'),
		HEURE_DEBUT: '20:00',
		HEURE_FIN: '05:30',
		WEEK_END: 'Non'
	}, [[6.72, 46.5], [6.73, 46.5]]),
	/** Casse libre de `WEEK_END`, et `WEEK_END` vide. */
	weekEndMinuscule: restriction(9003, { WEEK_END: 'oui' }),
	weekEndVide: restriction(9004, { WEEK_END: null, TYPE: null }),
	/** Un tracé en trois morceaux. */
	enMorceaux: restriction(9005, { RESTRICTION: 'Feux' }, [
		[[6.66, 46.5], [6.67, 46.5]],
		[[6.68, 46.5], [6.69, 46.5]],
		[[6.7, 46.505], [6.71, 46.505]]
	]),
	/** Une déviation dont un bout sort des communes connues (hors du canton). */
	deviationHorsCanton: restriction(9006, { RESTRICTION: 'Déviation' }, [
		[6.6, 46.5],
		[6.66, 46.5],
		[6.66, 46.51]
	])
} satisfies Record<string, RestrictionDgmr>;

/* ---- Le faux service ---- */

const PAGE = 2000;

/** Le sous-ensemble du SQL ArcGIS qu'emploie le module de données Routes. */
function filtre(where: string): (r: RestrictionDgmr) => boolean {
	if (where === '1=1') return () => true;
	let m = where.match(/^OBJECTID IN \(([\d,]+)\)$/);
	if (m) {
		const ids = new Set(m[1].split(',').map(Number));
		return (r) => ids.has(r.properties.OBJECTID);
	}
	// Une date telle qu'écrite par la DGMR : comparée sans conversion de fuseau.
	m = where.match(/^DATE_DEBUT >= (?:DATE '(\d{4}-\d{2}-\d{2})'|TIMESTAMP '(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}):\d{2}')$/);
	if (m) {
		const depuis = heureLocale(m[1] ?? `${m[2]}T${m[3]}`);
		return (r) => r.properties.DATE_DEBUT >= depuis;
	}
	throw new Error(`Requête non prévue par le faux DGMR : ${where}`);
}

export interface RequeteDgmr {
	numero: NumeroDgmr;
	where: string;
	/** Tous les paramètres reçus, pour vérifier par exemple qu'aucune emprise n'est envoyée. */
	parametres: URLSearchParams;
}

export interface FauxDgmr {
	fetch: typeof fetch;
	/** Requêtes reçues par la DGMR, dans l'ordre (pas celles des fichiers des communes). */
	requetes: RequeteDgmr[];
	/** Le numéro (les deux par défaut) répond désormais par cette erreur HTTP (`null` : rétabli). */
	panne(statut: number | null, numero?: NumeroDgmr): void;
	/** Le numéro (les deux par défaut) devient injoignable, comme sans réseau (`false` : rétabli). */
	horsLigne(oui: boolean, numero?: NumeroDgmr): void;
}

/**
 * Un faux `fetch` de la DGMR : `enCours` sert la 596, `aVenir` la 595. Il sert aussi `/communes.json` et
 * `/communes-limites.json` (limites carrées) pour le rattachement. Toute autre adresse ou requête lève une erreur.
 * Les pages suivent `resultOffset` et `resultRecordCount` (2000 au plus), et signalent la suite par
 * `properties.exceededTransferLimit`, comme ArcGIS en GeoJSON.
 */
export function fauxDgmr(
	{ enCours = [], aVenir = [] }: { enCours?: RestrictionDgmr[]; aVenir?: RestrictionDgmr[] },
	communes: Commune[] = [PULLY, LUTRY]
): FauxDgmr {
	const requetes: RequeteDgmr[] = [];
	const pannes = new Map<NumeroDgmr, number | null>();
	const injoignables = new Map<NumeroDgmr, boolean>();
	const numeros: Record<NumeroDgmr, RestrictionDgmr[]> = { 596: enCours, 595: aVenir };
	const json = (corps: unknown, status = 200) =>
		new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } });
	const pour = (numero: NumeroDgmr | undefined): NumeroDgmr[] => (numero ? [numero] : [596, 595]);

	const repondre = async (entree: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
		const url = new URL(entree instanceof Request ? entree.url : String(entree), 'http://localhost');
		if (url.pathname.endsWith('/communes.json')) return json(communes);
		if (url.pathname.endsWith('/communes-limites.json'))
			return json(Object.fromEntries(communes.map((c) => [c.bfs, carre(c.bbox)])));
		const m = url.pathname.match(/\/MapServer\/(596|595)\/query$/);
		if (url.hostname !== 'www.ogc.vd.ch' || !m) throw new Error(`Adresse non prévue : ${url}`);
		const numero = Number(m[1]) as NumeroDgmr;
		if (injoignables.get(numero)) throw new TypeError('Failed to fetch');
		const statut = pannes.get(numero);
		if (statut) return new Response('', { status: statut });

		const p = init?.body ? new URLSearchParams(String(init.body)) : url.searchParams;
		if (p.get('f') !== 'geojson') throw new Error(`Format non prévu par le faux DGMR : ${p.get('f')}`);
		const where = p.get('where') ?? '';
		requetes.push({ numero, where, parametres: p });
		const choisies = numeros[numero].filter(filtre(where));
		choisies.sort((a, b) => a.properties.OBJECTID - b.properties.OBJECTID);
		const debut = Number(p.get('resultOffset') ?? 0);
		const n = Math.min(Number(p.get('resultRecordCount') ?? PAGE), PAGE);
		const suite = choisies.length > debut + n;
		return json({
			type: 'FeatureCollection',
			features: choisies.slice(debut, debut + n),
			...(suite ? { properties: { exceededTransferLimit: true } } : {})
		});
	};

	return {
		fetch: repondre as typeof fetch,
		requetes,
		panne: (s, numero) => pour(numero).forEach((c) => pannes.set(c, s)),
		horsLigne: (oui, numero) => pour(numero).forEach((c) => injoignables.set(c, oui))
	};
}
