import { afterNavigate, goto } from '$app/navigation';
import { page } from '$app/state';
import type { Lecteur } from './types.js';

/** Une adresse, telle que le registre la lit. */
type Url = Pick<URL, 'pathname' | 'search'> & { readonly searchParams: Lecteur };

/**
 * Ce que le registre lit de la page de SvelteKit (`page` de `$app/state`) : un objet stable, dont les propriétés
 * suivent la navigation (réactives).
 */
export interface PageCarte {
	readonly route: { readonly id: string | null };
	readonly params: Readonly<Partial<Record<string, string>>>;
	/** État de l'entrée d'historique courante. */
	readonly state: App.PageState;
	/** Adresse de la page rendue. */
	readonly url: Url;
	/** Adresse écrite par une navigation superficielle (`goto(…, { shallow: true })`), par-dessus `url`. */
	readonly shallow: { readonly url: Url } | null;
}

/** Les options de `goto` dont se sert le registre. */
export interface OptionsNavigation {
	replace?: boolean;
	reset?: boolean;
	shallow?: boolean;
	state?: App.PageState;
}

/**
 * Le seul accès du registre à la navigation, à l'adresse et à l'historique. Le site lui donne ceux de SvelteKit et
 * du navigateur (`navigateurSvelteKit`) ; les tests, un faux navigateur.
 */
export interface Navigateur {
	readonly page: PageCarte;
	/** Chemin et requête de la barre d'adresse (`location`) : en avance sur `page` pendant une navigation. */
	readonly emplacement: { readonly pathname: string; readonly search: string };
	/** Change de page, ou d'entrée d'historique (`shallow`) ; résolue une fois l'adresse écrite et la page à jour. */
	goto(url: string, options: OptionsNavigation): Promise<void>;
	/** Remonte l'historique de `pas` entrées (`history.go(-pas)`). */
	reculer(pas: number): void;
	/** `f` est appelée après chaque navigation (`afterNavigate`) ; à brancher pendant l'initialisation d'un composant. */
	apresNavigation(f: () => void): void;
	/**
	 * `f` est appelée chaque fois que le navigateur change d'entrée par le précédent ou le suivant (`popstate`), avant
	 * que la page ne suive ; renvoie de quoi la débrancher.
	 */
	surParcours(f: () => void): () => void;
}

/** La navigation de SvelteKit et l'historique du navigateur, lus seulement à l'usage (les pages sont pré-générées). */
export function navigateurSvelteKit(): Navigateur {
	return {
		page,
		get emplacement() {
			return location;
		},
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- simple relais : l'adresse vient du registre, déjà construite
		goto: (url, options) => goto(url, options),
		reculer: (pas) => history.go(-pas),
		apresNavigation: (f) => afterNavigate(f),
		surParcours: (f) => {
			addEventListener('popstate', f);
			return () => removeEventListener('popstate', f);
		}
	};
}
