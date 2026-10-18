import type { Zone } from '#lib/types.js';
import { ordreListe } from './cartes.js';
import type { EtatRestriction, Restriction } from './donnees.svelte.js';
import { SORTES, type Sorte } from './sortes.js';
import type { Point } from './trace.js';

/**
 * Ce que montre le volet Routes : les puces qui filtrent la carte et la liste, et la liste des restrictions de la
 * zone visible. Fonctions pures.
 */

/** Les puces allumées du volet : les sortes et les états montrés. Elles ne vont pas dans l'adresse. */
export interface Filtres {
	sortes: readonly Sorte[];
	etats: readonly EtatRestriction[];
}

/** Toutes les puces allumées. */
export const FILTRES_INITIAUX: Filtres = {
	sortes: Object.keys(SORTES) as Sorte[],
	etats: ['en_cours', 'a_venir']
};

/**
 * Les puces des sortes, qui servent aussi de légende, dans l'ordre de la légende. « Autre » (une sorte que la DGMR
 * prévoit sans la publier à ce jour) n'apparaît que si une restriction chargée en est.
 */
export function sortesDesPuces(restrictions: readonly Restriction[]): Sorte[] {
	const avecAutre = restrictions.some((r) => r.sorte === 'autre');
	return (Object.keys(SORTES) as Sorte[]).filter((s) => s !== 'autre' || avecAutre);
}

/**
 * Le segment [a, b] coupe-t-il l'emprise, bords compris ? Découpage de Liang-Barsky : on cherche une portion du
 * segment, `t` entre 0 et 1, qui reste du bon côté des quatre bords.
 */
function segmentCoupe([ax, ay]: Point, [bx, by]: Point, [o, s, e, n]: Zone): boolean {
	const dx = bx - ax;
	const dy = by - ay;
	let t0 = 0;
	let t1 = 1;
	// Chaque bord, sous la forme p·t ≤ q.
	for (const [p, q] of [
		[-dx, ax - o],
		[dx, e - ax],
		[-dy, ay - s],
		[dy, n - ay]
	]) {
		if (p === 0) {
			if (q < 0) return false;
		} else {
			const t = q / p;
			if (p < 0) t0 = Math.max(t0, t);
			else t1 = Math.min(t1, t);
			if (t0 > t1) return false;
		}
	}
	return true;
}

/** Le tracé coupe-t-il l'emprise ? Un de ses segments au moins, ou un sommet isolé, y entre. */
function coupeLaZone(lignes: readonly Point[][], zone: Zone): boolean {
	return lignes.some((l) =>
		l.length === 1 ? segmentCoupe(l[0], l[0], zone) : l.some((p, i) => i > 0 && segmentCoupe(l[i - 1], p, zone))
	);
}

/**
 * La liste du volet : les restrictions que montrent les puces et dont le tracé coupe la zone visible (le milieu du
 * tracé peut être hors de la zone), en cours d'abord par fin la plus proche, puis à venir par jour de début. Rien
 * tant que la zone est inconnue.
 */
export function visibles(restrictions: readonly Restriction[], filtres: Filtres, zone: Zone | null): Restriction[] {
	if (!zone) return [];
	return restrictions
		.filter((r) => filtres.sortes.includes(r.sorte) && filtres.etats.includes(r.etat) && coupeLaZone(r.lignes, zone))
		.sort(ordreListe);
}
