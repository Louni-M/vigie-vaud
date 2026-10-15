import type { Commune } from '#lib/types.js';
import type { CoucheInscrite, Ouvert } from './types.js';

/** « a », « a et b », « a, b et c ». */
function enumerer(parties: string[]): string {
	return parties.length > 1 ? `${parties.slice(0, -1).join(', ')} et ${parties.at(-1)}` : (parties[0] ?? '');
}

/**
 * Titre et description de la page d'une commune (`/commune/<slug>`), pré-générée : c'est ce qu'affiche l'aperçu
 * d'un lien partagé. La description dit ce que les couches inscrites montrent de la commune, dans l'ordre du registre.
 */
export function teteCommune(commune: Commune, couches: readonly CoucheInscrite[]) {
	const resumes = couches.flatMap((c) => (c.resume ? [c.resume] : []));
	return {
		titre: titreFiche(commune, null, couches),
		description: `${commune.nom} (VD) sur Vigie Vaud : ${enumerer(resumes)}.`
	};
}

/**
 * Titre du document quand une fiche est ouverte : « Pully – Vigie Vaud » pour une commune, ou le `titre` que la
 * couche donne à l'élément ouvert (« Dossier n° 248845 – Lutry – Vigie Vaud »). L'élément est toujours dans la
 * commune du chemin.
 */
export function titreFiche(commune: Commune, ouvert: Ouvert | null, couches: readonly CoucheInscrite[]): string {
	const titre = ouvert && couches.find((c) => c.id === ouvert.couche)?.titre;
	return titre ? titre(ouvert.element, commune.nom) : `${commune.nom} – Vigie Vaud`;
}
