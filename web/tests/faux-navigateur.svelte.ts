import type { Navigateur, OptionsNavigation, PageCarte } from '#lib/registre/navigateur.js';

/*
 * Faux navigateur pour les tests du registre : un historique d'entrées et la page de SvelteKit qui le suit, comme le
 * fait le client de SvelteKit (`@sveltejs/kit/src/runtime/client/client.js`).
 *
 * - Une navigation superficielle (`shallow`) écrit l'adresse, puis met à jour `page.state` et `page.shallow` ; la page
 *   rendue (`page.url`, sa route) ne change pas.
 * - Une navigation vers une page met à jour l'adresse et la page ensemble, avec `page.shallow` à `null`.
 * - Au retour et à l'avance, le navigateur change d'entrée et prévient ses écouteurs (`popstate`) tout de suite, et la
 *   page suit plus tard : entre deux entrées d'une même page, seuls l'état et `page.shallow` changent ; sinon la page
 *   change, et `afterNavigate` suit. Le retour demandé par l'application (`reculer`) part dans une tâche à part.
 * - Toutes les navigations sont résolues après quelques micro-tâches, jamais tout de suite.
 */

const ORIGINE = 'https://vigie.test';

interface Entree {
	/** Adresse de la barre d'adresse. */
	url: URL;
	/** Adresse de la page rendue : celle de la dernière navigation vers une page. */
	page: URL;
	state: App.PageState;
	/** Écrite par une navigation superficielle. */
	superficielle: boolean;
	/** Numéro de la navigation vers une page qui l'a créée, ou dont elle dépend. */
	navigation: number;
}

/** Route et paramètres d'un chemin du groupe de la carte. */
function route(chemin: string): Pick<PageCarte, 'route' | 'params'> {
	const commune = /^\/commune\/([^/]+)$/.exec(chemin);
	if (commune) return { route: { id: '/(carte)/commune/[slug]' }, params: { slug: commune[1] } };
	const fiche = /^\/([^/]+)$/.exec(chemin);
	if (fiche) return { route: { id: '/(carte)/[fiche]' }, params: { fiche: fiche[1] } };
	return { route: { id: '/(carte)' }, params: {} };
}

const pageDe = (e: Entree): PageCarte => ({
	...route(e.page.pathname),
	state: e.state,
	url: e.page,
	shallow: e.superficielle ? { url: e.url } : null
});

/** Laisse passer quelques micro-tâches : le temps que SvelteKit résolve l'adresse ou charge la page. */
const plusTard = async () => {
	for (let i = 0; i < 3; i++) await Promise.resolve();
};

/**
 * Une tâche à part, comme le `setTimeout(0)` du navigateur, mais sans minuteur : sous Windows, Node n'en déclenche un
 * qu'au pas de ~15 ms de l'horloge système, au lieu de ~1 ms sous Linux, et les tests du registre en attendent des
 * dizaines.
 */
export const tache = () => new Promise<void>((r) => setImmediate(r));

/** Le chemin et la requête d'une adresse (« /commune/pully?d=1 »). */
const relative = (u: URL) => u.pathname + u.search;

/** Un navigateur arrivé sur `depart` (« /?d=248845 »), avant que la coquille ne soit montée. */
export function creerFauxNavigateur(depart: string) {
	// eslint-disable-next-line svelte/prefer-svelte-reactivity -- adresse figée d'une entrée, jamais modifiée
	const premiere = new URL(depart, ORIGINE);
	let entrees: Entree[] = [{ url: premiere, page: premiere, state: {}, superficielle: false, navigation: 0 }];
	let index = 0;
	let navigations = 0;
	let page = $state.raw<PageCarte>(pageDe(entrees[0]));
	/** Comme celle de SvelteKit, la page est un objet stable dont les propriétés suivent la navigation. */
	const pageStable: PageCarte = {
		get route() {
			return page.route;
		},
		get params() {
			return page.params;
		},
		get state() {
			return page.state;
		},
		get url() {
			return page.url;
		},
		get shallow() {
			return page.shallow;
		}
	};
	const rappels: (() => void)[] = [];
	const apresNavigation = () => rappels.forEach((f) => f());
	/** Écouteurs de `popstate`. */
	let parcours: (() => void)[] = [];

	/** Ajoute `e` après l'entrée courante (les entrées suivantes sont perdues), ou la met à sa place. */
	function ecrire(e: Entree, remplacer: boolean) {
		if (remplacer) entrees[index] = e;
		else {
			entrees = [...entrees.slice(0, index + 1), e];
			index++;
		}
	}

	/** Parcourt l'historique de `delta` entrées, comme les boutons du navigateur. */
	async function parcourir(delta: number) {
		const i = index + delta;
		if (i < 0 || i >= entrees.length) return;
		const avant = entrees[index];
		index = i;
		const e = entrees[i];
		parcours.forEach((f) => f());
		await plusTard();
		page = pageDe(e);
		if (e.navigation !== avant.navigation) apresNavigation();
	}

	const navigateur: Navigateur = {
		page: pageStable,
		get emplacement() {
			return entrees[index].url;
		},
		async goto(url: string, o: OptionsNavigation) {
			// eslint-disable-next-line svelte/prefer-svelte-reactivity -- adresse figée d'une entrée, jamais modifiée
			const cible = new URL(url, ORIGINE);
			const state = structuredClone($state.snapshot(o.state ?? {}));
			await plusTard();
			if (o.shallow) {
				const courante = entrees[index];
				const e = { url: cible, page: courante.page, state, superficielle: true, navigation: courante.navigation };
				ecrire(e, o.replace ?? false);
				await plusTard();
				page = pageDe(e);
			} else {
				const e = { url: cible, page: cible, state, superficielle: false, navigation: ++navigations };
				ecrire(e, o.replace ?? false);
				page = pageDe(e);
			}
			apresNavigation();
		},
		// `history.go` ne parcourt l'historique que plus tard, dans une tâche à part.
		reculer: (pas) => void tache().then(() => parcourir(-pas)),
		apresNavigation: (f) => void rappels.push(f),
		surParcours(f) {
			parcours.push(f);
			return () => (parcours = parcours.filter((g) => g !== f));
		}
	};

	return {
		navigateur,
		/** La coquille est montée : SvelteKit appelle `afterNavigate` une première fois. */
		monter: apresNavigation,
		/** Le bouton précédent du navigateur. */
		precedent: () => parcourir(-1),
		/** Le bouton suivant du navigateur. */
		suivant: () => parcourir(1),
		/** Adresse courante (« /commune/pully?d=1 »). */
		get adresse() {
			return relative(entrees[index].url);
		},
		/** Toutes les entrées de l'historique, l'entrée courante comprise. */
		get historique() {
			return entrees.map((e) => relative(e.url));
		},
		/** Position de l'entrée courante dans `historique`. */
		get index() {
			return index;
		},
		/** État de l'entrée courante. */
		get etat() {
			return entrees[index].state;
		}
	};
}

export type FauxNavigateur = ReturnType<typeof creerFauxNavigateur>;
