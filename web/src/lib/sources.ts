// Déclaration des sources (`sources.json` à la racine du dépôt), importée à la construction. Toutes les
// attributions affichées en viennent ; la construction échoue si le fichier est invalide (scripts/verifier-sources.ts).
import fichier from '../../../sources.json';
import type { Conseil, DonneeConseil, FichierSources, Plateforme, Source, VoieAcces } from './schema';

export const SOURCES: readonly Source[] = (fichier as FichierSources).sources;

/** Les plateformes retenues, que citent les blocs `site` des sources communales. */
export const PLATEFORMES: readonly Plateforme[] = (fichier as FichierSources).plateformes ?? [];

/** La source déclarée sous cet identifiant. */
export function source(id: string): Source {
	const s = SOURCES.find((s) => s.id === id);
	if (!s) throw new Error(`Source inconnue dans sources.json : ${id}`);
	return s;
}

const VOIES: Record<VoieAcces, string> = { direct: 'Direct', cron: 'Cron', worker: 'Worker', preparee: 'Préparée' };

/** Libellé de la voie d'accès d'une source : « Direct », « Cron », « Worker » ou « Préparée ». */
export const libelleVoie = (s: { voie_acces: VoieAcces }) => VOIES[s.voie_acces];

/** Ce que veut dire chaque voie d'accès, pour le lecteur (glossaire de `CONTEXT.md`). */
export const SENS_VOIES: Record<VoieAcces, string> = {
	direct: 'votre navigateur interroge la source à chaque visite',
	cron: 'la source est relevée par le cron et publiée dans le dépôt de données (les conseils : une fois par jour)',
	worker: 'la source passe par un relais',
	preparee: 'la source est transformée une fois en fichier, publié avec le site'
};

/**
 * Ce que donne un conseil, en toutes lettres, c'est-à-dire son niveau : « objets et séances », « séances et
 * préavis », « séances seulement » ; « objets seulement » ou « préavis seulement » sans ses Séances.
 */
export function libelleDonne(conseil: { donne: readonly DonneeConseil[] }): string {
	const objets = conseil.donne.includes('objets') ? 'objets' : conseil.donne.includes('preavis') ? 'préavis' : null;
	const seances = conseil.donne.includes('seances');
	if (objets && seances) return objets === 'objets' ? 'objets et séances' : 'séances et préavis';
	return seances ? 'séances seulement' : `${objets ?? 'objets'} seulement`;
}

/** Le conseil donne-t-il des Objets, tous (`objets`) ou ses préavis seulement (`preavis`) ? */
export const donneDesObjets = (conseil: { donne: readonly DonneeConseil[] }) =>
	conseil.donne.includes('objets') || conseil.donne.includes('preavis');

/** Clé du conseil dans le dépôt de données : `body_key` en minuscules (`vd`, `5586`), comme `Conseil.cle` du cron. */
export const cleConseil = (conseil: Conseil) => conseil.body_key.toLowerCase();

/**
 * Clé, dans le dépôt de données, du conseil que donne la source : celle de son bloc `conseil` ; pour une commune
 * scrapée passée non couverte, le n° OFS de sa commune, sous lequel son archive reste en ligne, sans import (récit 33
 * de la spec de J3) ; `null` pour une source sans conseil.
 */
export function cleDeLaSource(source: Source): string | null {
	if (source.conseil) return cleConseil(source.conseil);
	const c = source.couverture;
	if (!source.site || c?.mode !== 'non_couvert' || c.communes === 'canton') return null;
	return String(c.communes[0]);
}

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

/** Les communes lues sur leur site, pour À propos : leur nombre, puis par plateforme. */
export interface SitesLus {
	communes: number;
	/** Les plateformes qui ont au moins une commune couverte, dans l'ordre de la section `plateformes`. */
	plateformes: { nom: string; communes: number }[];
}

/**
 * « Conseils couverts » d'À propos : une ligne par conseil qui n'est pas lu sur un site (Grand Conseil, conseils
 * d'OpenParlData), puis le compte des communes lues sur leur site, par plateforme. Une commune non couverte (une source
 * communale sans bloc `conseil`) n'est pas comptée.
 */
export function conseilsCouverts(
	sources: readonly Source[],
	plateformes: readonly Plateforme[]
): { sources: ConseilCouvert[]; sites: SitesLus } {
	const conseils = listerConseils(sources);
	const lus = conseils.flatMap((c) => (c.source.site ? [c.source.site.plateforme] : []));
	const parPlateforme = plateformes
		.map((p) => ({ nom: p.nom, communes: lus.filter((id) => id === p.id).length }))
		.filter((p) => p.communes > 0);
	return {
		sources: conseils.filter((c) => !c.source.site),
		sites: { communes: lus.length, plateformes: parPlateforme }
	};
}

/**
 * La fin de « Conseils couverts » : « et 3 communes dont Vigie Vaud lit le site : i-web (2), Quicksite (1) » ;
 * `null` sans commune lue.
 */
export function phraseSitesLus(sites: SitesLus): string | null {
	if (sites.communes === 0) return null;
	const communes = `${sites.communes} commune${sites.communes > 1 ? 's' : ''}`;
	const parPlateforme = sites.plateformes.map((p) => `${p.nom} (${p.communes})`).join(', ');
	return `et ${communes} dont Vigie Vaud lit le site : ${parPlateforme}`;
}

/**
 * L'entrée « Sites des communes » de la liste Sources d'À propos, à la place d'une ligne par commune : les
 * plateformes de ses communes couvertes, la licence et la voie d'accès de leurs sources. L'attribution de chaque
 * commune reste au pied de ses fiches et dans la Couverture.
 */
export interface SitesDesCommunes {
	id: 'sites-des-communes';
	nom: 'Sites des communes';
	plateformes: string[];
	licence: string;
	voie_acces: VoieAcces;
}

/** Une entrée de la liste Sources d'À propos : une source, ou les sites des communes réunis. */
export type EntreeSources = Source | SitesDesCommunes;

/** Un groupe de la liste Sources d'À propos : une couche, ou « Carte et communes ». */
export interface GroupeSources {
	titre: string;
	sources: EntreeSources[];
}

/** Titre du groupe des sources qu'aucune couche ne déclare (fond de carte, recherche, limites, anciennes communes). */
export const CARTE_ET_COMMUNES = 'Carte et communes';

/**
 * Liste Sources d'À propos : un groupe par couche, dans l'ordre du registre, avec les sources qu'elle déclare,
 * puis « Carte et communes » avec toutes les autres, dans l'ordre de `sources.json`. Les sources communales (bloc
 * `site`), couvertes ou non, sont réunies en une seule entrée « Sites des communes », à la place de la première.
 */
export function grouperSources(
	couches: readonly { nom: string; sources: readonly string[] }[],
	sources: readonly Source[],
	plateformes: readonly Plateforme[] = PLATEFORMES
): GroupeSources[] {
	const parCouche = couches.map((c) => ({
		titre: c.nom,
		sources: sources.filter((s) => c.sources.includes(s.id))
	}));
	const declarees = new Set(couches.flatMap((c) => c.sources));
	const autres = { titre: CARTE_ET_COMMUNES, sources: sources.filter((s) => !declarees.has(s.id)) };
	const sites = sitesDesCommunes(sources, plateformes);
	let reunis = false;
	const groupes = [...parCouche, autres].map((g) => ({
		titre: g.titre,
		sources: g.sources.flatMap((s): EntreeSources[] => {
			if (!s.site || !sites) return [s];
			if (reunis) return [];
			reunis = true;
			return [sites];
		})
	}));
	return groupes.filter((g) => g.sources.length > 0);
}

/** L'entrée « Sites des communes », ou `null` sans source communale. */
function sitesDesCommunes(sources: readonly Source[], plateformes: readonly Plateforme[]): SitesDesCommunes | null {
	const communales = sources.filter((s) => s.site);
	if (communales.length === 0) return null;
	return {
		id: 'sites-des-communes',
		nom: 'Sites des communes',
		plateformes: conseilsCouverts(sources, plateformes).sites.plateformes.map((p) => p.nom),
		licence: communales[0].attribution.licence,
		voie_acces: communales[0].voie_acces
	};
}

const echapper = (texte: string) =>
	texte.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

/** Attribution d'une source en HTML (lien vers la source), pour le contrôle d'attribution de la carte. */
export function attributionHtml(s: Source): string {
	const { texte, lien } = s.attribution;
	return `<a href="${echapper(lien)}" target="_blank" rel="noopener">${echapper(texte)}</a>`;
}
