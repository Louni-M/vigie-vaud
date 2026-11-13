import { requeteAvecDelai } from '#lib/chargement.js';
import { normaliser } from '#lib/labels.js';
import type { Commune, Resultat } from '#lib/types.js';

type ResultatCommune = Extract<Resultat, { type: 'commune' }>;

/** Les noms qui commencent par la saisie passent en premier (« Yverdon » → Yverdon-les-Bains), puis les plus courts. */
function correspondants<T>(elements: readonly T[], nom: (e: T) => string, nq: string): T[] {
	return elements
		.map((e) => ({ e, n: normaliser(nom(e)) }))
		.filter(({ n }) => n.includes(nq))
		.sort((a, b) => Number(!a.n.startsWith(nq)) - Number(!b.n.startsWith(nq)) || a.n.length - b.n.length)
		.map(({ e }) => e);
}

/** Entre l'ancien nom et la commune actuelle, dans le libellé d'un ancien nom. */
const FLECHE = ' → ';

/**
 * Communes qui correspondent à une saisie, pour la recherche flottante : d'abord les communes actuelles, puis les
 * anciennes communes et les anciens noms, qui mènent à la commune actuelle (« Cully → Bourg-en-Lavaux »).
 */
export function chercherCommunes(communes: readonly Commune[], saisie: string): ResultatCommune[] {
	const nq = normaliser(saisie);
	if (nq.length < 2) return [];
	const actuelles = correspondants(communes, (c) => c.nom, nq).slice(0, 4);
	// Un ancien nom n'apporte rien quand sa commune est déjà proposée (« Yverdon » → Yverdon-les-Bains).
	const anciens = correspondants(
		communes.filter((c) => !actuelles.includes(c)).flatMap((c) => c.anciens.map((a) => ({ a, c }))),
		({ a }) => a.nom,
		nq
	).slice(0, 3);
	return [
		...actuelles.map((c): ResultatCommune => ({ type: 'commune', libelle: c.nom, commune: c })),
		...anciens.map(({ a, c }): ResultatCommune => ({ type: 'commune', libelle: `${a.nom}${FLECHE}${c.nom}`, commune: c }))
	];
}

/**
 * Le libellé d'un ancien nom, coupé autour de sa flèche (« Cully → Bourg-en-Lavaux » : `['Cully',
 * 'Bourg-en-Lavaux']`), pour que la liste montre la flèche sans la faire lire ; `null` pour tout autre libellé.
 */
export function ancienEtActuelle(r: Resultat): [string, string] | null {
	if (r.type !== 'commune') return null;
	const i = r.libelle.indexOf(FLECHE);
	return i < 0 ? null : [r.libelle.slice(0, i), r.libelle.slice(i + FLECHE.length)];
}

/**
 * Résultats calculés sans réseau, à chaque frappe : les communes (et anciens noms), puis ce qu'apportent les
 * couches (`chercherCouches` : fiches propres, puis éléments).
 */
export const resultatsLocaux = (
	communes: readonly Commune[],
	saisie: string,
	chercherCouches: (texte: string) => Resultat[]
): Resultat[] => [...chercherCommunes(communes, saisie), ...chercherCouches(saisie)];

/** Nombre de résultats affichés, adresses comprises. */
export const RESULTATS_MAX = 10;

/**
 * Les adresses et lieux swisstopo à la suite des résultats locaux. Un même lieu revient sous plusieurs catégories
 * (sortie d'autoroute, camping…), ou porte le nom d'une commune déjà proposée : un seul suffit.
 */
export function avecAdresses(locaux: readonly Resultat[], adresses: readonly Resultat[]): Resultat[] {
	const vus = new Set(locaux.map((r) => r.libelle));
	const uniques = adresses.filter((r) => !vus.has(r.libelle) && vus.add(r.libelle));
	return [...locaux, ...uniques].slice(0, RESULTATS_MAX);
}

interface Lieu {
	attrs: { origin: string; label: string; detail?: string; lat: number; lon: number };
}

const TYPES: Record<string, string> = { address: 'Adresse', zipcode: 'NPA', gazetteer: 'Lieu' };

/**
 * Le canton figure dans `detail` pour les adresses (« … ch vd ») et dans le libellé des lieux (« (VD) ») ;
 * pour les NPA, on vérifie que le point tombe dans le cadre d'une commune vaudoise.
 */
function vaudois({ attrs: a }: Lieu, communes: readonly Commune[]): boolean {
	if (a.origin === 'address') return / ch vd$/.test(a.detail ?? '');
	if (a.origin === 'gazetteer') return a.label.includes('(VD)');
	return communes.some(({ bbox: [w, s, e, n] }) => a.lon >= w && a.lon <= e && a.lat >= s && a.lat <= n);
}

/**
 * « <i>Lieu</i> <b>Donatyre</b> (VD) - Avenches » → « Donatyre - Avenches », et « Avenches - Avenches » → « Avenches » :
 * le type est affiché à part.
 */
const nettoyer = (label: string) =>
	label
		.replace(/<i>.*?<\/i>/g, '')
		.replace(/<[^>]+>/g, '')
		.replace(' (VD)', '')
		.replace(/\s+/g, ' ')
		.trim()
		.replace(/^(.+) - \1$/, '$1');

/**
 * Adresses et lieux swisstopo (geo.admin.ch) du canton pour une saisie. Rejette si swisstopo est injoignable, trop
 * lent (`delaiDepasse`) ou répond une erreur HTTP : la Recherche le dit, au lieu d'annoncer qu'il n'y a rien.
 */
export async function chercherAdresses(
	f: typeof fetch,
	saisie: string,
	communes: readonly Commune[]
): Promise<Resultat[]> {
	// Le filtre par cadre (bbox) vide les résultats.
	const url = new URL('https://api3.geo.admin.ch/rest/services/api/SearchServer');
	url.search = new URLSearchParams({
		searchText: saisie,
		type: 'locations',
		// Pas de « gg25 » : les communes viennent de la liste locale (communes actuelles).
		origins: 'address,zipcode,gazetteer',
		sr: '4326',
		lang: 'fr',
		// Les résultats hors canton sont écartés ensuite : on en demande davantage.
		limit: '20'
	}).toString();
	const r = await requeteAvecDelai(f, url);
	if (!r.ok) throw new Error(`Recherche swisstopo : HTTP ${r.status}`);
	const json: { results?: Lieu[] } = await r.json();
	return (json.results ?? [])
		.filter((l) => vaudois(l, communes))
		.map(({ attrs: a }) => ({
			type: 'adresse',
			categorie: TYPES[a.origin] ?? 'Lieu',
			libelle: nettoyer(a.label),
			lon: a.lon,
			lat: a.lat
		}));
}
