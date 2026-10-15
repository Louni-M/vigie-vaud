// Déclaration des sources (`sources.json` à la racine du dépôt), importée à la construction. Toutes les
// attributions affichées en viennent ; la construction échoue si le fichier est invalide (scripts/verifier-sources.ts).
import fichier from '../../../sources.json';
import type { FichierSources, Source } from './schema';

export const SOURCES: readonly Source[] = (fichier as FichierSources).sources;

/** La source déclarée sous cet identifiant. */
export function source(id: string): Source {
	const s = SOURCES.find((s) => s.id === id);
	if (!s) throw new Error(`Source inconnue dans sources.json : ${id}`);
	return s;
}

const echapper = (texte: string) =>
	texte.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

/** Attribution d'une source en HTML (lien vers la source), pour le contrôle d'attribution de la carte. */
export function attributionHtml(s: Source): string {
	const { texte, lien } = s.attribution;
	return `<a href="${echapper(lien)}" target="_blank" rel="noopener">${echapper(texte)}</a>`;
}
