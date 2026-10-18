import { ErreurApi } from '#lib/api.js';
import { inscrireEtat, type CauseEchec, type EtatSourceExecution } from '#lib/fraicheur.js';
import { getCommunes, getLimites } from '#lib/socle/communes.js';
import { creerClientDgmr, type CoucheDgmr, type EntiteDgmr } from './dgmr.js';
import { instant } from './horaires.js';
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
	/**
	 * Une restriction et ses communes, par son `OBJECTID` : celle déjà chargée sans nouvelle requête à la DGMR,
	 * sinon demandée aux deux couches par `OBJECTID IN (…)`, sans tout charger. `null` si la DGMR ne la publie ni
	 * en cours ni à venir ; rejette si la DGMR n'a pas pu être interrogée (la source passe alors en erreur) ou les
	 * limites des communes chargées.
	 */
	restriction(id: number): Promise<Restriction | null>;
	/**
	 * Pour le fil : les restrictions rattachées qui commencent le jour `jour` (AAAA-MM-JJ) ou après, à venir
	 * comprises, par `OBJECTID` croissant. La 596 n'est demandée que pour `DATE_DEBUT >= jour`, la 595 en entier ;
	 * une couche déjà chargée en entier sert sans nouvelle requête. Rejette si l'une des deux couches échoue (la
	 * source passe alors en erreur), ou si les limites des communes n'ont pas pu être chargées.
	 */
	depuis(jour: string): Promise<Restriction[]>;
	/**
	 * État de la source DGMR : heure de la dernière consultation réussie, échec, nouvel essai. Toute lecture de la DGMR
	 * le met à jour, celle de la carte comme celles du fil et d'un lien vers une restriction.
	 */
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

	/**
	 * Une lecture de la DGMR, quel que soit l'usage (carte, fil, lien vers une restriction) : son échec met la source
	 * en erreur ou hors ligne, sa réussite la rétablit. Les limites des communes n'en sont pas : elles ne viennent
	 * pas de la DGMR.
	 */
	function suivie<T>(p: Promise<T>): Promise<T> {
		return p.then(
			(r) => {
				erreur = null;
				return r;
			},
			(e) => {
				erreur = causeDe(e);
				throw e;
			}
		);
	}

	/* ---- Une couche : une requête par visite, retentée une fois ; un échec est oublié. ---- */

	const lues: Record<CoucheDgmr, Restriction[]> = { 596: [], 595: [] };
	let chargees = $state.raw<Record<EtatRestriction, boolean>>({ en_cours: false, a_venir: false });
	/** Les deux couches réunies et rattachées, recalculées à chaque couche lue et à l'arrivée des limites. */
	let restrictions = $state.raw<Restriction[]>([]);
	const chargements = new Map<CoucheDgmr, Promise<void>>();

	/** Une demande à la DGMR, retentée une fois au bout de quelques secondes. */
	const avecRetente = (couche: CoucheDgmr, where: string) =>
		dgmr.chercher(couche, where).catch(async () => {
			await new Promise((ok) => setTimeout(ok, RETENTE_MS));
			return dgmr.chercher(couche, where);
		});

	function chargerCouche(couche: CoucheDgmr): Promise<void> {
		let p = chargements.get(couche);
		if (p) return p;
		p = avecRetente(couche, '1=1')
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
		const p = suivie(
			Promise.allSettled([chargerCouche(596), chargerCouche(595)]).then((resultats) => {
				// Après le premier affichage des restrictions : les limites ne retardent ni la carte ni le fil.
				chargerLimites().catch(() => {});
				const echec = resultats.find((r) => r.status === 'rejected');
				if (echec) throw echec.reason;
				return restrictions;
			})
		);
		chargement = p;
		p.catch(() => (chargement = null));
		return p;
	}

	async function rattachees(): Promise<Restriction[]> {
		await charger();
		await chargerLimites();
		return restrictions;
	}

	/* ---- Une restriction : celle déjà chargée, sinon demandée par son OBJECTID aux deux couches. ---- */

	/** Restrictions trouvées par leur `OBJECTID` hors du chargement complet (lien partagé), gardées pour la visite. */
	const parId = new Map<number, Restriction | null>();

	async function demander(id: number): Promise<Restriction | null> {
		const where = `OBJECTID IN (${id})`;
		const [enCours, aVenir] = await Promise.all([dgmr.chercher(596, where), dgmr.chercher(595, where)]);
		const [r] = reunir(
			enCours.flatMap((e) => versRestriction(e, ETAT[596]) ?? []),
			aVenir.flatMap((e) => versRestriction(e, ETAT[595]) ?? [])
		);
		return r ?? null;
	}

	async function restriction(id: number): Promise<Restriction | null> {
		const chargee = restrictions.find((r) => r.id === id);
		const r = chargee ?? (parId.has(id) ? parId.get(id)! : await suivie(demander(id)));
		if (!chargee) parId.set(id, r);
		if (!r) return null;
		await chargerLimites();
		// Les limites arrivées entre-temps ont rattaché les restrictions chargées.
		return restrictions.find((x) => x.id === id) ?? { ...r, communes: communesDe(r, communes!) };
	}

	/* ---- Le fil : ce qui a commencé depuis son premier jour, et tout l'à venir. ---- */

	/** La 596 réduite au fil, par premier jour, gardée pour la visite ; un échec est oublié. */
	const reduites = new Map<string, Promise<Restriction[]>>();

	function enCoursDepuis(jour: string): Promise<Restriction[]> {
		// La carte l'a déjà demandée en entier (ou est en train de le faire) : le fil s'en sert.
		if (chargements.has(596)) return chargerCouche(596).then(() => lues[596]);
		let p = reduites.get(jour);
		if (p) return p;
		p = avecRetente(596, `DATE_DEBUT >= DATE '${jour}'`).then((es) =>
			es.flatMap((e) => versRestriction(e, ETAT[596]) ?? [])
		);
		reduites.set(jour, p);
		p.catch(() => reduites.delete(jour));
		return p;
	}

	async function depuis(jour: string): Promise<Restriction[]> {
		const [enCours] = await suivie(Promise.all([enCoursDepuis(jour), chargerCouche(595)]));
		// Comme pour la carte : les limites ne retardent pas la lecture de la DGMR.
		await chargerLimites();
		const cs = communes!;
		// La date telle qu'écrite par la DGMR, sans conversion de fuseau.
		return reunir(enCours, lues[595])
			.filter((r) => instant(r.dateDebut).jour >= jour)
			.map((r) => ({ ...r, communes: communesDe(r, cs) }));
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
		restriction,
		depuis,
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
