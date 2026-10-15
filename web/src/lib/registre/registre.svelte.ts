import { createContext, untrack } from 'svelte';
import { SvelteSet } from 'svelte/reactivity';
import { afterNavigate, goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';
import type { Map as MlMap } from 'maplibre-gl';
import type { Commune, Centre, Zone } from '#lib/types.js';
import type { Chargeur, Cible, Contexte, CoucheInscrite, Lecteur, Ouvert } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';
import { corrigerChemin, fermeture, memeElement, mouvement, type Adresse } from './navigation.js';
import { titreFiche } from './tete.js';
import { ancre, calquesAuDessus } from './recouvrement.js';

/** Ce que le registre demande à la carte du socle quand l'adresse change sous lui. */
export interface VueCarte {
	aller(c: Centre, anime?: boolean): void;
	/** Vol souple vers un point, au moins à ce zoom. */
	voler(lon: number, lat: number, zoom?: number): void;
	vueCanton(): void;
	/** Cadre une emprise ; `parDefaut` : la vue obtenue n'entre pas dans l'adresse. */
	cadrer(emprise: [number, number, number, number], anime?: boolean, parDefaut?: boolean): void;
}

/** Route de la fiche commune : la commune ouverte est dans le chemin (ADR 0012). */
const ROUTE_COMMUNE = '/(carte)/commune/[slug]' as const;

/** Zoom auquel un élément ouvert est montré. */
const ZOOM_ELEMENT = 16;

type NomComposant = keyof CoucheInscrite['composants'];

/**
 * Le registre des couches à l'exécution : commune ouverte, couches activées, paramètres des couches, vue,
 * élément ouvert et volet ouvert. Il est le seul maître de l'adresse : `brancherAdresse` synchronise son état
 * avec la requête (`replace` pour la vue et les réglages, `push` pour l'ouverture d'un élément ou d'une fiche).
 * `communes` donne l'index des communes, connu dès le rendu de la page pré-générée.
 */
export function creerRegistre(couches: readonly CoucheInscrite[], communes: () => readonly Commune[]) {
	const depart = lireUrl(couches, new URLSearchParams());

	let actives = $state<string[]>(depart.actives);
	let parametres = $state.raw<Record<string, unknown>>(depart.parametres);
	let vue = $state<Centre | null>(null);
	/** Dernier centre de la carte, même quand c'est une vue par défaut (canton, commune cadrée). */
	let centre: Centre | null = null;
	let zone = $state.raw<Zone | null>(null);
	let ouvert = $state<Ouvert | null>(null);
	let map = $state.raw<MlMap | null>(null);
	/** Volet ouvert sur la carte (bureau) ; n'entre pas dans l'adresse. */
	let volet = $state<string | null>(null);
	/** Message près de la recherche : élément introuvable (« Aucun dossier n° … ») ou impossible à localiser. */
	let avis = $state<string | null>(null);
	/** Couches activées au moins une fois : leur `Carte` reste montée, pour le fondu à la désactivation. */
	const montees = new SvelteSet<string>(depart.actives);

	/** Slug de la commune dont la fiche est ouverte, lu dans le chemin. */
	const slug = $derived(page.route.id === ROUTE_COMMUNE ? (page.params.slug ?? null) : null);
	const commune = $derived(slug === null ? null : (communes().find((c) => c.slug === slug) ?? null));

	const etat = (): EtatUrl => ({ actives, vue, ouvert, parametres });
	const requete = $derived(ecrireUrl(couches, etat()));
	/** Titre du document quand une fiche est ouverte ; il suit l'élément ouvert. */
	const titre = $derived(commune ? titreFiche(commune, ouvert, couches) : null);

	function appliquer(e: EtatUrl) {
		actives = e.actives;
		for (const id of e.actives) montees.add(id);
		parametres = e.parametres;
		ouvert = e.ouvert;
	}

	/* ---- Composants, importés une seule fois chacun, à la demande ---- */

	const charges = new Map<string, ReturnType<Chargeur<unknown>>>();
	/** L'`Apercu` reçoit aussi `voir` : celui qui le rend lui donne ce type. */
	function composant(c: CoucheInscrite, nom: NomComposant) {
		const chargeur = c.composants[nom] as Chargeur<unknown> | undefined;
		if (!chargeur) return null;
		const cle = `${c.id}:${nom}`;
		let p = charges.get(cle);
		if (!p) {
			p = chargeur();
			p.catch(() => charges.delete(cle));
			charges.set(cle, p);
		}
		return p;
	}

	/* ---- Actions ---- */

	/** La prochaine écriture de l'adresse crée une entrée d'historique au lieu de remplacer la courante. */
	let nouvelleEntree = false;

	function activer(id: string, oui: boolean) {
		const c = couches.find((c) => c.id === id);
		if (!c || c.permanente) return;
		if (oui) montees.add(id);
		const suivantes = new Set(actives);
		if (oui) suivantes.add(id);
		else suivantes.delete(id);
		actives = couches.filter((c) => suivantes.has(c.id)).map((c) => c.id);
	}

	function regler(id: string, partiel: object) {
		parametres = { ...parametres, [id]: { ...(parametres[id] as object), ...partiel } };
	}

	/** Carte du socle, branchée par `brancherAdresse`. */
	let carteSocle: () => VueCarte | undefined = () => undefined;

	function cadrerCommune(s: string, anime: boolean) {
		const c = communes().find((c) => c.slug === s);
		// Cadrée sur sa partie terrestre (`cadre`), pas sur son emprise lac compris.
		if (c) carteSocle()?.cadrer(c.cadre, anime, true);
	}

	/**
	 * Ouvrir une fiche commune crée une entrée d'historique. La nouvelle adresse garde les couches et les
	 * réglages, mais ni la vue (la carte va cadrer la commune) ni l'élément ouvert.
	 */
	function ouvrirCommune(s: string) {
		if (s === slug) return cadrerCommune(s, true);
		const q = ecrireUrl(couches, { ...etat(), vue: null, ouvert: null });
		goto(`${resolve(ROUTE_COMMUNE, { slug: s })}${q}`, { reset: false });
	}

	/** Fermer la fiche ramène à « / », sans bouger la carte. */
	function fermerCommune() {
		if (slug === null) return;
		const q = ecrireUrl(couches, { ...etat(), vue: vue ?? centre, ouvert: null });
		goto(`${resolve('/(carte)')}${q}`, { reset: false });
	}

	/* ---- Élément ouvert : toujours dans la fiche de sa commune ---- */

	/** Ce que reflète l'adresse courante : commune du chemin et élément de la requête. */
	let suivi: Pick<Adresse, 'commune' | 'ouvert'> = { commune: null, ouvert: null };
	/** Dernier élément demandé : une demande plus ancienne qui aboutit après lui est ignorée. */
	let demande: Ouvert | null = null;

	type Lieu = { commune: string; position: [number, number] } | null;

	/** Commune et position de l'élément selon sa couche ; `echec` si la couche n'a pas pu le chercher. */
	async function localiser(o: Ouvert): Promise<Lieu | 'echec'> {
		const c = couches.find((c) => c.id === o.couche);
		if (!c?.localiser) return null;
		try {
			return await c.localiser(o.element);
		} catch {
			return 'echec';
		}
	}

	const messageIntrouvable = (o: Ouvert) =>
		couches.find((c) => c.id === o.couche)?.introuvable?.(o.element) ?? `Aucun élément n° ${o.element}.`;
	const messageNonCherche = (o: Ouvert) =>
		`Le n° ${o.element} n’a pas pu être cherché : vérifiez votre connexion, puis réessayez.`;

	/**
	 * Ouvre un élément dans la fiche de sa commune, trouvée par `localiser`. Ouvrir un élément quand aucun n'est
	 * ouvert, ou celui d'une autre commune, crée une entrée d'historique : le retour du navigateur ramène à la
	 * fiche précédente. Passer d'un élément à un autre dans la même commune remplace l'entrée.
	 */
	async function ouvrirElement(cible: Ouvert & { position?: [number, number] }) {
		const o: Ouvert = { couche: cible.couche, element: cible.element };
		avis = null;
		if (cible.position) carteSocle()?.voler(cible.position[0], cible.position[1], ZOOM_ELEMENT);
		if (memeElement(ouvert, o)) return;
		demande = o;
		const lieu = await localiser(o);
		if (demande !== o) return;
		demande = null;
		if (lieu === 'echec') return void (avis = messageNonCherche(o));
		const k = corrigerChemin(slug, lieu);
		if (k === 'retirer') return void (avis = messageIntrouvable(o));
		if (!cible.position) carteSocle()?.voler(lieu!.position[0], lieu!.position[1], ZOOM_ELEMENT);
		if (k === null) {
			// Même commune : l'adresse suit l'état (entrée poussée si rien n'était ouvert).
			nouvelleEntree = ouvert === null;
			ouvert = o;
			return;
		}
		// Autre commune : une nouvelle entrée, sans la vue (la carte vole vers l'élément). L'état suivra l'adresse,
		// et la carte ne bougera pas une seconde fois.
		const depuis = slug;
		suivi = { commune: k.commune, ouvert: o };
		const q = ecrireUrl(couches, { ...etat(), vue: null, ouvert: o });
		goto(`${resolve(ROUTE_COMMUNE, { slug: k.commune })}${q}`, {
			reset: false,
			state: { element: { depuis } }
		});
	}

	/**
	 * L'adresse porte un élément qu'on n'a pas ouvert soi-même (lien partagé, précédent ou suivant du navigateur) :
	 * on corrige son chemin vers la commune de l'élément, ou on retire l'élément introuvable. `montrer` : la carte
	 * va vers lui, d'un saut à l'arrivée sur le site.
	 */
	async function corriger(o: Ouvert, montrer: boolean, initial: boolean) {
		demande = o;
		const lieu = await localiser(o);
		if (demande !== o || !memeElement(ouvert, o)) return;
		demande = null;
		if (lieu === 'echec') return void (avis = messageNonCherche(o));
		const k = corrigerChemin(slug, lieu);
		if (k === 'retirer') {
			avis = messageIntrouvable(o);
			ouvert = null;
			return;
		}
		const [lon, lat] = lieu!.position;
		if (montrer && initial) carteSocle()?.aller({ lon, lat, zoom: ZOOM_ELEMENT }, false);
		else if (montrer) carteSocle()?.voler(lon, lat, ZOOM_ELEMENT);
		if (k === null) return;
		suivi = { commune: k.commune, ouvert: o };
		goto(`${resolve(ROUTE_COMMUNE, { slug: k.commune })}${ecrireUrl(couches, etat())}`, {
			replace: true,
			reset: false,
			state: page.state
		});
	}

	function ouvrir(cible: Cible) {
		if ('commune' in cible) return ouvrirCommune(cible.commune);
		ouvrirElement(cible);
	}

	/**
	 * Fermer l'élément ramène à l'onglet de sa couche, sans bouger la carte : retour en arrière si l'application a
	 * poussé l'entrée depuis la même commune, sinon l'adresse est remplacée par le chemin de la commune.
	 */
	function fermer() {
		if (!ouvert) return;
		if (fermeture(page.state, slug) === 'retour') history.back();
		else ouvert = null;
	}

	/** Contexte passé aux composants d'une couche ; ses valeurs suivent l'état du registre. */
	function contexte(c: CoucheInscrite): Contexte {
		return {
			get map() {
				if (!map) throw new Error('Carte pas encore prête');
				return map;
			},
			avant: ancre(c.id),
			get zone() {
				return zone;
			},
			get parametres() {
				return parametres[c.id];
			},
			regler: (partiel) => regler(c.id, partiel as object),
			get active() {
				return actives.includes(c.id);
			},
			get ouvert() {
				return ouvert;
			},
			get commune() {
				return commune;
			},
			recouvert(point) {
				if (!map) return false;
				const calques = calquesAuDessus(map.getStyle().layers.map((l) => l.id), ancre(c.id));
				return calques.length > 0 && map.queryRenderedFeatures(point, { layers: calques }).length > 0;
			},
			ouvrir,
			fermer
		};
	}

	/* ---- Carte du socle ---- */

	/** La carte est prête : un calque vide par couche, dans l'ordre du registre, sous le repère du socle. */
	function carte(m: MlMap, sous: string) {
		for (const c of couches)
			m.addLayer({ id: ancre(c.id), type: 'background', layout: { visibility: 'none' } }, sous);
		map = m;
	}

	/** Fin d'un déplacement de la carte ; la vue du canton par défaut n'entre pas dans l'adresse. */
	function deplacement(z: Zone, c: Centre, parDefaut: boolean) {
		zone = z;
		centre = c;
		vue = parDefaut ? null : c;
	}

	/* ---- Adresse ---- */

	/**
	 * Synchronise l'état et l'adresse, dans les deux sens. À appeler pendant l'initialisation de la coquille.
	 * Les pages sont pré-générées sans paramètres : l'adresse de départ est lue après le premier rendu.
	 */
	function brancherAdresse(carte: () => VueCarte | undefined) {
		carteSocle = carte;
		/** Chemin et requête déjà reflétés par l'état ; `null` tant que l'adresse de départ n'a pas été lue. */
		let synchro: string | null = null;
		/**
		 * L'adresse a changé sous le registre : l'état la suit, et la carte bouge s'il le faut. Un élément qu'on
		 * n'a pas ouvert soi-même est localisé, pour corriger son chemin et, s'il le faut, le montrer.
		 */
		function suivre(params: Lecteur, initial: boolean) {
			const e = lireUrl(couches, params);
			const m = mouvement(suivi, { commune: slug, vue: e.vue, ouvert: e.ouvert }, initial);
			const nouveau = e.ouvert !== null && !memeElement(suivi.ouvert, e.ouvert);
			suivi = { commune: slug, ouvert: e.ouvert };
			appliquer(e);
			// Une carte qui ne bouge pas garde sa vue : l'adresse sera réécrite avec elle.
			if (m !== null || initial) vue = e.vue;
			if (m === 'canton') carteSocle()?.vueCanton();
			else if (m && typeof m === 'object' && 'aller' in m) carteSocle()?.aller(m.aller, !initial);
			else if (m && typeof m === 'object') cadrerCommune(m.cadrer, !initial);
			if (nouveau) corriger(e.ouvert!, m === 'element', initial);
		}

		afterNavigate(() => {
			if (synchro !== null) return;
			synchro = location.pathname + location.search;
			suivre(new URLSearchParams(location.search), true);
		});

		// État → adresse. Les déplacements et les réglages remplacent l'entrée courante.
		$effect(() => {
			const q = requete;
			untrack(() => {
				const push = nouvelleEntree;
				nouvelleEntree = false;
				if (synchro === null || q === location.search) return;
				synchro = location.pathname + q;
				suivi = { commune: slug, ouvert };
				goto(`${location.pathname}${q}`, {
					shallow: true,
					replace: !push,
					state: push ? { element: { depuis: slug } } : page.state
				});
			});
		});

		// Adresse → état : fiche ouverte ou fermée, précédent et suivant du navigateur, logo et lien « Carte ».
		$effect(() => {
			const url = page.shallow?.url ?? page.url;
			const cle = url.pathname + url.search;
			untrack(() => {
				if (synchro === null || cle === synchro) return;
				synchro = cle;
				suivre(url.searchParams, false);
			});
		});
	}

	return {
		couches,
		get actives() {
			return actives;
		},
		get zone() {
			return zone;
		},
		get map() {
			return map;
		},
		get ouvert() {
			return ouvert;
		},
		/** Commune dont la fiche est ouverte. */
		get commune() {
			return commune;
		},
		/** Titre du document quand une fiche est ouverte (`null` sinon). */
		get titre() {
			return titre;
		},
		/** Message près de la recherche (« Aucun dossier n° … »), jusqu'à la prochaine ouverture. */
		get avis() {
			return avis;
		},
		oublierAvis: () => (avis = null),
		get volet() {
			return volet;
		},
		set volet(id: string | null) {
			volet = id;
		},
		/** La `Carte` de cette couche doit être montée (activée, ou désactivée après l'avoir été). */
		montee: (id: string) => montees.has(id),
		active: (id: string) => actives.includes(id),
		activer,
		ouvrir,
		fermer,
		fermerCommune,
		composant,
		contexte,
		carte,
		deplacement,
		brancherAdresse
	};
}

export type Registre = ReturnType<typeof creerRegistre>;

/** Le registre de la coquille, pour les pages du groupe de la carte (titre de la fiche ouverte). */
export const [registreCourant, fournirRegistre] = createContext<Registre>();
