import { createContext, untrack } from 'svelte';
import { SvelteSet } from 'svelte/reactivity';
import { afterNavigate, goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';
import type { Map as MlMap } from 'maplibre-gl';
import type { Commune, Centre, Emprise, Zone } from '#lib/types.js';
import type { Chargeur, Cible, Contexte, CoucheInscrite, Fiche, Lecteur, Lieu, Ouvert } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';
import {
	corrigerChemin,
	creerNavigations,
	fermeture,
	memeElement,
	memeFiche,
	mouvement,
	type Adresse
} from './navigation.js';
import { ficheDuChemin, fichePropre } from './fiches.js';
import { cheminFiche } from './liens.js';
import { titreFiche } from './tete.js';
import { avisIntrouvable, avisNonCherche } from './avis.js';
import { ancre, calquesAuDessus } from './recouvrement.js';
import { zoneDuFil } from '#lib/fil/fil.js';

/** Volet du fil cantonal, à la place de celui d'une couche. */
export const FIL = 'fil';

/** Ce que le registre demande à la carte du socle quand l'adresse change sous lui. */
export interface VueCarte {
	aller(c: Centre, anime?: boolean): void;
	/** Vol souple vers un point, au moins à ce zoom ; `parDefaut` : la vue obtenue n'entre pas dans l'adresse. */
	voler(lon: number, lat: number, zoom?: number, parDefaut?: boolean): void;
	vueCanton(): void;
	/** Cadre une emprise ; `parDefaut` : la vue obtenue n'entre pas dans l'adresse. */
	cadrer(emprise: Emprise, anime?: boolean, parDefaut?: boolean): void;
}

/** Route de la fiche commune : la commune ouverte est dans le chemin (ADR 0012). */
const ROUTE_COMMUNE = '/(carte)/commune/[slug]' as const;
/** Route d'une fiche propre : son chemin, d'un seul segment, est celui que déclare sa couche (`/grand-conseil`). */
const ROUTE_FICHE = '/(carte)/[fiche]' as const;

/** Zoom auquel un élément ouvert est montré. */
const ZOOM_ELEMENT = 16;

type NomComposant = keyof CoucheInscrite['composants'];

/**
 * Le registre des couches à l'exécution : fiche ouverte (commune ou fiche propre), couches activées, paramètres des couches, vue,
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
	/** Zone du fil : celle du dernier déplacement fait par la personne (`zoneDuFil`). */
	let zoneFil = $state.raw<Zone | null>(null);
	/**
	 * Volet ouvert sur la carte (bureau) : l'id d'une couche, ou `'fil'` pour le fil cantonal, ouvert à l'arrivée.
	 * Un seul à la fois ; n'entre pas dans l'adresse.
	 */
	let volet = $state<string | null>(FIL);
	/**
	 * Onglet choisi dans la fiche commune (l'id de sa couche) ; `null` : le premier. Il reste quand on change de
	 * commune, et n'entre pas dans l'adresse.
	 */
	let onglet = $state<string | null>(null);
	/** Message près de la recherche : élément introuvable (« Aucun dossier n° … ») ou impossible à localiser. */
	let avis = $state<string | null>(null);
	/** Couches activées au moins une fois : leur `Carte` reste montée, pour le fondu à la désactivation. */
	const montees = new SvelteSet<string>(depart.actives);

	/** Slug de la commune dont la fiche est ouverte, lu dans le chemin. */
	const slug = $derived(page.route.id === ROUTE_COMMUNE ? (page.params.slug ?? null) : null);
	/** Fiche propre ouverte, et la couche qui la déclare, lue dans le chemin. */
	const propre = $derived(
		page.route.id === ROUTE_FICHE && page.params.fiche ? ficheDuChemin(couches, `/${page.params.fiche}`) : null
	);
	/** Fiche ouverte, lue dans le chemin : celle d'une commune ou une fiche propre, jamais les deux. */
	const fiche = $derived<Fiche | null>(
		slug !== null ? { commune: slug } : propre ? { fiche: propre.fiche.id } : null
	);
	const commune = $derived(slug === null ? null : (communes().find((c) => c.slug === slug) ?? null));

	const etat = (): EtatUrl => ({ actives, vue, ouvert, parametres });
	const requete = $derived(ecrireUrl(couches, etat()));
	/** Titre du document quand une fiche est ouverte ; il suit l'élément ouvert. */
	const nomFiche = $derived(commune?.nom ?? propre?.fiche.nom ?? null);
	const titre = $derived(nomFiche === null ? null : titreFiche(nomFiche, ouvert, couches));

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

	/**
	 * La carte montre une fiche : la commune entière, cadrée sur sa partie terrestre (`cadre`) et non sur son
	 * emprise lac compris, ou la position d'une fiche propre, au zoom d'un élément. Ces vues n'entrent pas dans
	 * l'adresse.
	 */
	function cadrerFiche(f: Fiche, anime: boolean) {
		if ('commune' in f) {
			const c = communes().find((c) => c.slug === f.commune);
			if (c) carteSocle()?.cadrer(c.cadre, anime, true);
			return;
		}
		const position = fichePropre(couches, f.fiche)?.fiche.position;
		if (position) carteSocle()?.voler(position[0], position[1], ZOOM_ELEMENT, true);
	}

	/** Change de page ; tant que la navigation n'a pas abouti, l'état n'écrit pas l'adresse (`creerNavigations`). */
	const navigations = creerNavigations(goto);
	const naviguer = (url: string, options: Parameters<typeof goto>[1]) => void navigations.naviguer(url, options);

	/**
	 * Ouvrir une fiche, commune ou propre, crée une entrée d'historique. La nouvelle adresse garde les couches et
	 * les réglages, mais ni la vue (la carte va cadrer la fiche) ni l'élément ouvert.
	 */
	function ouvrirFiche(f: Fiche) {
		if (memeFiche(f, fiche)) return cadrerFiche(f, true);
		const q = ecrireUrl(couches, { ...etat(), vue: null, ouvert: null });
		naviguer(`${cheminFiche(couches, f)}${q}`, { reset: false });
	}

	/** Fermer la fiche, commune ou propre, ramène à « / », sans bouger la carte. */
	function fermerFiche() {
		if (fiche === null) return;
		const q = ecrireUrl(couches, { ...etat(), vue: vue ?? centre, ouvert: null });
		naviguer(`${resolve('/(carte)')}${q}`, { reset: false });
	}

	/* ---- Élément ouvert : toujours dans l'une de ses fiches ---- */

	/** Ce que reflète l'adresse courante : fiche du chemin et élément de la requête. */
	let suivi: Pick<Adresse, 'fiche' | 'ouvert'> = { fiche: null, ouvert: null };
	/** Dernier élément demandé : une demande plus ancienne qui aboutit après lui est ignorée. */
	let demande: Ouvert | null = null;

	/**
	 * Montre l'élément ouvert dans la fiche `dans` : la carte va vers sa position (d'un saut si `saut`), ou cadre
	 * la fiche quand l'élément n'en a pas.
	 */
	function montrerElement(lieu: Lieu, dans: Fiche, saut: boolean) {
		if (lieu.position) {
			const [lon, lat] = lieu.position;
			if (saut) carteSocle()?.aller({ lon, lat, zoom: ZOOM_ELEMENT }, false);
			else carteSocle()?.voler(lon, lat, ZOOM_ELEMENT);
		} else cadrerFiche(dans, !saut);
	}

	/** Fiches et position de l'élément selon sa couche ; `echec` si la couche n'a pas pu le chercher. */
	async function localiser(o: Ouvert): Promise<Lieu | null | 'echec'> {
		const c = couches.find((c) => c.id === o.couche);
		if (!c?.localiser) return null;
		try {
			return await c.localiser(o.element);
		} catch {
			return 'echec';
		}
	}

	/**
	 * L'élément est introuvable : le message près de la recherche, et la fiche commune du chemin passe sur l'onglet
	 * de sa couche (`avisIntrouvable`).
	 */
	function introuvable(o: Ouvert) {
		const a = avisIntrouvable(couches, o, fiche);
		avis = a.avis;
		if (a.onglet) onglet = a.onglet;
	}

	/**
	 * Ouvre un élément dans l'une de ses fiches, trouvées par `localiser` : celle du chemin si elle en fait partie,
	 * sinon la première (`corrigerChemin`). Ouvrir un élément quand aucun n'est ouvert, ou dans une autre fiche, crée
	 * une entrée d'historique : le retour du navigateur ramène à la fiche précédente. Passer d'un élément à un autre
	 * dans la même fiche remplace l'entrée.
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
		if (lieu === 'echec') return void (avis = avisNonCherche(couches, o));
		const k = corrigerChemin(fiche, lieu);
		if (k === 'retirer') return introuvable(o);
		if (!cible.position) montrerElement(lieu!, k ?? fiche!, false);
		if (k === null) {
			// Même fiche : l'adresse suit l'état (entrée poussée si rien n'était ouvert).
			nouvelleEntree = ouvert === null;
			ouvert = o;
			return;
		}
		// Autre fiche : une nouvelle entrée, sans la vue (la carte vole vers l'élément). L'état suivra l'adresse,
		// et la carte ne bougera pas une seconde fois.
		const depuis = fiche;
		const chemin = cheminFiche(couches, k);
		suivi = { fiche: k, ouvert: o };
		const q = ecrireUrl(couches, { ...etat(), vue: null, ouvert: o });
		naviguer(`${chemin}${q}`, {
			reset: false,
			state: { element: { depuis } }
		});
	}

	/**
	 * L'adresse porte un élément qu'on n'a pas ouvert soi-même (lien partagé, précédent ou suivant du navigateur) :
	 * on corrige son chemin vers l'une de ses fiches, ou on retire l'élément introuvable, et la fiche du chemin
	 * s'ouvre sur l'onglet de sa couche. `montrer` : la carte va
	 * vers lui, d'un saut à l'arrivée sur le site.
	 */
	async function corriger(o: Ouvert, montrer: boolean, initial: boolean) {
		demande = o;
		const lieu = await localiser(o);
		if (demande !== o || !memeElement(ouvert, o)) return;
		demande = null;
		if (lieu === 'echec') return void (avis = avisNonCherche(couches, o));
		const k = corrigerChemin(fiche, lieu);
		if (k === 'retirer') {
			introuvable(o);
			ouvert = null;
			return;
		}
		if (montrer) montrerElement(lieu!, k ?? fiche!, initial);
		if (k === null) return;
		const chemin = cheminFiche(couches, k);
		suivi = { fiche: k, ouvert: o };
		naviguer(`${chemin}${ecrireUrl(couches, etat())}`, {
			replace: true,
			reset: false,
			state: page.state
		});
	}

	function ouvrir(cible: Cible) {
		if ('commune' in cible) {
			if (cible.onglet) onglet = cible.onglet;
			return ouvrirFiche({ commune: cible.commune });
		}
		if ('fiche' in cible) return ouvrirFiche({ fiche: cible.fiche });
		ouvrirElement(cible);
	}

	/**
	 * Fermer l'élément ramène à l'onglet de sa couche, sans bouger la carte : retour en arrière si l'application a
	 * poussé l'entrée depuis la même fiche, sinon l'adresse est remplacée par le chemin de la fiche.
	 */
	function fermer() {
		if (!ouvert) return;
		if (fermeture(page.state, fiche) === 'retour') history.back();
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
			get fiche() {
				return propre?.fiche ?? null;
			},
			get communes() {
				return communes();
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

	/** Jusqu'à cet instant (ms), les déplacements comptent comme faits par la personne : elle a cherché un lieu. */
	let vouluJusqua = 0;
	/** Délai laissé à la carte pour aller vers le lieu cherché (ouverture de la fiche, puis cadrage). */
	const DELAI_VOULU = 3_000;

	/**
	 * La personne a choisi un lieu dans la recherche (commune, adresse) : les déplacements qui suivent, même lancés
	 * par le registre ou le socle, sont les siens, et déplacent la zone du fil.
	 */
	function deplacementVoulu() {
		vouluJusqua = Date.now() + DELAI_VOULU;
	}

	/**
	 * Fin d'un déplacement de la carte ; la vue du canton par défaut n'entre pas dans l'adresse. `parLaPersonne` :
	 * elle a glissé ou zoomé ; la zone du fil ne suit que ses déplacements.
	 */
	function deplacement(z: Zone, c: Centre, parDefaut: boolean, parLaPersonne = false) {
		// Tous les déplacements de ce délai comptent : la colonne de la fiche s'ouvre, puis la commune est cadrée.
		const voulu = Date.now() < vouluJusqua;
		zone = z;
		zoneFil = zoneDuFil(zoneFil, z, parLaPersonne || voulu);
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
			const m = mouvement(suivi, { fiche, vue: e.vue, ouvert: e.ouvert }, initial);
			const nouveau = e.ouvert !== null && !memeElement(suivi.ouvert, e.ouvert);
			suivi = { fiche, ouvert: e.ouvert };
			appliquer(e);
			// Une carte qui ne bouge pas garde sa vue : l'adresse sera réécrite avec elle.
			if (m !== null || initial) vue = e.vue;
			if (m === 'canton') carteSocle()?.vueCanton();
			else if (m && typeof m === 'object' && 'aller' in m) carteSocle()?.aller(m.aller, !initial);
			else if (m && typeof m === 'object') cadrerFiche(m.cadrer, !initial);
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
				if (synchro === null || navigations.enCours || q === location.search) return;
				synchro = location.pathname + q;
				suivi = { fiche, ouvert };
				goto(`${location.pathname}${q}`, {
					shallow: true,
					replace: !push,
					state: push ? { element: { depuis: fiche } } : page.state
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
		/** Zone du fil, distincte de celle de la carte : les vols lancés par le registre ne la changent pas. */
		get zoneFil() {
			return zoneFil;
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
		/** Fiche ouverte, commune ou propre ; `null` : la carte seule. */
		get fiche() {
			return fiche;
		},
		/** Fiche propre ouverte et la couche qui la déclare. */
		get propre() {
			return propre;
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
		/** Onglet choisi dans la fiche commune ; `null` : le premier. */
		get onglet() {
			return onglet;
		},
		set onglet(id: string | null) {
			onglet = id;
		},
		/** La `Carte` de cette couche doit être montée (activée, ou désactivée après l'avoir été). */
		montee: (id: string) => montees.has(id),
		active: (id: string) => actives.includes(id),
		activer,
		ouvrir,
		fermer,
		fermerFiche,
		composant,
		contexte,
		carte,
		deplacement,
		deplacementVoulu,
		brancherAdresse
	};
}

export type Registre = ReturnType<typeof creerRegistre>;

/** Le registre de la coquille, pour les pages du groupe de la carte (titre de la fiche ouverte). */
export const [registreCourant, fournirRegistre] = createContext<Registre>();
