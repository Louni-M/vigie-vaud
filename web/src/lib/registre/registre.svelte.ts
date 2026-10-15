import { untrack } from 'svelte';
import { SvelteSet } from 'svelte/reactivity';
import { afterNavigate, goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { page } from '$app/state';
import type { Map as MlMap } from 'maplibre-gl';
import type { Centre, Zone } from '#lib/types.js';
import type { Chargeur, Cible, Contexte, CoucheInscrite, Ouvert } from './types.js';
import { ecrireUrl, lireUrl, type EtatUrl } from './url.js';

/** Ce que le registre demande à la carte du socle quand l'adresse change sous lui. */
export interface VueCarte {
	aller(c: Centre, anime?: boolean): void;
	vueCanton(): void;
}

type NomComposant = keyof CoucheInscrite['composants'];

/**
 * Le registre des couches à l'exécution : couches activées, paramètres des couches, vue, élément ouvert
 * et volet ouvert. Il est le seul maître de l'adresse : `brancherAdresse` synchronise son état avec la
 * requête (`replace` pour la vue et les réglages, `push` pour l'ouverture d'un élément).
 */
export function creerRegistre(couches: readonly CoucheInscrite[]) {
	const depart = lireUrl(couches, new URLSearchParams());

	let actives = $state<string[]>(depart.actives);
	let parametres = $state.raw<Record<string, unknown>>(depart.parametres);
	let vue = $state<Centre | null>(null);
	let zone = $state.raw<Zone | null>(null);
	let ouvert = $state<Ouvert | null>(null);
	let map = $state.raw<MlMap | null>(null);
	/** Volet ouvert sur la carte (bureau) ; n'entre pas dans l'adresse. */
	let volet = $state<string | null>(null);
	/** Couches activées au moins une fois : leur `Carte` reste montée, pour le fondu à la désactivation. */
	const montees = new SvelteSet<string>(depart.actives);

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

	function ouvrir(cible: Cible) {
		if ('commune' in cible) {
			goto(resolve('/commune/[slug]', { slug: cible.commune }));
			return;
		}
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
	function deplacement(z: Zone, centre: Centre, parDefaut: boolean) {
		zone = z;
		vue = parDefaut ? null : centre;
	}

	/* ---- Adresse ---- */

	/**
	 * Synchronise l'état et l'adresse, dans les deux sens. À appeler pendant l'initialisation de la coquille.
	 * Les pages sont pré-générées sans paramètres : l'adresse de départ est lue après le premier rendu.
	 */
	function brancherAdresse(carteSocle: () => VueCarte | undefined) {
		/** Requête déjà reflétée par l'état ; `null` tant que l'adresse de départ n'a pas été lue. */
		let synchro: string | null = null;

		afterNavigate(() => {
			if (synchro !== null) return;
			synchro = location.search;
			const e = lireUrl(couches, new URLSearchParams(location.search));
			appliquer(e);
			if (e.vue) {
				vue = e.vue;
				carteSocle()?.aller(e.vue, false);
			}
		});

		// État → adresse. Les déplacements et les réglages remplacent l'entrée courante.
		$effect(() => {
			const q = requete;
			untrack(() => {
				const push = nouvelleEntree;
				nouvelleEntree = false;
				if (synchro === null || q === location.search) return;
				synchro = q;
				goto(`${location.pathname}${q}`, {
					shallow: true,
					replace: !push,
					state: push ? { fiche: true } : page.state
				});
			});
		});

		// Adresse → état : précédent et suivant du navigateur, logo et lien « Carte » de l'en-tête.
		$effect(() => {
			const url = page.shallow?.url ?? page.url;
			const q = url.search;
			untrack(() => {
				if (synchro === null || q === synchro) return;
				synchro = q;
				const e = lireUrl(couches, url.searchParams);
				appliquer(e);
				if (e.vue) {
					vue = e.vue;
					carteSocle()?.aller(e.vue);
				} else if (!e.ouvert) {
					// Adresse nue « / » : retour à la vue d'ensemble du canton.
					vue = null;
					carteSocle()?.vueCanton();
				}
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
		composant,
		contexte,
		carte,
		deplacement,
		brancherAdresse
	};
}

export type Registre = ReturnType<typeof creerRegistre>;
