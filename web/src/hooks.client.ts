import { navigating } from '$app/state';
import { estFeuilleDeStyle, reserverRechargement } from '#lib/rechargement.js';

// Un fichier du site n'a pas pu être chargé (#lib/rechargement.ts). Ce module est lu avant le chargement des
// pages : l'écoute couvre aussi le premier affichage.
addEventListener('vite:preloadError', (event) => {
	// Pendant une navigation, SvelteKit s'en charge : s'il voit une nouvelle version, il charge la page cible en entier.
	if (navigating.to) return;
	if (reserverRechargement(() => sessionStorage, Date.now())) {
		location.reload();
	} else if (estFeuilleDeStyle(event.payload)) {
		// Déjà rechargée : on continue sans cette feuille de style plutôt que de laisser la page inerte.
		event.preventDefault();
	}
});
