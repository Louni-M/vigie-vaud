/**
 * Coquille sur téléphone : une seule vue plein écran à la fois, choisie dans la barre Carte · Couches · Fiche.
 */

/** Téléphone en portrait. À l'horizontale et sur tablette, la carte et la fiche restent côte à côte. */
export const TELEPHONE = '(max-width: 760px) and (min-height: 521px)';

/** Vue plein écran affichée sur téléphone. */
export type Affichage = 'carte' | 'couches' | 'fiche';

/** Ce qui est ouvert : commune de la fiche (slug) et élément ouvert (« couche:élément »). */
export interface Ouverture {
	commune: string | null;
	element: string | null;
}

/**
 * Vue affichée quand ce qui est ouvert change (ouverture, fermeture, retour du navigateur). « Fiche » n'a rien à
 * montrer quand plus rien n'est ouvert : on revient à la carte.
 */
export function affichageApres(affichage: Affichage, avant: Ouverture, apres: Ouverture): Affichage {
	if (apres.commune === null) return affichage === 'fiche' ? 'carte' : affichage;
	const nouveau = apres.commune !== avant.commune || (apres.element !== null && apres.element !== avant.element);
	return nouveau && affichage === 'couches' ? 'carte' : affichage;
}

/**
 * Décalage (px) vers le haut d'un point vers lequel la carte vole, pour le placer au milieu de la bande libre de
 * la carte : `haut` px couverts en haut (recherche), `bas` px en bas (aperçu).
 */
export const decalageAuDessus = (haut: number, bas: number) => (bas - haut) / 2;
