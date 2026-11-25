import { normaliser } from '#lib/labels.js';
import type { Commune, Resultat } from '#lib/types.js';
import { fichesPropres } from './fiches.js';
import { nomOnglet } from './onglet.js';
import { rubriqueDeLElement } from './rubriques.js';
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

/**
 * Les fiches propres que la saisie nomme, par leur nom ou un alias, dans l'ordre du registre, sous le nom de la
 * rubrique qui les ouvre.
 */
export function chercherFiches(couches: readonly CoucheInscrite[], texte: string): Extract<Resultat, { type: 'fiche' }>[] {
	const saisie = normaliser(texte);
	return fichesPropres(couches)
		.filter(({ fiche }) => [fiche.nom, ...(fiche.alias ?? [])].some((nom) => correspond(nom, saisie)))
		.map(({ couche, fiche }) => ({
			type: 'fiche' as const,
			nomRubrique: nomOnglet(couche, fiche.id),
			libelle: fiche.nom,
			fiche: fiche.id
		}));
}

/**
 * Résultats du registre pour une saisie, tels que les affiche la recherche du socle : les fiches propres, puis les
 * éléments des couches (`chercher`), chacun sous le nom de sa rubrique (`rubriqueDeLElement`) : un Objet du Grand
 * Conseil sous « Grand Conseil », celui d'un conseil communal sous « Conseils communaux ». Le registre trouve les
 * fiches sans passer par `chercher`.
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
			nomRubrique: rubriqueDeLElement(couches, r)?.rubrique.nom ?? c.nom,
			libelle: r.libelle,
			couche: r.couche,
			element: r.element
		}))
	)
];
