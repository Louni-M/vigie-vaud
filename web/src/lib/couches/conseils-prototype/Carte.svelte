<script lang="ts">
	// PROTOTYPE (ticket #45) : un point par commune rattachée à au moins un élément ; un clic ouvre le plus récent.
	import { onMount, untrack } from 'svelte';
	import type { MapLayerMouseEvent } from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { retirerDeLaCarte } from '#lib/socle/carte.js';
	import { ELEMENTS } from './donnees.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const ID = 'conseils-prototype';

	const parCommune = new Map<string, string>();
	for (const x of [...ELEMENTS].sort((a, b) => a.age - b.age))
		for (const s of x.communes) if (!parCommune.has(s)) parCommune.set(s, x.id);

	const communes = untrack(() => ctx.communes);
	map.addSource(ID, {
		type: 'geojson',
		data: {
			type: 'FeatureCollection',
			features: [...parCommune].flatMap(([slug, id]) => {
				const c = communes.find((c) => c.slug === slug);
				if (!c) return [];
				// Un peu à l'est de l'hôtel de ville, pour ne pas le cacher.
				return [{ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [c.hotel[0] + 0.004, c.hotel[1]] }, properties: { id, slug } }];
			})
		}
	});
	map.addLayer(
		{ id: ID, type: 'circle', source: ID, paint: { 'circle-color': '#7a3e9d', 'circle-radius': 7, 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 } },
		avant
	);

	$effect(() => {
		map.setLayoutProperty(ID, 'visibility', ctx.active ? 'visible' : 'none');
	});

	onMount(() => {
		const clic = (e: MapLayerMouseEvent) => {
			const f = e.features?.[0];
			if (f) ctx.ouvrir({ couche: 'conseils', element: f.properties.id, position: (f.geometry as unknown as { coordinates: [number, number] }).coordinates });
		};
		map.on('click', ID, clic);
		map.on('mouseenter', ID, () => (map.getCanvas().style.cursor = 'pointer'));
		map.on('mouseleave', ID, () => (map.getCanvas().style.cursor = ''));
		return () => {
			map.off('click', ID, clic);
			retirerDeLaCarte(map, [ID], [ID]);
		};
	});
</script>
