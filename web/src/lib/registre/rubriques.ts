// Les rubriques du sommaire, déclarées par les couches : le registre les range et les compte sans en nommer aucune.
import { nombre } from '#lib/almanach/typographie.js';
import type { Commune, Zone } from '#lib/types.js';
import type { Compter, CoucheInscrite, EtatCompte, Ouvert, Rubrique } from './types.js';

/** Une rubrique et la couche qui la déclare. */
export interface RubriqueInscrite {
	rubrique: Rubrique;
	couche: CoucheInscrite;
}

/** Les rubriques de toutes les couches, dans l'ordre du sommaire (leur rang). */
export function rubriquesDuSommaire(couches: readonly CoucheInscrite[]): RubriqueInscrite[] {
	return couches
		.flatMap((couche) => (couche.rubriques ?? []).map((rubrique) => ({ rubrique, couche })))
		.sort((a, b) => a.rubrique.rang - b.rubrique.rang);
}

/** La rubrique à volet d'identifiant `id` (celle que le panneau ouvre sous `volet=id`) ; `null` s'il n'y en a pas. */
export const rubriqueAVolet = (couches: readonly CoucheInscrite[], id: string): RubriqueInscrite | null =>
	rubriquesDuSommaire(couches).find(({ rubrique: r }) => !r.fiche && r.id === id) ?? null;

/** La rubrique où va un élément : celle que sa couche nomme d'après sa clé, sinon sa première ; `null` sans rubrique. */
export function rubriqueDeLElement(couches: readonly CoucheInscrite[], o: Ouvert): RubriqueInscrite | null {
	const couche = couches.find((c) => c.id === o.couche);
	const rubriques = couche?.rubriques ?? [];
	const id = couche?.rubriqueDe?.(o.element) ?? rubriques[0]?.id;
	const rubrique = rubriques.find((r) => r.id === id);
	return couche && rubrique ? { rubrique, couche } : null;
}

/**
 * Le nombre d'une rubrique pour la zone de la carte. Tant que la carte n'a rien affiché, celui d'une rubrique qui
 * compte la zone se charge.
 */
export const etatDuCompte = (
	r: Pick<Rubrique, 'portee'>,
	compter: Compter,
	zone: Zone | null,
	communes: readonly Commune[]
): EtatCompte => (r.portee === 'zone' && zone === null ? { etat: 'chargement' } : compter(zone, communes));

/**
 * La phrase du nombre d'une rubrique, que partagent sa ligne du sommaire et sa liste : le nombre (à mettre en
 * valeur), puis ce qui le suit. Zéro n'a pas de nombre : « Aucun dossier en cours dans la zone affichée ».
 */
export function phraseCompte(
	r: Pick<Rubrique, 'unite' | 'portee'>,
	n: number
): { nombre: string | null; texte: string } {
	const ou = r.portee === 'canton' ? ', pour tout le canton' : ' dans la zone affichée';
	if (n === 0) return { nombre: null, texte: `${r.unite.feminin ? 'Aucune' : 'Aucun'} ${r.unite.un}${ou}` };
	return { nombre: nombre.format(n), texte: `\u00a0${n > 1 ? r.unite.plusieurs : r.unite.un}${ou}` };
}
