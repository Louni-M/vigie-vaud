import type { AncienNom, Commune } from '#lib/types.js';

function liste(anciens: AncienNom[], type: AncienNom['type'], singulier: string, pluriel: string): string[] {
	const noms = anciens.filter((a) => a.type === type).map((a) => a.nom);
	if (!noms.length) return [];
	return [`${noms.length > 1 ? pluriel : singulier} : ${noms.join(', ')}`];
}

/**
 * Ce que l'en-tête de la fiche commune dit sous son nom. `siege` est l'adresse de l'hôtel de ville, ou `null`
 * quand sa position est approximative ; `anciens` liste les anciennes communes puis les anciens noms
 * (« Anciennes communes : Cully, Epesses, Grandvaux, Riex, Villette (Lavaux) »).
 */
export function enteteFiche(commune: Commune): { siege: string | null; anciens: string[] } {
	return {
		siege: commune.adresse || null,
		anciens: [
			...liste(commune.anciens, 'Ancienne commune', 'Ancienne commune', 'Anciennes communes'),
			...liste(commune.anciens, 'Ancien nom', 'Ancien nom', 'Anciens noms')
		]
	};
}
