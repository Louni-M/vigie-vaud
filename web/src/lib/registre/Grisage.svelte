<script lang="ts">
	/*
	 * Grisage de la carte : les communes que la couche du volet ouvert (bureau) ou de « Voir sur la carte »
	 * (téléphone) ne couvre pas sont voilées de gris, sous les calques de toutes les couches. La règle est dans la
	 * Couverture (`grisees`) ; ce composant ne fait que dessiner. Les limites des communes ne sont chargées qu'au premier grisage (en J1, à
	 * l'ouverture du volet Conseils, qui grise toutes les communes sauf Lausanne et Yverdon).
	 */
	import { untrack } from 'svelte';
	import type { GeoJSONSource, GeoJSONSourceSpecification, Map as MlMap } from 'maplibre-gl';
	import { retirerDeLaCarte } from '#lib/socle/carte.js';
	import { getLimites } from '#lib/socle/communes.js';

	let { map, sous, grisees }: { map: MlMap; sous: string; grisees: readonly number[] } = $props();

	const CALQUE = 'grisage';

	function donnees(limites: Awaited<ReturnType<typeof getLimites>>, bfs: readonly number[]) {
		return {
			type: 'FeatureCollection',
			features: bfs.map((n) => ({
				type: 'Feature',
				geometry: { type: 'MultiPolygon', coordinates: limites[n] ?? [] },
				properties: { bfs: n }
			}))
		} as GeoJSONSourceSpecification['data'];
	}

	// Calque posé vide dès que la carte est prête, avant que les couches n'ajoutent les leurs sous leur calque
	// d'ancrage : il reste ainsi sous toutes les couches. Il voile le fond, pas les éléments.
	const vide: GeoJSONSourceSpecification['data'] = { type: 'FeatureCollection', features: [] };
	untrack(() => {
		map.addSource(CALQUE, { type: 'geojson', data: vide });
		map.addLayer(
			{ id: CALQUE, type: 'fill', source: CALQUE, paint: { 'fill-color': '#5b6170', 'fill-opacity': 0.45 } },
			sous
		);
	});
	const source = untrack(() => map.getSource(CALQUE) as GeoJSONSource);

	$effect(() => {
		const bfs = grisees;
		if (!bfs.length) {
			source.setData(vide);
			return;
		}
		let abandonne = false;
		getLimites(fetch).then(
			(limites) => {
				if (!abandonne) source.setData(donnees(limites, bfs));
			},
			() => {}
		);
		return () => {
			abandonne = true;
		};
	});

	$effect(() => () => retirerDeLaCarte(map, [CALQUE], [CALQUE]));
</script>
