import type { Source } from '#lib/schema.js';
import { niveauDe } from '#lib/sources.js';
import type { Commune } from '#lib/types.js';

const GRAND_CONSEIL = 'les objets du Grand Conseil qui la nomment';

/**
 * `resume` de la couche Conseils : ce qu'elle montre d'une commune, pour la description de sa page, connu à la
 * construction. Le conseil d'une commune est la source à bloc `conseil` dont la Couverture déclarée la nomme ; ce
 * qu'il donne décide de la forme, et le nom de sa source dit s'il est communal ou général. Toutes les communes ont « Au Grand Conseil ».
 */
export function resumeConseils(sources: readonly Source[]): (commune: Commune) => string {
	return (commune) => {
		const source = sources.find((s) => {
			const communes = s.couverture?.communes;
			return s.conseil && Array.isArray(communes) && communes.includes(commune.bfs);
		});
		const conseil = source?.conseil;
		if (!source || !conseil) return GRAND_CONSEIL;
		const donne = niveauDe(conseil)?.resume ?? (conseil.donne.includes('preavis') ? 'les préavis' : 'les objets');
		// Le nom du conseil vient de sa source : « Conseil général de Ropraz (site de la commune) ».
		const nom = /^Conseil général\b/.test(source.nom) ? 'Conseil général' : 'Conseil communal';
		return `${donne} de son ${nom}, et ${GRAND_CONSEIL}`;
	};
}
