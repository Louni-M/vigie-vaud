import { limitesDe } from '#lib/couverture.js';
import type { Source } from '#lib/schema.js';
import { source } from '#lib/sources.js';
import type { Restriction } from './donnees.svelte.js';
import { echeance, ligneHoraires, periode } from './horaires.js';
import type { Passage } from './rattachement.js';
import { SORTES } from './sortes.js';

/**
 * Ce que montrent l'onglet Routes de la fiche commune et la carte d'une restriction (partagée par l'onglet, la
 * liste du volet et l'aperçu sur téléphone). Fonctions pures.
 */

/** L'encadré en tête de l'onglet : « La DGMR publie {limites}. », le texte venant de `sources.json`. */
export function encadreLimites(source: Pick<Source, 'nom_court' | 'limites'>): string | null {
	const limites = limitesDe(source);
	return limites ? `La ${source.nom_court} publie ${limites}.` : null;
}

/**
 * Ordre des listes de restrictions (onglet, volet) : l'en cours d'abord, fin la plus proche en tête, puis l'à venir
 * par début ; à égalité, par `OBJECTID`.
 */
export function ordreListe(a: Restriction, b: Restriction): number {
	if (a.etat !== b.etat) return a.etat === 'en_cours' ? -1 : 1;
	const [x, y] = a.etat === 'en_cours' ? [a.dateFin, b.dateFin] : [a.dateDebut, b.dateDebut];
	return x - y || a.id - b.id;
}

/** Les restrictions rattachées à la commune, en cours et à venir, chacune dans l'ordre des listes. */
export function sectionsDeLaCommune(
	restrictions: readonly Restriction[],
	slug: string
): { enCours: Restriction[]; aVenir: Restriction[] } {
	const ici = restrictions.filter((r) => r.communes?.some((p) => p.commune.slug === slug)).sort(ordreListe);
	return { enCours: ici.filter((r) => r.etat === 'en_cours'), aVenir: ici.filter((r) => r.etat === 'a_venir') };
}

/** « 770 m » (à 10 m près), « 2,3 km ». */
export const longueurTexte = (m: number) =>
	m < 995 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`;

/** « Pully », « Lutry, Pully », « Lutry, Pully et 3 autres ». */
export function communesTexte(passages: readonly Passage[], max = 2): string {
	const noms = passages.slice(0, max).map((p) => p.commune.nom).join(', ');
	const autres = passages.length - max;
	return autres > 0 ? `${noms} et ${autres} ${autres > 1 ? 'autres' : 'autre'}` : noms;
}

/** Ce que montre la carte d'une restriction. */
export interface CarteRestriction {
	/** La sorte telle que publiée (« Fermeture », ou une valeur inconnue comme « Manifestation »). */
	sorte: string;
	couleur: string;
	/** Une déviation : son trait est en tirets, comme sur la carte. */
	tirets: boolean;
	aVenir: boolean;
	/** Les communes, de la plus grande longueur parcourue à la plus petite ; `null` avant le rattachement. */
	communes: string | null;
	/** Nom court de la source (« DGMR »). */
	source: string;
	periode: string;
	echeance: string;
	/** La plage quotidienne (« La nuit seulement, de 19 h 30 à 5 h 30 »), seulement quand `HEURE_*` la donnent. */
	plage: string | null;
	remarque: string | null;
	/** « 770 m dans la commune, sur 2 communes », dans l'onglet d'une commune parmi plusieurs traversées. */
	dansLaCommune: string | null;
}

/**
 * La carte d'une restriction, vue depuis `commune` (slug) dans un onglet, ou sans commune dans le volet et
 * l'aperçu. `aujourdhui` (AAAA-MM-JJ à Lausanne) date l'échéance.
 */
export function carteRestriction(r: Restriction, { aujourdhui, commune }: { aujourdhui: string; commune?: string }): CarteRestriction {
	const ici = commune && r.communes && r.communes.length > 1 ? r.communes.find((p) => p.commune.slug === commune) : undefined;
	return {
		sorte: r.libelleSorte,
		couleur: SORTES[r.sorte].couleur,
		tirets: r.sorte === 'deviation',
		aVenir: r.etat === 'a_venir',
		communes: r.communes ? communesTexte(r.communes) : null,
		source: source('dgmr-restrictions').nom_court,
		periode: periode(r),
		echeance: echeance(r, aujourdhui),
		plage: r.heureDebut && r.heureFin ? ligneHoraires(r) : null,
		remarque: r.remarque,
		dansLaCommune: ici ? `${longueurTexte(ici.metres)} dans la commune, sur ${r.communes!.length} communes` : null
	};
}
