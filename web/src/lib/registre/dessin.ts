// Ce que la carte dessine, tiré de l'état du registre : une seule couche à la fois, en plus de celles qui le sont
// toujours. Le dessin des couches, le grisage et l'attribution de la carte en dépendent.
import { rubriqueAVolet } from './rubriques.js';
import type { CoucheInscrite } from './types.js';

/**
 * La couche dessinée : celle de l'onglet courant quand une fiche commune est ouverte (`ongletCommune`), sinon celle de
 * la rubrique ouverte dans le panneau ; au sommaire, aucune. La fiche propre d'une couche n'y change rien.
 */
export function coucheDessinee(
	couches: readonly CoucheInscrite[],
	{ panneau, ongletCommune }: { panneau: string; ongletCommune: string | null }
): string | null {
	if (ongletCommune !== null) return ongletCommune;
	return rubriqueAVolet(couches, panneau)?.couche.id ?? null;
}

/**
 * La carte d'une couche dessine toujours quelque chose : une couche permanente (Hôtels de ville), ou le marqueur de
 * sa fiche propre (le Grand Conseil). Sa `Carte` est montée dès l'arrivée.
 */
export const toujoursSurLaCarte = (c: CoucheInscrite) => c.permanente || c.fiche !== undefined;

/** Les couches qui montrent quelque chose sur la carte, dans l'ordre du registre : la couche dessinée comprise. */
export const couchesSurLaCarte = (couches: readonly CoucheInscrite[], dessinee: string | null): string[] =>
	couches.filter((c) => toujoursSurLaCarte(c) || c.id === dessinee).map((c) => c.id);
