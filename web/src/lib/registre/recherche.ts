import { normaliser } from '#lib/labels.js';
import type { Commune, Resultat } from '#lib/types.js';
import { fichesPropres } from './fiches.js';
import type { CoucheInscrite } from './types.js';

/** Ce que le registre apporte à la recherche du socle : fiches propres et éléments des couches. */
export type ResultatRegistre = Extract<Resultat, { type: 'fiche' | 'element' }>;

/**
 * Un nom ou un alias correspond à une saisie de 2 lettres au moins dont il commence, sans accents ni casse ; un nom
 * de 2 lettres (« GC ») seulement s'il est tapé en entier.
 */
function correspond(nom: string, saisie: string): boolean {
	const n = normaliser(nom);
	if (saisie.length < 2) return false;
	return n.length <= 2 ? n === saisie : n.startsWith(saisie);
}

/** Les fiches propres que la saisie nomme, par leur nom ou un alias, dans l'ordre du registre. */
export function chercherFiches(couches: readonly CoucheInscrite[], texte: string): Extract<Resultat, { type: 'fiche' }>[] {
	const saisie = normaliser(texte);
	return fichesPropres(couches)
		.filter(({ fiche }) => [fiche.nom, ...(fiche.alias ?? [])].some((nom) => correspond(nom, saisie)))
		.map(({ couche, fiche }) => ({ type: 'fiche' as const, nomCouche: couche.nom, libelle: fiche.nom, fiche: fiche.id }));
}

/**
 * Résultats du registre pour une saisie, tels que les affiche la recherche du socle : les fiches propres, puis les
 * éléments des couches (`chercher`). Le registre trouve les fiches sans passer par `chercher`.
 */
export const resultatsCouches = (
	couches: readonly CoucheInscrite[],
	texte: string,
	communes: readonly Commune[]
): ResultatRegistre[] => [
	...chercherFiches(couches, texte),
	...couches.flatMap((c) =>
		(c.chercher?.(texte, communes) ?? []).map((r) => ({
			type: 'element' as const,
			nomCouche: c.nom,
			libelle: r.libelle,
			couche: r.couche,
			element: r.element
		}))
	)
];
