import { dansLimites, type Limites } from '#lib/socle/communes.js';
import type { Commune } from '#lib/types.js';
import { lignesDe, metres, type Geometrie, type Point } from './trace.js';

/**
 * Rattachement par la position d'une restriction de circulation : les communes que son tracé parcourt, rangées par
 * longueur. Fonction pure, calculée dans le navigateur sur les limites des communes publiées avec le site.
 */

/** Une commune et ses limites ([polygone][anneau][point], trous compris). */
export interface CommuneLimitee {
	commune: Commune;
	limites: Limites;
}

/** Une commune traversée par une restriction, et les mètres que le tracé y parcourt. */
export interface Passage {
	commune: Commune;
	metres: number;
}

/** Longueur dès laquelle une commune compte : un tracé qui longe une limite n'y entre que de quelques mètres. */
export const SEUIL_METRES = 20;

type Emprise = [number, number, number, number];

function emprise(points: Iterable<number[]>): Emprise {
	let [w, s, e, n] = [Infinity, Infinity, -Infinity, -Infinity];
	for (const [x, y] of points) {
		w = Math.min(w, x);
		s = Math.min(s, y);
		e = Math.max(e, x);
		n = Math.max(n, y);
	}
	return [w, s, e, n];
}

/** Emprise des limites de chaque commune, calculée une fois. */
const emprises = new WeakMap<Limites, Emprise>();
function empriseDe(limites: Limites): Emprise {
	let e = emprises.get(limites);
	if (!e) emprises.set(limites, (e = emprise(limites.flat(2))));
	return e;
}

const disjointes = ([w1, s1, e1, n1]: Emprise, [w2, s2, e2, n2]: Emprise) => w1 > e2 || w2 > e1 || s1 > n2 || s2 > n1;

/** Fractions (0 à 1) du segment a→b où il coupe un bord des limites. */
function coupures(a: Point, b: Point, limites: Limites): number[] {
	const ts: number[] = [];
	const [rx, ry] = [b[0] - a[0], b[1] - a[1]];
	for (const polygone of limites)
		for (const anneau of polygone)
			for (let i = 1; i < anneau.length; i++) {
				const [px, py] = anneau[i - 1];
				const [sx, sy] = [anneau[i][0] - px, anneau[i][1] - py];
				const d = rx * sy - ry * sx;
				// Parallèles : le milieu des morceaux voisins dira de quel côté passe le tracé.
				if (d === 0) continue;
				const [qx, qy] = [px - a[0], py - a[1]];
				const t = (qx * sy - qy * sx) / d;
				const u = (qx * ry - qy * rx) / d;
				if (t > 0 && t < 1 && u >= 0 && u <= 1) ts.push(t);
			}
	return ts;
}

/** Mètres du segment a→b dans les limites : découpé à chaque bord, chaque morceau compté si son milieu y est. */
function metresDans(a: Point, b: Point, limites: Limites): number {
	const ts = [0, ...coupures(a, b, limites), 1].sort((x, y) => x - y);
	let dedans = 0;
	for (let i = 1; i < ts.length; i++) {
		const [t1, t2] = [ts[i - 1], ts[i]];
		if (t2 <= t1) continue;
		const t = (t1 + t2) / 2;
		if (dansLimites(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, limites)) dedans += t2 - t1;
	}
	return dedans * metres(a, b);
}

/**
 * Les communes que parcourt le tracé, de la plus grande longueur à la plus petite, avec leurs mètres. Une commune
 * compte dès 20 m parcourus ; si aucune ne les atteint, celle qui contient la plus grande part. La part hors de
 * toute commune (hors du canton) est ignorée ; un tracé qui n'entre dans aucune commune n'en a donc aucune.
 * `LineString` et `MultiLineString` ; communes trouées ou en plusieurs morceaux. Seul un filtre par emprise
 * écarte les communes lointaines : une restriction n'a que quelques centaines de sommets.
 */
export function rattacher(geometrie: Geometrie, communes: readonly CommuneLimitee[]): Passage[] {
	const lignes = lignesDe(geometrie);
	const candidates = communes
		.map((c) => ({ ...c, emprise: empriseDe(c.limites) }))
		.filter((c) => !disjointes(c.emprise, emprise(lignes.flat())));
	const parCommune = new Map<CommuneLimitee['commune'], number>();
	for (const l of lignes)
		for (let i = 1; i < l.length; i++) {
			const [a, b] = [l[i - 1], l[i]];
			const segment = emprise([a, b]);
			for (const c of candidates) {
				if (disjointes(c.emprise, segment)) continue;
				const m = metresDans(a, b, c.limites);
				if (m > 0) parCommune.set(c.commune, (parCommune.get(c.commune) ?? 0) + m);
			}
		}
	const passages = [...parCommune].map(([commune, m]) => ({ commune, metres: m }));
	passages.sort((x, y) => y.metres - x.metres);
	const retenus = passages.filter((p) => p.metres >= SEUIL_METRES);
	return retenus.length ? retenus : passages.slice(0, 1);
}
