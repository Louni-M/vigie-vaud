// Règles du registre pour un élément qu'il n'ouvre pas, valables pour toute couche : le message près de la
// recherche et l'onglet de sa couche (spec J2, « Registre »).
import type { CoucheInscrite, Fiche, Ouvert } from './types.js';

const coucheDe = (couches: readonly CoucheInscrite[], o: Ouvert) => couches.find((c) => c.id === o.couche);

/** Message près de la recherche quand la couche n'a pas pu chercher l'élément (`localiser` a rejeté). */
export function avisNonCherche(couches: readonly CoucheInscrite[], o: Ouvert): string {
	return (
		coucheDe(couches, o)?.nonCherche?.(o.element) ??
		`Le n° ${o.element} n’a pas pu être cherché : vérifiez votre connexion, puis réessayez.`
	);
}

/**
 * Élément que sa couche ne trouve pas : le message près de la recherche (`introuvable`), et l'onglet de sa couche,
 * que la fiche commune du chemin ouvre (`/commune/lutry?d=<dossier disparu>` : l'onglet Permis de Lutry). Sans
 * fiche commune dans le chemin, ou pour une couche sans onglet, `onglet` est `null` : il n'y a que le message.
 */
export function avisIntrouvable(
	couches: readonly CoucheInscrite[],
	o: Ouvert,
	fiche: Fiche | null
): { avis: string; onglet: string | null } {
	const couche = coucheDe(couches, o);
	// Une fiche propre n'a que l'onglet de sa couche : rien à choisir.
	const onglet = fiche && 'commune' in fiche && couche?.composants.Onglet ? couche.id : null;
	return { avis: couche?.introuvable?.(o.element) ?? `Aucun élément n° ${o.element}.`, onglet };
}
