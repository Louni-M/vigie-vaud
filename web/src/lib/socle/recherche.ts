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
		...actuelles.map((c): ResultatCommune => ({ type: 'commune', label: c.nom, commune: c })),
		...anciens.map(({ a, c }): ResultatCommune => ({ type: 'commune', label: `${a.nom} → ${c.nom}`, commune: c }))
	];
}
