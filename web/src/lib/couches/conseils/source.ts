// Ce que l'onglet Conseil et les fiches disent de la source d'un conseil, lu dans `sources.json` : le pied de la
// fiche d'un Objet ou d'une Séance, et la note de niveau sous le nom du conseil (spec de J3, « Couche Conseils et
// onglet Conseil », « Fiches »). Rien n'y est écrit en dur pour OpenParlData.
import { RAISONS } from '#lib/couverture.js';
import { deCommune } from '#lib/labels.js';
import type { MessageNonCouvert } from '#lib/registre/types.js';
import type { DonneeConseil, Objet, Source } from '#lib/schema.js';
import { SOURCES } from '#lib/sources.js';
import type { Commune } from '#lib/types.js';
import { sourceDuConseil } from './cles.js';

/** Un texte et son lien. */
export interface TexteLie {
	texte: string;
	lien: string;
}

/** « Commune de Préverenges » → « commune de Préverenges » : l'attribution reprise au milieu d'une phrase. */
const enMinuscule = (texte: string) => texte.charAt(0).toLowerCase() + texte.slice(1);

/** « Source : », avec l'espace insécable de la typographie française avant les deux-points. */
const SOURCE = 'Source\u00a0: ';

/**
 * Le pied de la fiche d'un élément du conseil (`vd`, `5643`), tiré de l'attribution de sa source, pour tous les
 * conseils : « Source : site de la commune de Préverenges » pour une commune scrapée, « Source : OpenParlData.ch »
 * pour OpenParlData (dont l'attribution s'écrit « Source: OpenParlData.ch »), avec son lien. `null` pour un conseil
 * que `sources` ne déclare pas.
 */
export function piedDeFiche(conseil: string, sources: readonly Source[] = SOURCES): TexteLie | null {
	const source = sourceDuConseil(conseil, sources);
	if (!source) return null;
	const { texte, lien } = source.attribution;
	const nom = source.site ? `site de la ${enMinuscule(texte)}` : texte.replace(/^Source\s*:\s*/, '');
	return { texte: SOURCE + nom, lien };
}

/** La note de niveau : « Séances seulement : les objets sont sur le site de la commune › », la suite en lien. */
export interface NoteDeNiveau {
	niveau: string;
	suite: string;
	/** La page de liste des Séances d'une commune scrapée, ou la page du conseil (Yverdon) ; `null` sans l'une ni l'autre. */
	lien: string | null;
}

/**
 * La note sous le nom du conseil, seulement s'il manque quelque chose : un conseil qui ne donne que ses Séances,
 * scrapé ou non (Yverdon), a ses objets sur le site de sa commune ; une commune scrapée en séances et préavis, ses
 * autres objets. `null` pour un conseil qui donne ses objets.
 */
export function noteDeNiveau(source: Source): NoteDeNiveau | null {
	const donne: readonly DonneeConseil[] = source.conseil?.donne ?? [];
	if (donne.includes('objets') || !donne.includes('seances')) return null;
	const lien = source.site?.seances ?? source.conseil?.page ?? null;
	if (donne.includes('preavis'))
		return { niveau: 'Séances et préavis', suite: 'les autres objets sont sur le site de la commune ›', lien };
	return { niveau: 'Séances seulement', suite: 'les objets sont sur le site de la commune ›', lien };
}

/**
 * La mention de la fiche d'un Objet d'une commune scrapée qui n'a ni statut ni auteur·e : le site de la commune ne
 * les publie pas (un préavis n'est pas d'office de la Municipalité, ni en attente). `null` pour un Objet qui a l'un
 * ou l'autre, ou d'un conseil sans site (OpenParlData).
 */
export function mentionNonPublies(
	conseil: string,
	objet: Pick<Objet, 'statut' | 'contributeurs'>,
	sources: readonly Source[] = SOURCES
): string | null {
	if (!sourceDuConseil(conseil, sources)?.site || objet.statut || objet.contributeurs.length) return null;
	return 'Statut et auteur·e·s : non publiés par le site de la commune';
}

/**
 * Les sources de la couche Conseils, dans l'ordre de `sources.json` : chaque source à bloc `conseil`, et chaque
 * commune non couverte d'une plateforme retenue (bloc `site` sans conseil), pour que sa raison soit dans la cellule
 * de la Couverture. Ajouter une commune, c'est ajouter son entrée à `sources.json`.
 */
export const sourcesDeLaCouche = (sources: readonly Source[] = SOURCES) =>
	sources.filter((s) => s.conseil || s.site).map((s) => s.id);

/**
 * Ce qui suit « Non couvert : » en tête de l'onglet Conseil d'une commune sans conseil couvert. Commune d'une
 * plateforme retenue déclarée non couverte (une source à bloc `site` en mode `non_couvert`) : la phrase de sa raison
 * et un lien vers la page du conseil, celui de l'attribution. Hors de J3 : une phrase neutre, sans lien.
 */
export function nonCouvertConseils(
	commune: Pick<Commune, 'bfs' | 'nom'>,
	sources: readonly Source[] = SOURCES
): MessageNonCouvert {
	const declaree = sources.find(
		({ site, couverture: c }) =>
			site && c?.mode === 'non_couvert' && Array.isArray(c.communes) && c.communes.includes(commune.bfs)
	);
	const raison = declaree?.couverture?.raison;
	if (!declaree || !raison) return { texte: 'Vigie Vaud ne lit pas encore le site de cette commune.' };
	return {
		texte: RAISONS[raison].onglet(deCommune(commune.nom)),
		lien: { texte: 'Le conseil sur le site de la commune ›', url: declaree.attribution.lien }
	};
}
