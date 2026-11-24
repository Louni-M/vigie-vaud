// Badge de fraîcheur : de quand datent les données d'une source, ou pourquoi elles manquent. Un badge par source,
// sans agrégat, sous le nom de chaque onglet et dans le volet de la couche (décisions de #2), sauf les sites des
// communes, regroupés par plateforme dans le volet.
import { SvelteMap } from 'svelte/reactivity';
import { dateHeure, type EtatCouverture } from './couverture.js';
import type { SorteFraicheur, Source } from './schema';

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

type SansMillesime = Exclude<SorteFraicheur, 'millesime'>;

/** Ce qui précède l'âge de la dernière donnée. */
const PREFIXES: Record<SansMillesime, string> = { requete: 'consulté ', donnee: '', import: 'mis à jour ' };

/** Tant que rien n'a été obtenu ; pour un conseil, `conseils/import.json` manque ou ne le cite pas. */
const PAS_ENCORE: Record<SansMillesime, string> = {
	requete: 'pas encore consulté',
	donnee: 'pas encore chargé',
	import: 'dernière mise à jour inconnue'
};

/**
 * Libellé du badge d'une source, suivi de son nom court : « consulté il y a 2 min · CAMAC » ou « consulté il y a
 * 2 min · DGMR » (`requete`), « il y a 4 min · … » (`donnee`, l'âge de la donnée elle-même, qu'aucune source ne
 * donne encore), « édition 2025 · UCV » (`millesime`), « mis à jour il y a 6 h · Grand Conseil » (`import`,
 * dernier import réussi du conseil), ou la cause d'un échec.
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
	else if (derniere == null) quand = PAS_ENCORE[source.fraicheur];
	else {
		const date = typeof derniere === 'number' ? new Date(derniere, 0, 1) : derniere;
		quand = `${PREFIXES[source.fraicheur]}${age(date, maintenant)}`;
	}
	return `${quand} · ${source.nom_court}`;
}

/**
 * Libellé du badge des sites d'une plateforme, après la liste de la rubrique : un seul badge pour toutes ses communes
 * couvertes, qui donne le plus ancien de leurs derniers imports réussis (« mis à jour il y a 45 min · sites de
 * 19 communes »), ou combien l'ont déjà été (« mis à jour il y a 45 min · 1 site de commune sur 19 »). Le nom de la
 * plateforme n'y est pas : il ne dit rien au visiteur. Le badge de chaque site reste sous l'onglet de sa commune.
 */
export function libelleBadgeSites(imports: readonly (Date | null)[], maintenant: Date): string {
	const total = imports.length;
	const sites = `site${total > 1 ? 's' : ''} de ${total}\u00a0commune${total > 1 ? 's' : ''}`;
	const dates = imports.filter((d): d is Date => d != null);
	if (dates.length === 0) return `dernière mise à jour inconnue · ${sites}`;
	const plusAncien = new Date(Math.min(...dates.map((d) => d.getTime())));
	const quand = `mis à jour ${age(plusAncien, maintenant)}`;
	if (dates.length === total) return `${quand} · ${sites}`;
	return `${quand} · ${dates.length}\u00a0site${dates.length > 1 ? 's' : ''} de commune sur ${total}`;
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
export function etatExecution(id: string): EtatSourceExecution | null {
	return etats.get(id) ?? null;
}
