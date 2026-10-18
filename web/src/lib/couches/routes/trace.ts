/**
 * Géométrie du tracé d'une restriction de circulation, en WGS84 : ses lignes, sa longueur et son milieu.
 * Fonctions pures. Les distances sont équirectangulaires : à l'échelle d'un tracé vaudois (quelques kilomètres),
 * l'écart à la distance géodésique reste bien en deçà du mètre.
 */

/** [longitude, latitude]. */
export type Point = [number, number];

/** Géométrie d'une restriction telle que la DGMR la publie en GeoJSON. */
export type Geometrie = { type: 'LineString'; coordinates: Point[] } | { type: 'MultiLineString'; coordinates: Point[][] };

/** Rayon terrestre moyen, en mètres. */
const R = 6_371_000;
const RAD = Math.PI / 180;

/** Les lignes d'une géométrie : une seule pour une `LineString`, chacun de ses morceaux pour une `MultiLineString`. */
export const lignesDe = (g: Geometrie): Point[][] => (g.type === 'LineString' ? [g.coordinates] : g.coordinates);

/** Distance en mètres entre deux points proches. */
export function metres([lonA, latA]: Point, [lonB, latB]: Point): number {
	const k = Math.cos(((latA + latB) / 2) * RAD);
	return Math.hypot((lonB - lonA) * k, latB - latA) * RAD * R;
}

/** Longueur du tracé en mètres : ses morceaux bout à bout, sans les sauts de l'un à l'autre. */
export function longueur(lignes: Point[][]): number {
	let total = 0;
	for (const l of lignes) for (let i = 1; i < l.length; i++) total += metres(l[i - 1], l[i]);
	return total;
}

/**
 * Le point à mi-longueur du tracé, `MultiLineString` comprise (les morceaux mis bout à bout, dans leur ordre).
 * C'est le point de la carte sous le zoom 11, la position de la restriction et celle de son entrée dans le fil.
 */
export function milieu(lignes: Point[][]): Point {
	let reste = longueur(lignes) / 2;
	for (const l of lignes)
		for (let i = 1; i < l.length; i++) {
			const [a, b] = [l[i - 1], l[i]];
			const d = metres(a, b);
			if (d > 0 && d >= reste) {
				const t = reste / d;
				return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
			}
			reste -= d;
		}
	return lignes[0][0];
}
