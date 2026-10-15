import { untrack } from 'svelte';
import { SvelteSet } from 'svelte/reactivity';
import { afterNavigate, goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';
import type { Map as MlMap } from 'maplibre-gl';
import type { Commune, Centre, Zone } from '#lib/types.js';
import type { Chargeur, Cible, Contexte, CoucheInscrite, Lecteur, Ouvert } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';
import { mouvement } from './navigation.js';

/** Ce que le registre demande à la carte du socle quand l'adresse change sous lui. */
export interface VueCarte {
	aller(c: Centre, anime?: boolean): void;
	vueCanton(): void;
	/** Cadre une emprise ; `parDefaut` : la vue obtenue n'entre pas dans l'adresse. */
	cadrer(emprise: [number, number, number, number], anime?: boolean, parDefaut?: boolean): void;
}

/** Route de la fiche commune : la commune ouverte est dans le chemin (ADR 0012). */
const ROUTE_COMMUNE = '/(carte)/commune/[slug]' as const;

/** Emprise sur laquelle cadrer une commune : sa partie terrestre quand elle est connue, sinon toute la commune. */
export const cadreDe = (c: Commune) => c.cadre ?? c.bbox;

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
	/** Couches activées au moins une fois : leur `Carte` reste montée, pour le fondu à la désactivation. */
	const montees = new SvelteSet<string>(depart.actives);

	/** Slug de la commune dont la fiche est ouverte, lu dans le chemin. */
	const slug = $derived(page.route.id === ROUTE_COMMUNE ? (page.params.slug ?? null) : null);
	const commune = $derived(slug === null ? null : (communes().find((c) => c.slug === slug) ?? null));

	const etat = (): EtatUrl => ({ actives, vue, ouvert, parametres });
	const requete = $derived(ecrireUrl(couches, etat()));

	function appliquer(e: EtatUrl) {
		actives = e.actives;
		for (const id of e.actives) montees.add(id);
		parametres = e.parametres;
		ouvert = e.ouvert;
	}

	/* ---- Composants, importés une seule fois chacun, à la demande ---- */

	const charges = new Map<string, ReturnType<Chargeur<unknown>>>();
	function composant(c: CoucheInscrite, nom: NomComposant) {
		const chargeur = c.composants[nom];
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
		if (c) carteSocle()?.cadrer(cadreDe(c), anime, true);
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

	function ouvrir(cible: Cible) {
		if ('commune' in cible) return ouvrirCommune(cible.commune);
		if (ouvert?.couche === cible.couche && ouvert.element === cible.element) return;
		nouvelleEntree = true;
		ouvert = { couche: cible.couche, element: cible.element };
	}

	function fermer() {
		if (!ouvert) return;
		if (page.state.fiche) history.back();
		else ouvert = null;
	}

	/** Contexte passé aux composants d'une couche ; ses valeurs suivent l'état du registre. */
	function contexte(c: CoucheInscrite): Contexte {
		return {
			get map() {
				if (!map) throw new Error('Carte pas encore prête');
				return map;
			},
			avant: `couche:${c.id}`,
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
			ouvrir,
			fermer
		};
	}

	/* ---- Carte du socle ---- */

	/** La carte est prête : un calque vide par couche, dans l'ordre du registre, sous le repère du socle. */
	function carte(m: MlMap, sous: string) {
		for (const c of couches)
			m.addLayer({ id: `couche:${c.id}`, type: 'background', layout: { visibility: 'none' } }, sous);
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
		/** Commune de l'adresse reflétée par l'état. */
		let suivie: string | null = null;

		/** L'adresse a changé sous le registre : l'état la suit, et la carte bouge s'il le faut. */
		function suivre(params: Lecteur, initial: boolean) {
			const e = lireUrl(couches, params);
			appliquer(e);
			vue = e.vue;
			const m = mouvement(suivie, { commune: slug, vue: e.vue, ouvert: e.ouvert }, initial);
			suivie = slug;
			if (m === 'canton') carteSocle()?.vueCanton();
			else if (m && 'aller' in m) carteSocle()?.aller(m.aller, !initial);
			else if (m) cadrerCommune(m.cadrer, !initial);
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
				goto(`${location.pathname}${q}`, {
					shallow: true,
					replace: !push,
					state: push ? { fiche: true } : page.state
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
