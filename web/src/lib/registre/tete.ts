import type { Commune } from '#lib/types.js';
import type { CoucheInscrite } from './types.js';

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
		titre: `${commune.nom} – Vigie Vaud`,
		description: `${commune.nom} (VD) sur Vigie Vaud : ${enumerer(resumes)}.`
	};
}
