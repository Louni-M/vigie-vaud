/**
 * Coquille sur téléphone : une seule vue plein écran à la fois, choisie dans la barre Carte · Fil · Couches · Fiche.
 */

/** Téléphone en portrait. À l'horizontale et sur tablette, la carte et la fiche restent côte à côte. */
export const TELEPHONE = '(max-width: 760px) and (min-height: 521px)';

/** Vue plein écran affichée sur téléphone. */
export type Affichage = 'carte' | 'fil' | 'couches' | 'fiche';

/**
 * Ce qui est ouvert : la fiche (« commune:pully », « fiche:grand-conseil ») et l'élément ouvert
 * (« couche:élément »).
 */
export interface Ouverture {
	fiche: string | null;
	element: string | null;
}

/**
 * Vue affichée quand ce qui est ouvert change (ouverture, fermeture, retour du navigateur). « Fiche » n'a rien à
 * montrer quand plus rien n'est ouvert : on revient à la carte. Ce qu'on ouvre depuis la vue Couches ou la vue Fil
 * s'affiche en aperçu, sur la carte.
 */
export function affichageApres(affichage: Affichage, avant: Ouverture, apres: Ouverture): Affichage {
	if (apres.fiche === null) return affichage === 'fiche' ? 'carte' : affichage;
	const nouveau = apres.fiche !== avant.fiche || (apres.element !== null && apres.element !== avant.element);
	return nouveau && (affichage === 'couches' || affichage === 'fil') ? 'carte' : affichage;
}

/** Vue affichée à l'arrivée : celle de la fiche du chemin (`/commune/pully`, `/grand-conseil`), sinon la carte. */
export const affichageArrivee = (ouverture: Ouverture): Affichage => (ouverture.fiche === null ? 'carte' : 'fiche');

/**
 * Décalage (px) vers le haut d'un point vers lequel la carte vole, pour le placer au milieu de la bande libre de
 * la carte : `haut` px couverts en haut (recherche), `bas` px en bas (aperçu).
 */
export const decalageAuDessus = (haut: number, bas: number) => (bas - haut) / 2;
