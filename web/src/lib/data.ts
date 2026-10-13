import { chercher, sql, type Entite, type Requete } from './api';
import { getRattachement, type Rattachement } from './communes';
import { masquerNoms, nettoyer } from './masquage';
import type { Commune, Dossier, PointHisto, Statut } from './types';

export { getCommunes } from './communes';
export { ErreurApi } from './api';

/**
 * Données CAMAC, lues en direct sur le service du canton depuis le navigateur.
 * Les conversions reprennent celles de pipeline/fetch.py (`normalize`).
 */

type Fetch = typeof fetch;

export const SOURCE = 'Source : Géodonnées Etat de Vaud (CAMAC), consultées en direct';

const STATUT: Record<string, Statut> = {
	'Enquête publique en cours': 'enquete',
	'Procédure en cours': 'procedure',
	'Permis délivré': 'delivre',
	Réalisé: 'realise',
	'Abandonné/refusé': 'abandonne'
};
const ETAT = Object.fromEntries(Object.entries(STATUT).map(([k, v]) => [v, k])) as Record<Statut, string>;

const NATURE: Record<string, string> = {
	'Construction nouvelle': 'construction',
	Transformation: 'transformation',
	'Transformation(s)': 'transformation',
	Adjonction: 'adjonction',
	Agrandissement: 'agrandissement',
	'Changement ou nouvelle destination des locaux': 'changement',
	'Reconstruction après démolition': 'reconstruction',
	'Reconstruction après incendie': 'reconstruction_incendie',
	'Rénovation totale': 'renovation',
	'Démolition totale': 'demolition',
	'Démolition partielle': 'demolition_partielle'
};

/** Année de début d'enquête, en SQL : DATE_ENQUETE vaut toujours « Du jj.mm.aaaa au … ». */
const ANNEE_SQL = 'SUBSTRING(DATE_ENQUETE FROM 10 FOR 4)';
/** Comme pipeline/fetch.py : les « procédures en cours » plus anciennes ne sont jamais clôturées dans la couche. */
const ACTIVE_PROCEDURE_YEARS = 3;

/** « 17.01.2026 » ou « 17/01/2026 » → « 2026-01-17 ». */
const DATE_RE = /(\d{2})[./](\d{2})[./](\d{4})/g;
function dates(s: unknown): string[] {
	return [...String(s ?? '').matchAll(DATE_RE)].map((m) => `${m[3]}-${m[2]}-${m[1]}`);
}

const texte = (v: unknown) => (v == null || v === '' ? undefined : String(v));
const statutDe = (etat: unknown) => STATUT[String(etat ?? '')] ?? 'autre';
const natureDe = (n: unknown) => NATURE[String(n ?? '')] ?? 'autre';

function versPoint({ attributes: a, geometry: g }: Entite): PointHisto {
	const [debut, fin] = dates(a.DATE_ENQUETE);
	return {
		id: Number(a.NO_CAMAC),
		statut: statutDe(a.ETAT),
		nature: natureDe(a.NATURE),
		debut,
		fin,
		lon: g?.x ?? 0,
		lat: g?.y ?? 0
	};
}

function versDossier(e: Entite, r: Rattachement): Dossier {
	const a = e.attributes;
	const p = versPoint(e);
	const c = r.communeDe(p.lon, p.lat);
	const d: Dossier = {
		...p,
		fao: texte(a.NO_FAO),
		description: texte(masquerNoms(nettoyer(texte(a.DESCRIPTION)))),
		decision: texte(a.DECISION_COMMUNALE),
		date_decision: dates(a.DATE_DECISION)[0],
		url: texte(a.URL),
		bfs: c.bfs,
		commune: c.nom,
		slug: c.slug
	};
	for (const k of Object.keys(d) as (keyof Dossier)[]) if (d[k] === undefined) delete d[k];
	return d;
}

const CHAMPS_DOSSIER = 'NO_CAMAC,NO_FAO,DATE_ENQUETE,NATURE,DESCRIPTION,DECISION_COMMUNALE,DATE_DECISION,URL,ETAT';
const CHAMPS_POINT = 'NO_CAMAC,ETAT,NATURE,DATE_ENQUETE';

async function dossiers(f: Fetch, q: Requete): Promise<Dossier[]> {
	const [entites, r] = await Promise.all([chercher({ outFields: CHAMPS_DOSSIER, ...q }), getRattachement(f)]);
	return entites.map((e) => versDossier(e, r));
}

/* ---- Dossiers en cours : chargés à l'ouverture de la carte. ---- */

const auj = new Date();
/** Date de début d'enquête au-delà de laquelle une « procédure en cours » compte comme en cours. */
const LIMITE_PROCEDURE = `${auj.getFullYear() - ACTIVE_PROCEDURE_YEARS}${auj.toISOString().slice(4, 10)}`;
/** Dossiers en cours, au plus près côté serveur (année seulement) ; le jour exact est filtré ensuite. */
const EN_COURS_SQL =
	`(ETAT = ${sql(ETAT.enquete)} OR ` +
	`(ETAT = ${sql(ETAT.procedure)} AND ${ANNEE_SQL} >= '${LIMITE_PROCEDURE.slice(0, 4)}'))`;

let actifs: Promise<Dossier[]> | null = null;
export function getActive(f: Fetch): Promise<Dossier[]> {
	if (actifs) return actifs;
	const limite = LIMITE_PROCEDURE;
	actifs = dossiers(f, { where: EN_COURS_SQL }).then((ds) => {
		retenir(ds);
		return ds.filter((d) => d.statut === 'enquete' || (d.debut ?? '') >= limite).sort((a, b) => a.id - b.id);
	});
	actifs.catch(() => (actifs = null));
	return actifs;
}

/* ---- Fiches : à l'unité, ou par lots pour la liste de l'historique. ---- */

const fiches = new Map<number, Dossier>();

export async function getDossier(f: Fetch, id: number): Promise<Dossier | undefined> {
	if (!fiches.has(id)) await getDossiers(f, [id]);
	return fiches.get(id);
}

/** Fiches complètes des numéros demandés (déjà chargées, ou par lots de 300 numéros). */
export async function getDossiers(f: Fetch, ids: number[], signal?: AbortSignal): Promise<Dossier[]> {
	const manquants = [...new Set(ids)].filter((id) => !fiches.has(id) && Number.isInteger(id));
	const lots = [];
	for (let i = 0; i < manquants.length; i += 300) lots.push(manquants.slice(i, i + 300));
	await Promise.all(
		lots.map(async (lot) => {
			for (const d of await dossiers(f, { where: `NO_CAMAC IN (${lot.join(',')})` })) fiches.set(d.id, d);
		})
	);
	signal?.throwIfAborted();
	return ids.flatMap((id) => fiches.get(id) ?? []);
}

/** Garde en mémoire des fiches déjà obtenues (dossiers en cours, pages commune). */
export function retenir(ds: Dossier[]) {
	for (const d of ds) fiches.set(d.id, d);
}

/* ---- Historique de la carte : points légers, une année à la fois. ---- */

export const getHistoAnnee = (annee: number): Promise<PointHisto[]> =>
	chercher({ where: `${ANNEE_SQL} = '${annee}'`, outFields: CHAMPS_POINT }).then((es) => es.map(versPoint));

/* ---- Pages commune ---- */

export interface ChiffresCommune {
	statuts: Record<Statut, number>;
	parAnnee: Record<string, number>;
	/** Dossiers hors dossiers en cours, publication la plus récente d'abord. */
	historique: PointHisto[];
}

/** Marge autour de l'emprise : dossiers sur un lac, rattachés à la commune riveraine la plus proche. */
const MARGE = 0.01;

/**
 * Chiffres d'une commune, calculés dans le navigateur sur les points légers de son emprise,
 * rattachés à la commune comme sur la carte : chiffres et listes concordent.
 */
export async function getChiffresCommune(f: Fetch, c: Commune): Promise<ChiffresCommune> {
	const [w, s, e, n] = c.bbox;
	const [entites, r] = await Promise.all([
		chercher({ where: '1=1', outFields: CHAMPS_POINT, enveloppe: [w - MARGE, s - MARGE, e + MARGE, n + MARGE] }),
		getRattachement(f)
	]);
	const statuts = { enquete: 0, procedure: 0, delivre: 0, realise: 0, abandonne: 0, autre: 0 };
	const parAnnee: Record<string, number> = {};
	const historique: PointHisto[] = [];
	for (const ent of entites) {
		const p = versPoint(ent);
		if (r.communeDe(p.lon, p.lat).slug !== c.slug) continue;
		statuts[p.statut]++;
		if (p.debut) parAnnee[p.debut.slice(0, 4)] = (parAnnee[p.debut.slice(0, 4)] ?? 0) + 1;
		const enCours = p.statut === 'enquete' || (p.statut === 'procedure' && (p.debut ?? '') >= LIMITE_PROCEDURE);
		if (!enCours) historique.push(p);
	}
	historique.sort((a, b) => (b.debut ?? '').localeCompare(a.debut ?? '') || b.id - a.id);
	return { statuts, parAnnee, historique };
}
