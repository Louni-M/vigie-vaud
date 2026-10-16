import type { Source } from '#lib/schema.js';
import type { Commune } from '#lib/types.js';

const GRAND_CONSEIL = 'les objets du Grand Conseil qui la nomment';

/**
 * `resume` de la couche Conseils : ce qu'elle montre d'une commune, pour la description de sa page, connu à la
 * construction. Le conseil communal d'une commune est la source à bloc `conseil` dont la Couverture déclarée la
 * nomme ; ce qu'il donne décide de la forme. Toutes les communes ont « Au Grand Conseil ».
 */
export function resumeConseils(sources: readonly Source[]): (commune: Commune) => string {
	return (commune) => {
		const conseil = sources.find((s) => {
			const communes = s.couverture?.communes;
			return s.conseil && Array.isArray(communes) && communes.includes(commune.bfs);
		})?.conseil;
		if (!conseil) return GRAND_CONSEIL;
		const objets = conseil.donne.includes('objets');
		const seances = conseil.donne.includes('seances');
		const donne = objets && seances ? 'les objets et les séances' : seances ? 'les séances' : 'les objets';
		return `${donne} de son Conseil communal, et ${GRAND_CONSEIL}`;
	};
}
