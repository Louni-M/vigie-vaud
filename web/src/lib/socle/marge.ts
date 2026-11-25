/** Largeur de carte (px) qu'il faut voir à côté du panneau pour que la carte centre ses vues dans ce reste. */
export const LARGEUR_UTILE = 300;

/**
 * Marge gauche de la carte, en px : le bord droit du panneau posé dessus (`bordPanneau`, depuis le bord gauche de la
 * carte), ou 0 quand il resterait moins de `LARGEUR_UTILE` px de carte à côté de lui (tablette, fiche ouverte) : une
 * commune cadrée dans une bande étroite dézoomerait jusqu'au canton.
 */
export const margeDuPanneau = (largeurCarte: number, bordPanneau: number) =>
	largeurCarte - bordPanneau < LARGEUR_UTILE ? 0 : bordPanneau;
