// Badge de fraîcheur : de quand datent les données d'une source, ou pourquoi elles manquent. Un badge par source,
// sans agrégat, sous le nom de chaque onglet et dans le volet de la couche (décisions de #2).
import { SvelteMap } from 'svelte/reactivity';
import { dateHeure, type EtatCouverture } from './couverture.js';
import type { Source } from './schema';

/** Pourquoi le dernier chargement d'une source a échoué, vu du navigateur. */
export type CauseEchec = 'hors_ligne' | 'indisponible';

/**
 * État d'une source à l'exécution, tenu par son code d'accès (pour Permis, le module de données).
 * `derniere` : dernière donnée obtenue, selon la sorte de fraîcheur de la source (heure de la requête, date de la
 * donnée, ou millésime d'une source Préparée) ; `null` tant que rien n'a été obtenu.
 */
export interface EtatSourceExecution {
	readonly derniere: Date | number | null;
	/** Le dernier chargement a échoué, nouvelle tentative automatique comprise. */
	readonly erreur: CauseEchec | null;
	/** Recharge la source, sans recharger la page. */
	recharger(): void;
}

const CAUSES: Record<CauseEchec, string> = {
	hors_ligne: 'hors ligne',
	indisponible: 'service indisponible'
};

/** « à l’instant », « il y a 4 min », « il y a 2 h », « il y a 3 j ». */
function age(date: Date, maintenant: Date): string {
	const minutes = Math.floor((maintenant.getTime() - date.getTime()) / 60_000);
	if (minutes < 1) return 'à l’instant';
	if (minutes < 60) return `il y a ${minutes} min`;
	if (minutes < 24 * 60) return `il y a ${Math.floor(minutes / 60)} h`;
	return `il y a ${Math.floor(minutes / (24 * 60))} j`;
}

/**
 * Libellé du badge d'une source, suivi de son nom court : « consulté il y a 2 min · CAMAC » (`requete`),
 * « il y a 4 min · DGMR » (`donnee`), « édition 2025 · UCV » (`millesime`), ou la cause d'un échec.
 */
export function libelleBadge(
	source: Pick<Source, 'fraicheur' | 'nom_court'>,
	etat: Pick<EtatSourceExecution, 'derniere' | 'erreur'>,
	maintenant: Date
): string {
	const { derniere, erreur } = etat;
	let quand: string;
	if (erreur) quand = CAUSES[erreur];
	else if (source.fraicheur === 'millesime')
		quand = derniere == null ? 'édition inconnue' : `édition ${typeof derniere === 'number' ? derniere : derniere.getFullYear()}`;
	else if (derniere == null) quand = source.fraicheur === 'requete' ? 'pas encore consulté' : 'pas encore chargé';
	else {
		const date = typeof derniere === 'number' ? new Date(derniere, 0, 1) : derniere;
		quand = source.fraicheur === 'requete' ? `consulté ${age(date, maintenant)}` : age(date, maintenant);
	}
	return `${quand} · ${source.nom_court}`;
}

/** La cause d'un échec, dans le message d'échec. */
const CAUSES_MESSAGE: Record<CauseEchec, string> = {
	hors_ligne: 'vous semblez hors ligne',
	indisponible: 'le service est indisponible pour le moment'
};

/**
 * Message d'échec d'une source Direct, après la nouvelle tentative automatique : « Source en panne depuis le … »
 * si la surveillance a constaté une panne (état tiré de la Couverture), sinon le message de la couche et la cause
 * vue du navigateur. `null` tant que le navigateur obtient les données, même si le cron déclare la panne.
 */
export function messageEchec(message: string, cause: CauseEchec | null, etat: EtatCouverture): string | null {
	if (!cause) return null;
	if (etat.etat === 'en_panne') return etat.depuis ? `Source en panne depuis le ${dateHeure(etat.depuis)}.` : 'Source en panne.';
	return `${message} : ${CAUSES_MESSAGE[cause]}.`;
}

/* ---- États des sources à l'exécution, inscrits par leur code d'accès ---- */

const etats = new SvelteMap<string, EtatSourceExecution>();

/** Le code d'accès d'une source y inscrit son état, une seule fois. */
export function inscrireEtat(id: string, etat: EtatSourceExecution): void {
	etats.set(id, etat);
}

/** État de la source à l'exécution, ou `null` si son code d'accès n'est pas encore chargé. */
export function etatSource(id: string): EtatSourceExecution | null {
	return etats.get(id) ?? null;
}
