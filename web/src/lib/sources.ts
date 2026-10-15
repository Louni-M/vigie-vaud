// Déclaration des sources (`sources.json` à la racine du dépôt), importée à la construction. Toutes les
// attributions affichées en viennent ; la construction échoue si le fichier est invalide (scripts/verifier-sources.ts).
import fichier from '../../../sources.json';
import type { FichierSources, Source, VoieAcces } from './schema';

export const SOURCES: readonly Source[] = (fichier as FichierSources).sources;

/** La source déclarée sous cet identifiant. */
export function source(id: string): Source {
	const s = SOURCES.find((s) => s.id === id);
	if (!s) throw new Error(`Source inconnue dans sources.json : ${id}`);
	return s;
}

const VOIES: Record<VoieAcces, string> = { direct: 'Direct', cron: 'Cron', worker: 'Worker', preparee: 'Préparée' };

/** Libellé de la voie d'accès d'une source : « Direct », « Cron », « Worker » ou « Préparée ». */
export const libelleVoie = (s: Source) => VOIES[s.voie_acces];

/** Ce que veut dire chaque voie d'accès, pour le lecteur (glossaire de `CONTEXT.md`). */
export const SENS_VOIES: Record<VoieAcces, string> = {
	direct: 'votre navigateur interroge la source à chaque visite',
	cron: 'la source est relevée toutes les 30 minutes par le cron et publiée dans le dépôt de données',
	worker: 'la source passe par un relais',
	preparee: 'la source est transformée une fois en fichier, publié avec le site'
};

/** Un groupe de la liste Sources d'À propos : une couche, ou « Carte et communes ». */
export interface GroupeSources {
	titre: string;
	sources: Source[];
}

/** Titre du groupe des sources qu'aucune couche ne déclare (fond de carte, recherche, limites, anciennes communes). */
export const CARTE_ET_COMMUNES = 'Carte et communes';

/**
 * Liste Sources d'À propos : un groupe par couche, dans l'ordre du registre, avec les sources qu'elle déclare,
 * puis « Carte et communes » avec toutes les autres, dans l'ordre de `sources.json`.
 */
export function grouperSources(
	couches: readonly { nom: string; sources: readonly string[] }[],
	sources: readonly Source[]
): GroupeSources[] {
	const parCouche = couches.map((c) => ({
		titre: c.nom,
		sources: sources.filter((s) => c.sources.includes(s.id))
	}));
	const declarees = new Set(couches.flatMap((c) => c.sources));
	const autres = { titre: CARTE_ET_COMMUNES, sources: sources.filter((s) => !declarees.has(s.id)) };
	return [...parCouche, autres].filter((g) => g.sources.length > 0);
}

const echapper = (texte: string) =>
	texte.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

/** Attribution d'une source en HTML (lien vers la source), pour le contrôle d'attribution de la carte. */
export function attributionHtml(s: Source): string {
	const { texte, lien } = s.attribution;
	return `<a href="${echapper(lien)}" target="_blank" rel="noopener">${echapper(texte)}</a>`;
}
