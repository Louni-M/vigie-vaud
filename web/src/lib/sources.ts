// Déclaration des sources (`sources.json` à la racine du dépôt), importée à la construction. Toutes les
// attributions affichées en viennent ; la construction échoue si le fichier est invalide (scripts/verifier-sources.ts).
import fichier from '../../../sources.json';
import type { Conseil, DonneeConseil, FichierSources, Source, VoieAcces } from './schema';

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
	cron: 'la source est relevée par le cron et publiée dans le dépôt de données (les conseils : une fois par jour)',
	worker: 'la source passe par un relais',
	preparee: 'la source est transformée une fois en fichier, publié avec le site'
};

/** Ce que donne un conseil, en toutes lettres : « objets et séances », « séances seulement » ou « objets seulement ». */
export function libelleDonne(conseil: { donne: readonly DonneeConseil[] }): string {
	const objets = conseil.donne.includes('objets');
	const seances = conseil.donne.includes('seances');
	return objets && seances ? 'objets et séances' : seances ? 'séances seulement' : 'objets seulement';
}

/** Clé du conseil dans le dépôt de données : `body_key` en minuscules (`vd`, `5586`), comme `Conseil.cle` du cron. */
export const cleConseil = (conseil: Conseil) => conseil.body_key.toLowerCase();

/** N° OFS de la commune d'un conseil communal (`body_key` numérique) ; `null` pour le Grand Conseil. */
export const communeDuConseil = (conseil: Conseil) => (/^\d+$/.test(conseil.body_key) ? Number(conseil.body_key) : null);

/**
 * Nom du conseil, tiré du nom de sa source : sans la mention finale entre parenthèses, l'apostrophe typographique
 * (« Conseil communal d’Yverdon-les-Bains »). La même règle que `nom_du_conseil` du cron, qui écrit le nom de l'index.
 */
export const nomDuConseil = (nomSource: string) => nomSource.replace(/\s*\([^()]*\)$/, '').replace(/'/g, '’');

/** Un conseil couvert : sa source et ce qu'il donne. */
export interface ConseilCouvert {
	source: Source & { conseil: Conseil };
	donne: string;
}

/** Les conseils couverts, tirés des sources qui ont un bloc `conseil`, dans l'ordre de `sources.json`. */
export function listerConseils(sources: readonly Source[]): ConseilCouvert[] {
	return sources.flatMap((s) => (s.conseil ? [{ source: { ...s, conseil: s.conseil }, donne: libelleDonne(s.conseil) }] : []));
}

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
