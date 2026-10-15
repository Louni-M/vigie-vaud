import type { Commune } from '#lib/types.js';

/**
 * Faux service du canton (MapServer/537) et fichiers des communes, pour les tests : un `fetch` qui
 * répond aux seules requêtes qu'envoie le module de données Permis, et garde la trace de chacune.
 */

export const PULLY: Commune = { bfs: 5590, nom: 'Pully', slug: 'pully', habitants: 18900, bbox: [6.65, 46.49, 6.7, 46.52] };
export const LUTRY: Commune = { bfs: 5606, nom: 'Lutry', slug: 'lutry', habitants: 10500, bbox: [6.7, 46.49, 6.75, 46.52] };

/** Limites carrées, sans lac : le rattachement par position est alors évident. */
const carre = ([w, s, e, n]: Commune['bbox']) => [[[[w, s], [e, s], [e, n], [w, n], [w, s]]]];

export interface EntiteCamac {
	attributes: Record<string, string | number | null>;
	geometry?: { x: number; y: number };
}

/** Une entité CAMAC telle que la renvoie le canton ; par défaut, une construction à l'enquête à Pully. */
export function entite(no: number, a: Record<string, string | number | null> = {}, [x, y] = [6.67, 46.5]): EntiteCamac {
	return {
		attributes: {
			NO_CAMAC: no,
			NO_FAO: null,
			DATE_ENQUETE: 'Du 19.09.2026 au 19.10.2026',
			NATURE: 'Construction nouvelle',
			DESCRIPTION: null,
			DECISION_COMMUNALE: null,
			DATE_DECISION: null,
			URL: null,
			ETAT: 'Enquête publique en cours',
			...a
		},
		geometry: { x, y }
	};
}

const PAGE = 2000;
const annee = (e: EntiteCamac) => String(e.attributes.DATE_ENQUETE ?? '').slice(9, 13);

/** Le sous-ensemble du SQL ArcGIS qu'emploie le module de données. */
function filtre(where: string): (e: EntiteCamac) => boolean {
	if (where === '1=1') return () => true;
	let m = where.match(/^NO_CAMAC IN \(([\d,]+)\)$/);
	if (m) {
		const ids = new Set(m[1].split(',').map(Number));
		return (e) => ids.has(Number(e.attributes.NO_CAMAC));
	}
	m = where.match(/^SUBSTRING\(DATE_ENQUETE FROM 10 FOR 4\) = '(\d{4})'$/);
	if (m) {
		const a = m[1];
		return (e) => annee(e) === a;
	}
	m = where.match(
		/^\(ETAT = '(.+?)' OR \(ETAT = '(.+?)' AND SUBSTRING\(DATE_ENQUETE FROM 10 FOR 4\) >= '(\d{4})'\)\)$/
	);
	if (m) {
		const [, enquete, procedure, a] = m;
		return (e) => e.attributes.ETAT === enquete || (e.attributes.ETAT === procedure && annee(e) >= a);
	}
	throw new Error(`Requête non prévue par le faux canton : ${where}`);
}

export interface FauxCanton {
	fetch: typeof fetch;
	/** Clauses `where` des requêtes d'entités reçues (comptages exclus), dans l'ordre. */
	requetes: string[];
	/** Le service répond désormais par cette erreur HTTP (`null` : rétabli). */
	panne(statut: number | null): void;
}

export function fauxCanton(entites: EntiteCamac[], communes: Commune[] = [PULLY, LUTRY]): FauxCanton {
	const requetes: string[] = [];
	let statutPanne: number | null = null;
	const json = (corps: unknown, status = 200) =>
		new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } });

	const repondre = async (entree: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
		const url = new URL(entree instanceof Request ? entree.url : String(entree), 'http://localhost');
		if (url.pathname.endsWith('/communes.json')) return json(communes);
		if (url.pathname.endsWith('/communes-limites.json'))
			return json(Object.fromEntries(communes.map((c) => [c.bfs, carre(c.bbox)])));
		if (!url.pathname.endsWith('/MapServer/537/query')) throw new Error(`Adresse non prévue : ${url}`);
		if (statutPanne) return new Response('', { status: statutPanne });

		const p = init?.body ? new URLSearchParams(String(init.body)) : url.searchParams;
		const where = p.get('where') ?? '';
		let choisies = entites.filter(filtre(where));
		const geometrie = p.get('geometry');
		if (geometrie) {
			const [w, s, e, n] = geometrie.split(',').map(Number);
			choisies = choisies.filter(({ geometry: g }) => g && g.x >= w && g.x <= e && g.y >= s && g.y <= n);
		}
		if (p.get('returnCountOnly') === 'true') return json({ count: choisies.length });
		requetes.push(where);
		choisies.sort((a, b) => Number(a.attributes.NO_CAMAC) - Number(b.attributes.NO_CAMAC));
		const debut = Number(p.get('resultOffset') ?? 0);
		const n = Math.min(Number(p.get('resultRecordCount') ?? PAGE), PAGE);
		return json({ features: choisies.slice(debut, debut + n), exceededTransferLimit: choisies.length > debut + n });
	};

	return {
		fetch: repondre as typeof fetch,
		requetes,
		panne: (s) => (statutPanne = s)
	};
}
