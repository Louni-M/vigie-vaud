import type { Emprise } from '#lib/types.js';

/** Ordonnée de Mercator d'une latitude (degrés), celle de la carte : la symétrie se fait à l'écran, pas en degrés. */
const versY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
const versLat = (y: number) => (Math.atan(Math.exp(y)) * 360) / Math.PI - 90;

/**
 * L'emprise qui contient `cadre` et dont `centre` [lon, lat] est le milieu : cadrée, elle montre toute la commune avec
 * son hôtel de ville au centre de la vue. Chaque côté s'étend jusqu'à l'écart le plus grand entre le centre et un bord
 * de `cadre`.
 */
export function cadreAutourDe(cadre: Emprise, [lon, lat]: [number, number]): Emprise {
	const [ouest, sud, est, nord] = cadre;
	const dx = Math.max(lon - ouest, est - lon, 0);
	const y = versY(lat);
	const dy = Math.max(y - versY(sud), versY(nord) - y, 0);
	return [lon - dx, versLat(y - dy), lon + dx, versLat(y + dy)];
}
