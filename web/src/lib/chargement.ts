// Chargement côté site, partagé par toutes ses requêtes : le délai d'attente d'une requête, la promesse gardée par
// clé pour la visite, et la lecture d'un fichier JSON versionné (dépôt de données).

type Fetch = typeof fetch;

/** Délai d'attente de toute requête du site : au-delà, elle est interrompue et rejette (`delaiDepasse`). */
export const DELAI_REQUETE = 20_000;

/**
 * `f(entree, init)`, interrompue au bout de `delai` ms si la réponse n'est pas entièrement arrivée (corps compris).
 * Elle rejette alors par une `DOMException` « TimeoutError », que reconnaît `delaiDepasse`.
 */
export function requeteAvecDelai(
	f: Fetch,
	entree: RequestInfo | URL,
	init: RequestInit = {},
	delai: number = DELAI_REQUETE
): Promise<Response> {
	return f(entree, { ...init, signal: AbortSignal.timeout(delai) });
}

/** L'échec vient-il du délai d'attente dépassé (et non d'une panne du réseau) ? */
export const delaiDepasse = (e: unknown): boolean => e instanceof DOMException && e.name === 'TimeoutError';

/**
 * Un fichier JSON, par son adresse, s'il porte la `version` attendue : le site n'y vérifie rien d'autre, le contenu
 * étant validé à l'écriture (cron, préparation). Rejette s'il est injoignable, trop lent (`delaiDepasse`), en erreur
 * HTTP, illisible ou d'une autre version. `absent` : ce que vaut un fichier qui n'existe pas (404), au lieu de
 * rejeter. `init` : les options de la requête (`{ cache: 'no-cache' }`).
 */
export async function lireJsonVersionne<T>(
	f: Fetch,
	adresse: string,
	version: number,
	{ init, absent }: { init?: RequestInit; absent?: { vaut: T } } = {}
): Promise<T> {
	const r = await requeteAvecDelai(f, adresse, init);
	if (r.status === 404 && absent) return absent.vaut;
	if (!r.ok) throw new Error(`${adresse} : HTTP ${r.status}`);
	const contenu: unknown = await r.json();
	const lu = contenuVersionne<T>(contenu, version);
	if (lu === null)
		throw new Error(`${adresse} : version inconnue (${String((contenu as { version?: unknown } | null)?.version)})`);
	return lu;
}

/** Un JSON déjà lu, s'il est un objet de la `version` attendue ; `null` sinon. */
export function contenuVersionne<T>(json: unknown, version: number): T | null {
	return typeof json === 'object' && json !== null && (json as { version?: unknown }).version === version
		? (json as T)
		: null;
}

/** Des promesses gardées par clé pour la visite (`memoPromesse`). */
export interface MemoPromesse<K> {
	/**
	 * La promesse de la clé : celle de `g()` au premier appel, la même ensuite tant qu'elle est en cours ou après sa
	 * réussite. Un échec est oublié : l'appel suivant rappelle `g`. Rendue telle quelle, sans enveloppe : un même
	 * objet d'un appel à l'autre (`{#await}`).
	 */
	<T>(cle: K, g: () => Promise<T>): Promise<T>;
	/** La clé a-t-elle une promesse, en cours ou réussie ? */
	demandee(cle: K): boolean;
}

/** Une promesse par clé, oubliée en cas d'échec : chaque chargement n'est fait qu'une fois par visite s'il réussit. */
export function memoPromesse<K>(): MemoPromesse<K> {
	const promesses = new Map<K, Promise<unknown>>();
	function obtenir<T>(cle: K, g: () => Promise<T>): Promise<T> {
		const gardee = promesses.get(cle) as Promise<T> | undefined;
		if (gardee) return gardee;
		const p = g();
		promesses.set(cle, p);
		p.catch(() => {
			if (promesses.get(cle) === p) promesses.delete(cle);
		});
		return p;
	}
	return Object.assign(obtenir, { demandee: (cle: K) => promesses.has(cle) });
}
