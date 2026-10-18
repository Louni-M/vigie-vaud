/**
 * Les sortes de restriction de circulation, lues du champ `RESTRICTION` de la DGMR, et leurs couleurs sur la carte.
 * Module léger : la description de la couche l'importe sans charger le module de données.
 */

export type Sorte = 'fermeture' | 'deviation' | 'feux' | 'particuliere' | 'autre';

/** Nom et couleur de chaque sorte, dans l'ordre de la légende. « Autre » reçoit toute valeur inconnue, en gris. */
export const SORTES: Record<Sorte, { nom: string; couleur: string }> = {
	fermeture: { nom: 'Fermeture', couleur: '#c92a2a' },
	deviation: { nom: 'Déviation', couleur: '#e8590c' },
	feux: { nom: 'Feux', couleur: '#e0a800' },
	particuliere: { nom: 'Restriction particulière', couleur: '#7048e8' },
	autre: { nom: 'Autre', couleur: '#868e96' }
};

const PUBLIEES: Record<string, Sorte> = {
	Fermeture: 'fermeture',
	Déviation: 'deviation',
	Feux: 'feux',
	'Restriction particulière': 'particuliere'
};

/**
 * La sorte d'une valeur de `RESTRICTION`. Une valeur inconnue (la DGMR prévoit « Manifestation » et « Autre »,
 * absentes à ce jour) devient « autre » ; son libellé publié reste affiché tel quel.
 */
export const sorteDe = (restriction: string | null): Sorte =>
	restriction && Object.hasOwn(PUBLIEES, restriction) ? PUBLIEES[restriction] : 'autre';
