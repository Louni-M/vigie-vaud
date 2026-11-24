/**
 * Coquille sur téléphone : une seule vue plein écran à la fois, choisie dans la barre du bas : le panneau (le
 * sommaire ou la rubrique ouverte), la carte, et la fiche quand quelque chose est ouvert.
 */

/**
 * Téléphone : la largeur seule décide. Une condition sur la hauteur faisait basculer le téléphone dans la mise en page
 * du bureau dès que le clavier s'ouvrait. À l'horizontale (plus de 760 px de large) et sur tablette, la carte et la
 * fiche restent côte à côte.
 */
export const TELEPHONE = '(max-width: 760px)';

/** Vue plein écran affichée sur téléphone ; elle est dans l'adresse (`affichage=carte`), avec son historique. */
export type Affichage = 'panneau' | 'carte' | 'fiche';

/**
 * La vue que nomme l'adresse (`affichage=…`), ou `null`. Les anciennes vues Fil et Couches, qui montraient ce que
 * montre le panneau, sont lues comme lui.
 */
export function lireAffichage(texte: string | null): Affichage | null {
	if (texte === 'fil' || texte === 'couches') return 'panneau';
	return texte === 'panneau' || texte === 'carte' || texte === 'fiche' ? texte : null;
}

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
 * montrer quand plus rien n'est ouvert : on revient à la vue d'où la fiche a été ouverte (`origine`). Un élément
 * ouvert depuis le panneau s'affiche en aperçu, sur la carte ; une fiche ouverte depuis le panneau, dans la vue Fiche.
 */
export function affichageApres(affichage: Affichage, avant: Ouverture, apres: Ouverture, origine: Affichage): Affichage {
	if (apres.fiche === null) return affichage === 'fiche' ? origine : affichage;
	const element = apres.element !== null && apres.element !== avant.element;
	if (element) return affichageOuverture(affichage);
	return apres.fiche !== avant.fiche && affichage === 'panneau' ? 'fiche' : affichage;
}

/**
 * Vue affichée dès qu'on ouvre un élément, avant de savoir dans quelle fiche : depuis le panneau, la carte, pour son
 * aperçu ; les autres vues restent.
 */
export const affichageOuverture = (affichage: Affichage): Affichage => (affichage === 'panneau' ? 'carte' : affichage);

/**
 * Vue affichée à l'arrivée, et celle qui va avec l'adresse quand elle n'en nomme aucune : la fiche quand le chemin en
 * ouvre une (`/commune/pully`, `/grand-conseil`), la carte quand l'adresse ouvre un élément ou nomme une vue de la
 * carte (`vue=`), sinon le panneau.
 */
export function affichageArrivee(ouverture: Ouverture, avecVue: boolean): Affichage {
	if (ouverture.fiche !== null) return 'fiche';
	return ouverture.element !== null || avecVue ? 'carte' : 'panneau';
}

/**
 * Vue que donne l'adresse : celle de sa requête (`affichage=carte`), sinon celle de l'arrivée (`affichageArrivee`).
 * « Fiche » sans fiche ouverte n'a rien à montrer : celle de l'arrivée.
 */
export function affichageDeLAdresse(demandee: Affichage | null, ouverture: Ouverture, avecVue: boolean): Affichage {
	if (demandee === null || (demandee === 'fiche' && ouverture.fiche === null)) return affichageArrivee(ouverture, avecVue);
	return demandee;
}

/**
 * Décalage (px) vers le haut d'un point vers lequel la carte vole, pour le placer au milieu de la bande libre de
 * la carte : `haut` px couverts en haut (recherche), `bas` px en bas (aperçu).
 */
export const decalageAuDessus = (haut: number, bas: number) => (bas - haut) / 2;

/**
 * La Recherche `ouverte` s'affiche en plein écran par-dessus la vue Carte ou le panneau, en tête desquels elle se
 * trouve ; ce n'est pas une quatrième vue. Le bureau ne l'ouvre jamais.
 */
export const recherchePleine = (telephone: boolean, affichage: Affichage, ouverte: boolean) =>
	telephone && affichage !== 'fiche' && ouverte;

/** Ce qui referme la Recherche plein écran : un résultat choisi, « Annuler », ou le retour arrière du téléphone. */
export type FinRecherche = 'choix' | 'annuler' | 'retour';

/**
 * Texte du champ de la carte quand la Recherche se referme. « Annuler » et le retour arrière effacent ce qu'on a tapé
 * et rendent le texte d'avant l'ouverture (`avant`) ; un résultat choisi laisse son nom (`champ`), comme sur bureau.
 */
export const texteApresRecherche = (fin: FinRecherche, avant: string, champ: string) =>
	fin === 'choix' ? champ : avant;
