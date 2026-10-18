/**
 * Les deux états d'une restriction de circulation et leurs libellés. Module léger, comme `sortes.ts` : les fonctions
 * pures et les composants l'importent sans charger le module de données.
 */

/** En cours si la restriction vient de la 596, à venir si elle vient de la 595 : le site ne le recalcule pas. */
export type EtatRestriction = 'en_cours' | 'a_venir';

/**
 * Libellé de chaque état, dans l'ordre des listes : `nom` seul (puces, sections de l'onglet, fiche), `minuscules`
 * dans une phrase (« les restrictions à venir », « à venir · Lutry »).
 */
export const ETATS = {
	en_cours: { nom: 'En cours', minuscules: 'en cours' },
	a_venir: { nom: 'À venir', minuscules: 'à venir' }
} as const satisfies Record<EtatRestriction, { nom: string; minuscules: string }>;
