// État partagé d'une source chargée une fois par visite, dans le navigateur, au premier besoin : l'état des sources
// (`couverture-courante`), le dernier import des conseils (`imports-courants`). Après un échec, il réessaie de
// lui-même, à intervalles croissants, jusqu'à la réussite : la page n'a rien à redemander, et ses lectures, faites
// dans des `$derived`, ne relancent jamais de requête.
import { browser } from '$app/env';

/** Attente avant chaque nouvel essai après un échec ; la dernière se répète tant que la source reste en panne. */
export const DELAIS_ESSAI: readonly number[] = [5_000, 15_000, 60_000, 300_000];

/**
 * Ce que rend `creerEtatSource` : à ne pas confondre avec `EtatSource` du schéma, l'état d'une source selon le cron.
 */
export interface EtatSourcePartage<T> {
	/** La valeur, une fois un essai réussi ; `null` avant. Demande le chargement. */
	valeur(): T | null;
	/** Vrai une fois le premier essai terminé, même en échec : la valeur reste alors `null` en attendant le suivant. */
	chargee(): boolean;
}

/**
 * L'état d'une source que `charger` lit, et qui rejette en cas d'échec. Rien n'est chargé hors du navigateur
 * (`actif`, faux à la pré-génération) : la valeur y reste `null`.
 */
export function creerEtatSource<T>(
	charger: () => Promise<T>,
	{ actif = browser }: { actif?: boolean } = {}
): EtatSourcePartage<T> {
	let valeur = $state.raw<T | null>(null);
	let chargee = $state(false);
	// Pas d'état réactif ici : `demander` est appelée depuis des `$derived`, où l'écrire est interdit.
	let demande = false;
	let echecs = 0;

	function essayer() {
		charger().then(
			(v) => {
				valeur = v;
				chargee = true;
			},
			() => {
				chargee = true;
				setTimeout(essayer, DELAIS_ESSAI[Math.min(echecs++, DELAIS_ESSAI.length - 1)]);
			}
		);
	}

	function demander() {
		if (actif && !demande) {
			demande = true;
			essayer();
		}
	}

	return {
		valeur() {
			demander();
			return valeur;
		},
		chargee() {
			demander();
			return chargee;
		}
	};
}
