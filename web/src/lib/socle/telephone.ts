/**
 * Coquille sur téléphone : une seule vue plein écran à la fois, choisie dans la barre Carte · Fil · Couches · Fiche.
 */

/**
 * Téléphone : la largeur seule décide. Une condition sur la hauteur faisait basculer le téléphone dans la mise en page
 * du bureau dès que le clavier s'ouvrait. À l'horizontale (plus de 760 px de large) et sur tablette, la carte et la
 * fiche restent côte à côte.
 */
export const TELEPHONE = '(max-width: 760px)';

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

/**
 * La Recherche `ouverte` s'affiche en plein écran par-dessus la vue Carte, et depuis elle seule ; ce n'est pas une
 * cinquième vue. Le bureau ne l'ouvre jamais.
 */
export const recherchePleine = (telephone: boolean, affichage: Affichage, ouverte: boolean) =>
	telephone && affichage === 'carte' && ouverte;

/** Ce qui referme la Recherche plein écran : un résultat choisi, « Annuler », ou le retour arrière du téléphone. */
export type FinRecherche = 'choix' | 'annuler' | 'retour';

/**
 * Texte du champ de la carte quand la Recherche se referme. « Annuler » et le retour arrière effacent ce qu'on a tapé
 * et rendent le texte d'avant l'ouverture (`avant`) ; un résultat choisi laisse son nom (`champ`), comme sur bureau.
 */
export const texteApresRecherche = (fin: FinRecherche, avant: string, champ: string) =>
	fin === 'choix' ? champ : avant;
