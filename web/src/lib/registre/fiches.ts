// Les fiches propres que déclarent les couches inscrites (`Couche.fiche`). Le registre ne les connaît que par ce
// que les couches en disent : identifiant, chemin, nom, position.
import type { CoucheInscrite, FichePropre } from './types.js';

/** Une fiche propre et la couche qui la déclare. */
export interface FicheDeCouche {
	couche: CoucheInscrite;
	fiche: FichePropre;
}

/** Les fiches propres des couches, dans l'ordre du registre. */
export const fichesPropres = (couches: readonly CoucheInscrite[]): FicheDeCouche[] =>
	couches.flatMap((couche) => (couche.fiche ? [{ couche, fiche: couche.fiche }] : []));

/** La fiche propre de cet identifiant, ou `null`. */
export const fichePropre = (couches: readonly CoucheInscrite[], id: string): FicheDeCouche | null =>
	fichesPropres(couches).find((f) => f.fiche.id === id) ?? null;

/** La fiche propre dont la page a ce chemin (« /grand-conseil »), ou `null`. */
export const ficheDuChemin = (couches: readonly CoucheInscrite[], chemin: string): FicheDeCouche | null =>
	fichesPropres(couches).find((f) => f.fiche.chemin === chemin) ?? null;
