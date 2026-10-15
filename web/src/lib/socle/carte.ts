import type { Map as MlMap } from 'maplibre-gl';

/**
 * Retire de la carte du socle les calques, puis les sources, d'un composant qui se démonte. La carte a pu être
 * détruite avant lui (fin de la coquille) : il n'y a alors rien à retirer. Ses écouteurs, eux, se retirent
 * toujours sans risque (`map.off`).
 */
export function retirerDeLaCarte(map: MlMap, calques: readonly string[], sources: readonly string[]): void {
	if (!map.style) return;
	for (const id of calques) map.removeLayer(id);
	for (const id of sources) map.removeSource(id);
}
