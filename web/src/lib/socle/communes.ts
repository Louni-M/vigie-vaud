import { asset } from '$app/paths';
import type { Commune } from '#lib/types.js';

/**
 * Index et limites des communes (swissBOUNDARIES3D, swisstopo, données ouvertes), produits par
 * pipeline/communes.py et hébergés avec le site : ce ne sont pas des données cantonales.
 */

type Fetch = typeof fetch;
/** Polygones d'une commune : [polygone][anneau][point] = [lon, lat]. */
export type Limites = number[][][][];

const cache = new Map<string, Promise<unknown>>();
function getJson<T>(f: Fetch, path: string): Promise<T> {
	let p = cache.get(path) as Promise<T> | undefined;
	if (!p) {
		p = f(asset(path as Parameters<typeof asset>[0])).then((r) => {
			if (!r.ok) throw new Error(`${path} : ${r.status}`);
			return r.json() as Promise<T>;
		});
		p.catch(() => cache.delete(path));
		cache.set(path, p);
	}
	return p;
}

export const getCommunes = (f: Fetch) => getJson<Commune[]>(f, 'communes.json');
/** Limites des communes, par n° OFS. */
export const getLimites = (f: Fetch) => getJson<Record<string, Limites>>(f, 'communes-limites.json');

function dansAnneau(lon: number, lat: number, anneau: number[][]): boolean {
	let dedans = false;
	for (let i = 0, j = anneau.length - 1; i < anneau.length; j = i++) {
		const [xi, yi] = anneau[i];
		const [xj, yj] = anneau[j];
		if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dedans = !dedans;
	}
	return dedans;
}

const dansLimites = (lon: number, lat: number, l: Limites) =>
	l.some(([ext, ...trous]) => dansAnneau(lon, lat, ext) && !trous.some((t) => dansAnneau(lon, lat, t)));

/** Distance approximative (degrés, latitude corrigée) d'un point au contour le plus proche. */
function distance(lon: number, lat: number, l: Limites): number {
	const k = Math.cos((lat * Math.PI) / 180);
	let min = Infinity;
	for (const poly of l)
		for (const anneau of poly)
			for (let i = 1; i < anneau.length; i++) {
				const [ax, ay] = anneau[i - 1];
				const [bx, by] = anneau[i];
				const dx = (bx - ax) * k;
				const dy = by - ay;
				const px = (lon - ax) * k;
				const py = lat - ay;
				const t = Math.max(0, Math.min(1, (px * dx + py * dy) / (dx * dx + dy * dy || 1)));
				min = Math.min(min, Math.hypot(px - t * dx, py - t * dy));
			}
	return min;
}

export interface Rattachement {
	communeDe(lon: number, lat: number): Commune;
	limites(c: Commune): Limites;
}

/**
 * Rattache un point à sa commune actuelle, comme pipeline/fetch.py : commune qui le contient,
 * sinon la plus proche (lacs, imprécisions).
 */
export const getRattachement = (f: Fetch): Promise<Rattachement> =>
	(cache.get('rattachement') as Promise<Rattachement>) ??
	(() => {
		const p = Promise.all([getCommunes(f), getLimites(f)]).then(([communes, limites]) => {
			const parBfs = communes.map((c) => ({ c, l: limites[c.bfs] ?? [] }));
			return {
				communeDe(lon: number, lat: number) {
					const candidates = parBfs.filter(
						({ c: { bbox: [w, s, e, n] } }) => lon >= w && lon <= e && lat >= s && lat <= n
					);
					const ici = candidates.find(({ l }) => dansLimites(lon, lat, l));
					if (ici) return ici.c;
					// Rare (quelques dossiers sur un lac) : on peut se permettre de parcourir toutes les communes.
					const proches = parBfs.map((x) => ({ c: x.c, d: distance(lon, lat, x.l) }));
					return proches.reduce((a, b) => (b.d < a.d ? b : a)).c;
				},
				limites: (c: Commune) => limites[c.bfs] ?? []
			};
		});
		p.catch(() => cache.delete('rattachement'));
		cache.set('rattachement', p);
		return p;
	})();
