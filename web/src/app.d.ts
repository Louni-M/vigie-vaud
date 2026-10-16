// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		interface PageState {
			/**
			 * Entrée d'historique poussée par l'application à l'ouverture d'un élément : `depuis` est la fiche de
			 * l'entrée précédente (`null` : la carte seule). Fermer l'élément y revient si c'est la même fiche.
			 */
			element?: { depuis: import('#lib/registre/types.js').Fiche | null };
		}
		// interface Platform {}
	}
}

export {};
