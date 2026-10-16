import type { Commune } from '#lib/types.js';
import { enteteFiche } from './entete.js';
import type { CoucheInscrite, FichePropre, Ouvert } from './types.js';

/** « a », « a et b », « a, b et c ». */
function enumerer(parties: string[]): string {
	return parties.length > 1 ? `${parties.slice(0, -1).join(', ')} et ${parties.at(-1)}` : (parties[0] ?? '');
}

/**
 * Titre et description de la page d'une commune (`/commune/<slug>`), pré-générée : c'est ce qu'affiche l'aperçu
 * d'un lien partagé. La description dit ce que les couches inscrites montrent de la commune, dans l'ordre du registre,
 * puis nomme ses anciennes communes et ses anciens noms.
 */
export function teteCommune(commune: Commune, couches: readonly CoucheInscrite[]) {
	const resumes = couches.flatMap((c) => {
		const resume = typeof c.resume === 'function' ? c.resume(commune) : c.resume;
		return resume ? [resume] : [];
	});
	// Les anciennes communes, comme dans l'en-tête de la fiche : on retrouve son village dans l'aperçu du lien.
	const anciens = enteteFiche(commune).anciens.map((l) => ` ${l}.`);
	return {
		titre: titreFiche(commune.nom, null, couches),
		description: `${commune.nom} (VD) sur Vigie Vaud : ${enumerer(resumes)}.${anciens.join('')}`
	};
}

/**
 * Titre et description de la page d'une fiche propre (`/grand-conseil`), pré-générée : le nom et la description que
 * la couche déclare pour sa fiche.
 */
export function teteFiche(fiche: FichePropre) {
	return { titre: titreFiche(fiche.nom, null, []), description: fiche.description };
}

/**
 * Titre du document quand une fiche est ouverte : « Pully – Vigie Vaud » pour une commune, « Grand Conseil – Vigie
 * Vaud » pour une fiche propre, ou le `titre` que la couche donne à l'élément ouvert (« Dossier n° 248845 – Lutry –
 * Vigie Vaud »), qui reçoit `nom`, le nom de la fiche du chemin, où l'élément est ouvert.
 */
export function titreFiche(nom: string, ouvert: Ouvert | null, couches: readonly CoucheInscrite[]): string {
	const titre = ouvert && couches.find((c) => c.id === ouvert.couche)?.titre;
	return titre ? titre(ouvert.element, nom) : `${nom} – Vigie Vaud`;
}
