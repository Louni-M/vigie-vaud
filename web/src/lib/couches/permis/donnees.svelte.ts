import { creerClientCanton, ErreurApi, sql, type Entite, type Requete } from '#lib/api.js';
import { inscrireEtat, type CauseEchec, type EtatSourceExecution } from '#lib/fraicheur.js';
import { getRattachement, type Rattachement } from '#lib/socle/communes.js';
import { masquerNoms, nettoyer } from '#lib/masquage.js';
import { source } from '#lib/sources.js';
import type { Commune, Dossier, PointHisto, Statut, Zone } from '#lib/types.js';

/**
 * Module de données de la couche Permis, partagé par ses composants : dossiers CAMAC lus en direct sur
 * le service du canton depuis le navigateur. Les conversions reprennent `normalize` du script de la version
 * hébergée (étiquette `chantiers-hebergee`).
 */

type Fetch = typeof fetch;

export const SOURCE = `Source : ${source('camac-permis').attribution.texte}, consultées en direct`;

/* ---- Conversion CAMAC → Dossier (privée) ---- */

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
/** Comme dans la version hébergée : les « procédures en cours » plus anciennes ne sont jamais clôturées dans la couche. */
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

/** N° au plus par requête de fiches. */
const LOT = 300;
const CHAMPS_DOSSIER = 'NO_CAMAC,NO_FAO,DATE_ENQUETE,NATURE,DESCRIPTION,DECISION_COMMUNALE,DATE_DECISION,URL,ETAT';
const CHAMPS_POINT = 'NO_CAMAC,ETAT,NATURE,DATE_ENQUETE';

/* ---- Module de données ---- */

export interface DonneesPermis {
	/** Dossiers en cours (vide tant qu'ils ne sont pas chargés), par n° croissant. */
	readonly actifs: Dossier[];
	/**
	 * Charge les dossiers en cours, une seule fois par visite. Un échec est retenté une fois au bout d'environ 5 s,
	 * puis la source passe en erreur ; un nouvel appel recommence.
	 */
	chargerActifs(): Promise<Dossier[]>;
	/** Points légers de l'historique déjà chargés, toutes années confondues (dossiers en cours compris). */
	readonly histo: PointHisto[];
	/** Des années de l'historique sont en cours de chargement. */
	readonly histoChargement: boolean;
	/** Une année au moins n'a pas pu être chargée au dernier appel de `chargerHisto` : historique partiel. */
	readonly histoEchec: boolean;
	/** Charge l'historique de l'année en cours jusqu'à `depuis`, sans redemander les années déjà obtenues. */
	chargerHisto(depuis: number): Promise<void>;
	/** Fiche complète d'un dossier, ou `undefined` si le canton ne la connaît pas. */
	fiche(id: number): Promise<Dossier | undefined>;
	/**
	 * Fiches complètes des n° demandés, dans le même ordre (n° inconnus omis) : déjà en mémoire,
	 * ou chargées par lots de 300 n°. `signal` interrompu : rejette, mais les fiches obtenues restent en mémoire.
	 */
	fiches(ids: number[], signal?: AbortSignal): Promise<Dossier[]>;
	/**
	 * Chiffres d'une commune, calculés dans le navigateur sur les points légers de son emprise,
	 * rattachés à la commune comme sur la carte : chiffres et listes concordent.
	 */
	chiffres(commune: Commune): Promise<ChiffresCommune>;
	/** État de la source CAMAC : heure de la dernière consultation réussie, échec, nouvel essai. */
	readonly source: EtatSourceExecution;
}

export interface ChiffresCommune {
	statuts: Record<Statut, number>;
	parAnnee: Record<string, number>;
	/** Dossiers hors dossiers en cours, publication la plus récente d'abord. */
	historique: PointHisto[];
}

/** Délai avant l'unique nouvelle tentative automatique d'un chargement raté. */
const RETENTE_MS = 5_000;

/** Hors ligne si le navigateur le dit (ou le client du canton), sinon le service est tenu pour indisponible. */
const causeDe = (e: unknown): CauseEchec =>
	(e instanceof ErreurApi && e.hors_ligne) || globalThis.navigator?.onLine === false ? 'hors_ligne' : 'indisponible';

/** Marge autour de l'emprise : dossiers sur un lac, rattachés à la commune riveraine la plus proche. */
const MARGE = 0.01;

export interface Options {
	/** `fetch` du navigateur, pour le service du canton et les fichiers des communes. */
	fetch: Fetch;
	/** Horloge : « dossiers en cours » et année courante en dépendent. */
	maintenant?: () => Date;
}

export function creerDonneesPermis({ fetch: f, maintenant = () => new Date() }: Options): DonneesPermis {
	/* ---- État de la source : chaque réponse du canton date la consultation (pas une réponse tirée du cache). ---- */

	let derniere = $state.raw<Date | null>(null);
	const canton = creerClientCanton(async (entree, init) => {
		const r = await f(entree, init);
		if (r.ok) derniere = maintenant();
		return r;
	});

	let erreur = $state<CauseEchec | null>(null);
	/**
	 * Un chargement principal de la source (dossiers en cours, chiffres d'une commune) : un échec est retenté une
	 * seule fois, au bout de RETENTE_MS ; si la nouvelle tentative échoue aussi, la source passe en erreur.
	 */
	async function charge<T>(g: () => Promise<T>): Promise<T> {
		try {
			const r = await g().catch(async () => {
				await new Promise((ok) => setTimeout(ok, RETENTE_MS));
				return g();
			});
			erreur = null;
			return r;
		} catch (e) {
			erreur = causeDe(e);
			throw e;
		}
	}

	async function dossiers(q: Requete): Promise<Dossier[]> {
		const [entites, r] = await Promise.all([canton.chercher({ outFields: CHAMPS_DOSSIER, ...q }), getRattachement(f)]);
		return entites.map((e) => versDossier(e, r));
	}

	/* ---- Dossiers en cours ---- */

	const auj = maintenant();
	/** Date de début d'enquête au-delà de laquelle une « procédure en cours » compte comme en cours. */
	const LIMITE_PROCEDURE = `${auj.getFullYear() - ACTIVE_PROCEDURE_YEARS}${auj.toISOString().slice(4, 10)}`;
	/** Dossiers en cours, au plus près côté serveur (année seulement) ; le jour exact est filtré ensuite. */
	const EN_COURS_SQL =
		`(ETAT = ${sql(ETAT.enquete)} OR ` +
		`(ETAT = ${sql(ETAT.procedure)} AND ${ANNEE_SQL} >= '${LIMITE_PROCEDURE.slice(0, 4)}'))`;

	let actifs = $state.raw<Dossier[]>([]);
	let chargementActifs: Promise<Dossier[]> | null = null;
	function chargerActifs(): Promise<Dossier[]> {
		if (chargementActifs) return chargementActifs;
		const p = charge(() => dossiers({ where: EN_COURS_SQL })).then((ds) => {
			const r = ds
				.filter((d) => d.statut === 'enquete' || (d.debut ?? '') >= LIMITE_PROCEDURE)
				.sort((a, b) => a.id - b.id);
			retenir(ds);
			actifs = r;
			return r;
		});
		chargementActifs = p;
		p.catch(() => (chargementActifs = null));
		return p;
	}

	/* ---- Fiches : à l'unité, ou par lots pour les listes. ---- */

	const cache = new Map<number, Dossier>();
	/** Garde en mémoire des fiches déjà obtenues (dossiers en cours). */
	function retenir(ds: Dossier[]) {
		for (const d of ds) cache.set(d.id, d);
	}

	async function fiches(ids: number[], signal?: AbortSignal): Promise<Dossier[]> {
		const manquants = [...new Set(ids)].filter((id) => !cache.has(id) && Number.isInteger(id));
		const lots = [];
		for (let i = 0; i < manquants.length; i += LOT) lots.push(manquants.slice(i, i + LOT));
		await Promise.all(lots.map(async (lot) => retenir(await dossiers({ where: `NO_CAMAC IN (${lot.join(',')})` }))));
		signal?.throwIfAborted();
		return ids.flatMap((id) => cache.get(id) ?? []);
	}

	async function fiche(id: number): Promise<Dossier | undefined> {
		if (!cache.has(id)) await fiches([id]);
		return cache.get(id);
	}

	/*
	 * Historique de la carte : points légers lus une année à la fois, de l'année en cours jusqu'à
	 * « depuis ». Les fiches complètes ne sont chargées que pour les dossiers listés.
	 */

	let histo = $state.raw<PointHisto[]>([]);
	let histoEnCours = $state(0);
	let histoEchec = $state(false);
	const anneesDemandees = new Set<number>();

	function chargerHisto(depuis: number): Promise<void> {
		histoEchec = false;
		const chargements = [];
		for (let a = maintenant().getFullYear(); a >= depuis; a--) {
			if (anneesDemandees.has(a)) continue;
			anneesDemandees.add(a);
			histoEnCours++;
			chargements.push(
				canton
					.chercher({ where: `${ANNEE_SQL} = '${a}'`, outFields: CHAMPS_POINT })
					.then(
						(es) => (histo = histo.concat(es.map(versPoint))),
						() => {
							anneesDemandees.delete(a);
							histoEchec = true;
						}
					)
					.finally(() => histoEnCours--)
			);
		}
		return Promise.all(chargements).then(() => {});
	}

	/* ---- Chiffres d'une commune ---- */

	async function chiffres(c: Commune): Promise<ChiffresCommune> {
		const [w, s, e, n] = c.bbox;
		const [entites, r] = await charge(() =>
			Promise.all([
				canton.chercher({
					where: '1=1',
					outFields: CHAMPS_POINT,
					enveloppe: [w - MARGE, s - MARGE, e + MARGE, n + MARGE]
				}),
				getRattachement(f)
			])
		);
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
		historique.sort(parPublication);
		return { statuts, parAnnee, historique };
	}

	return {
		get actifs() {
			return actifs;
		},
		chargerActifs,
		get histo() {
			return histo;
		},
		get histoChargement() {
			return histoEnCours > 0;
		},
		get histoEchec() {
			return histoEchec;
		},
		chargerHisto,
		fiche,
		fiches,
		chiffres,
		source: {
			get derniere() {
				return derniere;
			},
			get erreur() {
				return erreur;
			},
			/**
			 * Lève l'erreur, ce qui fait recharger les composants qui l'affichaient, et recharge les dossiers en
			 * cours s'ils manquent (avec, de nouveau, une seule nouvelle tentative automatique).
			 */
			recharger() {
				erreur = null;
				chargerActifs().catch(() => {});
			}
		}
	};
}

export type { Zone };

/** Ordre de la liste : publication la plus récente d'abord, ou fin d'enquête la plus proche. */
export type Tri = 'recent' | 'fin';

/** Réglages de la couche Permis, tels que les porte l'URL. */
export interface Parametres {
	/** Statuts affichés, parmi ceux proposés (en cours, ou tous avec l'historique). */
	statuts: Statut[];
	/** Nature des travaux ; vide : toutes. */
	nature: string;
	historique: boolean;
	/** Première année de l'historique affiché. */
	depuis: number;
	tri: Tri;
}

/** Publication (début d'enquête) la plus récente d'abord. */
const parPublication = (a: PointHisto, b: PointHisto) => (b.debut ?? '').localeCompare(a.debut ?? '') || b.id - a.id;

/**
 * Dossiers de la zone visible qui passent les filtres, dans l'ordre de la liste.
 * Fonction pure : `dossiers` est d'ordinaire le module de données lui-même.
 */
export function visibles(
	zone: Zone | null,
	parametres: Parametres,
	dossiers: { actifs: Dossier[]; histo: PointHisto[] }
): (Dossier | PointHisto)[] {
	if (!zone) return [];
	const [w, s, e, n] = zone;
	const { statuts, nature } = parametres;
	const garde = (d: PointHisto) =>
		d.lon >= w && d.lon <= e && d.lat >= s && d.lat <= n &&
		statuts.includes(d.statut) && (!nature || d.nature === nature);
	const liste: (Dossier | PointHisto)[] = dossiers.actifs.filter(garde);
	// Comme sur la carte : l'historique est filtré par année, pas les dossiers en cours.
	if (parametres.historique) {
		const idsActifs = new Set(dossiers.actifs.map((d) => d.id));
		for (const d of dossiers.histo)
			if (!idsActifs.has(d.id) && annee(d) >= parametres.depuis && garde(d)) liste.push(d);
	}
	return liste.sort(parametres.tri === 'fin' ? parFin : parPublication);
}

/** Enquêtes en cours d'abord, la plus proche de sa fin en tête ; ensuite par publication. */
const parFin = (a: PointHisto, b: PointHisto) =>
	Number(b.statut === 'enquete') - Number(a.statut === 'enquete') ||
	(a.statut === 'enquete' ? (a.fin ?? '').localeCompare(b.fin ?? '') : 0) ||
	parPublication(a, b);

const annee = (d: PointHisto) => Number(d.debut?.slice(0, 4) ?? 0);

/** Le module de données de la couche Permis, créé une seule fois et partagé par la carte et les pages. */
export const permis = creerDonneesPermis({ fetch: (entree, init) => fetch(entree, init) });
inscrireEtat('camac-permis', permis.source);
