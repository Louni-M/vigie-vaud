/**
 * Grisage sur téléphone. Sur bureau, le grisage suit le volet ouvert ; sur téléphone, les volets sont empilés dans
 * la vue Couches, loin de la carte : le bouton « Voir sur la carte » du volet d'une couche montre son grisage sur
 * la vue Carte, avec la pastille « Couverture : <couche> × ». Il dure jusqu'à la croix, au choix d'une autre couche
 * ou à la désactivation de la couche, survit aux changements de vue et n'entre pas dans l'adresse.
 */

/** Id de la couche dont le grisage est montré sur la carte du téléphone, ou `null`. */
export type GrisageMobile = string | null;

export type EvenementGrisage =
	/** « Voir sur la carte » dans le volet de cette couche. */
	| { voir: string }
	/** La croix de la pastille. */
	| { effacer: true }
	/** Les couches activées ont changé. */
	| { actives: readonly string[] };

/** Le grisage après un événement. */
export function grisageApres(grisage: GrisageMobile, e: EvenementGrisage): GrisageMobile {
	if ('voir' in e) return e.voir;
	if ('effacer' in e) return null;
	return grisage !== null && e.actives.includes(grisage) ? grisage : null;
}
