/**
 * Les sortes de restriction de circulation, lues du champ `RESTRICTION` de la DGMR, et leurs couleurs sur la carte.
 * Module léger : la description de la couche l'importe sans charger le module de données. La carte y prend sa
 * priorité au clic.
 */

import type { EtatRestriction } from './etats.js';

export type Sorte = 'fermeture' | 'deviation' | 'feux' | 'particuliere' | 'autre';

/**
 * Nom de la puce et couleur de chaque sorte, dans l'ordre de la légende. La puce « Autres » reçoit toute valeur
 * inconnue, en gris ; la restriction, elle, garde son libellé publié.
 */
export const SORTES: Record<Sorte, { nom: string; couleur: string }> = {
	fermeture: { nom: 'Fermeture', couleur: '#c92a2a' },
	deviation: { nom: 'Déviation', couleur: '#e8590c' },
	feux: { nom: 'Feux', couleur: '#e0a800' },
	particuliere: { nom: 'Restriction particulière', couleur: '#7048e8' },
	autre: { nom: 'Autres', couleur: '#868e96' }
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

/** Une déviation se dessine en tirets : sur la carte, dans la légende et devant chaque restriction listée. */
export const enTirets = (s: Sorte) => s === 'deviation';

/** Ce qui précède une restriction dans une liste ou une fiche : sa sorte telle que publiée, sa couleur et son trait. */
export interface Pastille {
	/** La sorte telle que publiée (« Fermeture », ou une valeur inconnue comme « Manifestation »). */
	sorte: string;
	couleur: string;
	/** Une déviation : son trait est en tirets, comme sur la carte. */
	tirets: boolean;
}

export const pastille = (r: { sorte: Sorte; libelleSorte: string }): Pastille => ({
	sorte: r.libelleSorte,
	couleur: SORTES[r.sorte].couleur,
	tirets: enTirets(r.sorte)
});

/**
 * Priorité au clic sur des restrictions superposées, de la plus contraignante à la moins contraignante : ce qui
 * bloque d'abord, la déviation en dernier (elle reste à un clic par « Mêmes travaux »).
 */
export const PRIORITE_CLIC: readonly Sorte[] = ['fermeture', 'feux', 'particuliere', 'autre', 'deviation'];

/**
 * La restriction à ouvrir parmi celles sous le clic : la plus contraignante ; à sorte égale l'en cours, dessinée
 * au-dessus de l'à venir, puis le plus petit `OBJECTID`, pour que le même clic ouvre toujours la même restriction.
 */
export function plusContraignante<T extends { id: number; sorte: Sorte; etat: EtatRestriction }>(
	restrictions: readonly T[]
): T | null {
	const rang = (r: T) => PRIORITE_CLIC.indexOf(r.sorte);
	const ordre = (a: T, b: T) =>
		rang(a) - rang(b) || Number(a.etat === 'a_venir') - Number(b.etat === 'a_venir') || a.id - b.id;
	return [...restrictions].sort(ordre)[0] ?? null;
}
