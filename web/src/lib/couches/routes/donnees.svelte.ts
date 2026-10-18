import { ErreurApi } from '#lib/api.js';
import { inscrireEtat, type CauseEchec, type EtatSourceExecution } from '#lib/fraicheur.js';
import { getCommunes, getLimites } from '#lib/socle/communes.js';
import { creerClientDgmr, type CoucheDgmr, type EntiteDgmr } from './dgmr.js';
import { rattacher, type CommuneLimitee, type Passage } from './rattachement.js';
import { sorteDe, type Sorte } from './sortes.js';
import { lignesDe, longueur, milieu, type Point } from './trace.js';

/**
 * Module de données de la couche Routes, partagé par ses composants : les restrictions de circulation de la DGMR,
 * en cours (couche 596) et à venir (595), lues en direct depuis le navigateur pour tout le canton, sans emprise.
 * Chaque couche n'est demandée qu'une fois par visite, pour tous les usages. Les restrictions sont ensuite
 * rattachées à leurs communes par leur tracé, une fois chargées les limites des communes (voie Préparée).
 */

type Fetch = typeof fetch;

/** En cours si la restriction vient de la 596, à venir si elle vient de la 595 : le site ne le recalcule pas. */
export type EtatRestriction = 'en_cours' | 'a_venir';

const ETAT: Record<CoucheDgmr, EtatRestriction> = { 596: 'en_cours', 595: 'a_venir' };

/**
 * Une restriction de circulation, ses champs tels que la DGMR les écrit (textes vides ramenés à `null`).
 * Ni `ENTITE` ni `ARRDT` : codes internes, jamais lus.
 */
export interface Restriction {
	/** `OBJECTID`, la seule clé unique ; jamais affichée. */
	id: number;
	etat: EtatRestriction;
	sorte: Sorte;
	/** `RESTRICTION` telle que publiée (« Fermeture », ou une valeur inconnue comme « Manifestation ») ; « Autre » si vide. */
	libelleSorte: string;
	/** `NOM` : le nom des travaux, texte libre ; vide s'il manque. */
	nom: string;
	/** `RHRC` : « <n°>-<B/C/IL>-<P/S> » en principe, mais publié tel quel. */
	rhrc: string | null;
	/**
	 * `DATE_DEBUT` et `DATE_FIN` en millisecondes : l'heure locale codée comme de l'UTC. À lire par leurs
	 * composantes UTC (`getUTCHours`…), jamais par `getHours`. Une heure 00:00 veut dire « jour entier ».
	 */
	dateDebut: number;
	dateFin: number;
	/** `HEURE_DEBUT` et `HEURE_FIN` (« HH:MM ») : la plage quotidienne, quand les deux sont remplies. */
	heureDebut: string | null;
	heureFin: string | null;
	/** `WEEK_END` brut, en casse libre : « non » ou « Non » veut dire levée le week-end. */
	weekEnd: string | null;
	/** `TYPE` : le genre de travaux (« Infrastructure », « Revêtement », « Entretien »). */
	travaux: string | null;
	remarque: string | null;
	/** Le tracé, en lignes WGS84 (une seule pour une `LineString`). */
	lignes: Point[][];
	/** Longueur du tracé, en mètres. */
	longueur: number;
	/** Point à mi-longueur du tracé : sa position sur la carte et dans le fil. */
	milieu: Point;
	/**
	 * Les communes que parcourt le tracé, de la plus grande longueur à la plus petite (la première est celle de sa
	 * fiche et du fil) ; `null` tant que les limites des communes ne sont pas chargées.
	 */
	communes: Passage[] | null;
}

const texte = (v: unknown) => (v == null || String(v).trim() === '' ? null : String(v).trim());

function versRestriction({ properties: p, geometry }: EntiteDgmr, etat: EtatRestriction): Restriction | null {
	const lignes = geometry ? lignesDe(geometry).filter((l) => l.length > 0) : [];
	if (!lignes.length) return null;
	const publiee = texte(p.RESTRICTION);
	return {
		id: Number(p.OBJECTID),
		etat,
		sorte: sorteDe(publiee),
		libelleSorte: publiee ?? 'Autre',
		nom: texte(p.NOM) ?? '',
		rhrc: texte(p.RHRC),
		dateDebut: Number(p.DATE_DEBUT),
		dateFin: Number(p.DATE_FIN),
		heureDebut: texte(p.HEURE_DEBUT),
		heureFin: texte(p.HEURE_FIN),
		weekEnd: texte(p.WEEK_END),
		travaux: texte(p.TYPE),
		remarque: texte(p.REMARQUE),
		lignes,
		longueur: longueur(lignes),
		milieu: milieu(lignes),
		communes: null
	};
}

/** Les deux couches réunies par `OBJECTID` croissant ; une restriction présente dans les deux compte en cours. */
function reunir(enCours: Restriction[], aVenir: Restriction[]): Restriction[] {
	const ids = new Set(enCours.map((r) => r.id));
	return [...enCours, ...aVenir.filter((r) => !ids.has(r.id))].sort((a, b) => a.id - b.id);
}

export interface DonneesRoutes {
	/**
	 * Restrictions en cours et à venir déjà chargées, par `OBJECTID` croissant (vide tant que rien n'est chargé),
	 * avec leurs communes dès que les limites sont là.
	 */
	readonly restrictions: Restriction[];
	/** La couche de cet état (596 en cours, 595 à venir) a été lue : sans elle, rien n'est dit de ses restrictions. */
	chargee(etat: EtatRestriction): boolean;
	/** Les restrictions ont leurs communes : les limites des communes sont chargées. */
	readonly rattache: boolean;
	/**
	 * Charge les deux couches, chacune une seule fois par visite. Un échec d'une couche est retenté une fois au bout
	 * d'environ 5 s ; s'il persiste, la source passe en erreur et la promesse rejette, mais ce que l'autre couche a
	 * donné reste dans `restrictions`. Un nouvel appel ne redemande que la couche manquée.
	 */
	charger(): Promise<Restriction[]>;
	/**
	 * Charge les deux couches puis les limites des communes, et donne les restrictions rattachées. Rejette si la
	 * DGMR a échoué, ou si les limites n'ont pas pu être chargées (elles sont alors redemandées au prochain appel).
	 */
	rattachees(): Promise<Restriction[]>;
	/** État de la source DGMR : heure de la dernière consultation réussie, échec, nouvel essai. */
	readonly source: EtatSourceExecution;
}

/** Délai avant l'unique nouvelle tentative automatique d'un chargement raté. */
const RETENTE_MS = 5_000;

/** Hors ligne si le navigateur le dit (ou le client), sinon le service est tenu pour indisponible. */
const causeDe = (e: unknown): CauseEchec =>
	(e instanceof ErreurApi && e.hors_ligne) || globalThis.navigator?.onLine === false ? 'hors_ligne' : 'indisponible';

export interface Options {
	/** `fetch` du navigateur, pour la DGMR. */
	fetch: Fetch;
	/** Horloge : date la dernière consultation. */
	maintenant?: () => Date;
}

export function creerDonneesRoutes({ fetch: f, maintenant = () => new Date() }: Options): DonneesRoutes {
	/* ---- État de la source : chaque réponse de la DGMR date la consultation. ---- */

	let derniere = $state.raw<Date | null>(null);
	const dgmr = creerClientDgmr(async (entree, init) => {
		const r = await f(entree, init);
		if (r.ok) derniere = maintenant();
		return r;
	});
	let erreur = $state<CauseEchec | null>(null);

	/* ---- Une couche : une requête par visite, retentée une fois ; un échec est oublié. ---- */

	const lues: Record<CoucheDgmr, Restriction[]> = { 596: [], 595: [] };
	let chargees = $state.raw<Record<EtatRestriction, boolean>>({ en_cours: false, a_venir: false });
	/** Les deux couches réunies et rattachées, recalculées à chaque couche lue et à l'arrivée des limites. */
	let restrictions = $state.raw<Restriction[]>([]);
	const chargements = new Map<CoucheDgmr, Promise<void>>();

	function chargerCouche(couche: CoucheDgmr): Promise<void> {
		let p = chargements.get(couche);
		if (p) return p;
		const essai = () => dgmr.chercher(couche, '1=1');
		p = essai()
			.catch(async () => {
				await new Promise((ok) => setTimeout(ok, RETENTE_MS));
				return essai();
			})
			.then((es) => {
				const etat = ETAT[couche];
				const rs = es.flatMap((e) => versRestriction(e, etat) ?? []);
				lues[couche] = rs;
				chargees = { ...chargees, [etat]: true };
				publier();
			});
		chargements.set(couche, p);
		p.catch(() => chargements.delete(couche));
		return p;
	}

	/* ---- Rattachement : les limites des communes, chargées une fois après les restrictions. ---- */

	let communes = $state.raw<CommuneLimitee[] | null>(null);
	/** Les communes de chaque restriction lue, calculées une seule fois. */
	const rattachements = new WeakMap<Restriction, Passage[]>();

	function communesDe(r: Restriction, cs: CommuneLimitee[]): Passage[] {
		let p = rattachements.get(r);
		if (!p) rattachements.set(r, (p = rattacher({ type: 'MultiLineString', coordinates: r.lignes }, cs)));
		return p;
	}

	function publier() {
		const rs = reunir(lues[596], lues[595]);
		const cs = communes;
		restrictions = cs ? rs.map((r) => ({ ...r, communes: communesDe(r, cs) })) : rs;
	}

	let limites: Promise<void> | null = null;

	/** Les limites des communes, sans passer par la DGMR (elles ne datent pas sa consultation). */
	function chargerLimites(): Promise<void> {
		if (limites) return limites;
		const p = Promise.all([getCommunes(f), getLimites(f)]).then(([cs, ls]) => {
			communes = cs.map((commune) => ({ commune, limites: ls[commune.bfs] ?? [] }));
			publier();
		});
		limites = p;
		p.catch(() => (limites = null));
		return p;
	}

	/* ---- Les deux couches : une panne de l'une, même de la seule 595, met la source en erreur. ---- */

	let chargement: Promise<Restriction[]> | null = null;

	function charger(): Promise<Restriction[]> {
		if (chargement) return chargement;
		const p = Promise.allSettled([chargerCouche(596), chargerCouche(595)]).then((resultats) => {
			// Après le premier affichage des restrictions : les limites ne retardent ni la carte ni le fil.
			chargerLimites().catch(() => {});
			const echec = resultats.find((r) => r.status === 'rejected');
			if (echec) {
				erreur = causeDe(echec.reason);
				throw echec.reason;
			}
			erreur = null;
			return restrictions;
		});
		chargement = p;
		p.catch(() => (chargement = null));
		return p;
	}

	async function rattachees(): Promise<Restriction[]> {
		await charger();
		await chargerLimites();
		return restrictions;
	}

	return {
		get restrictions() {
			return restrictions;
		},
		chargee: (etat) => chargees[etat],
		get rattache() {
			return communes !== null;
		},
		charger,
		rattachees,
		source: {
			get derniere() {
				return derniere;
			},
			get erreur() {
				return erreur;
			},
			/** Lève l'erreur, ce qui fait recharger les composants qui l'affichaient, et redemande la couche manquée. */
			recharger() {
				erreur = null;
				charger().catch(() => {});
			}
		}
	};
}

/** Le module de données de la couche Routes, créé une seule fois et partagé par la carte et les pages. */
export const routes = creerDonneesRoutes({ fetch: (entree, init) => fetch(entree, init) });
inscrireEtat('dgmr-restrictions', routes.source);
