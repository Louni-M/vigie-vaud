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
		...anciens.map(({ a, c }): ResultatCommune => ({ type: 'commune', libelle: `${a.nom} → ${c.nom}`, commune: c }))
	];
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
