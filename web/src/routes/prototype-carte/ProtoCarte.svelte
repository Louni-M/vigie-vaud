<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : carte avec les couches Permis et Hôtels de ville, et le marqueur du Grand Conseil.
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
	import type { Map as MlMap, GeoJSONSource, PaddingOptions, ExpressionSpecification } from 'maplibre-gl';
	import { asset } from '$app/paths';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import { GRAND_CONSEIL, hdv, type Proto } from './proto.svelte.js';

	/** `marge` : place occupée par les panneaux posés sur la carte, en px. */
	let { p, marge = { top: 0, right: 0, bottom: 0, left: 0 } }: { p: Proto; marge?: PaddingOptions } = $props();

	const CANTON: [number, number, number, number] = [5.9, 46.18, 7.25, 46.99];
	const STYLE = 'https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json';

	let container: HTMLDivElement;
	let map: MlMap | undefined = $state();
	let pret = $state(false);
	let limites: Record<string, number[][][][]> = {};

	const vide = { type: 'FeatureCollection' as const, features: [] };
	const couleur = [
		'match',
		['get', 'statut'],
		...STATUTS_ORDRE.flatMap((s) => [s, STATUTS[s].couleur]),
		STATUTS.autre.couleur
	] as unknown as ExpressionSpecification;

	const padding = (extra = 0) => ({
		top: (marge.top ?? 0) + extra,
		right: (marge.right ?? 0) + extra,
		bottom: (marge.bottom ?? 0) + extra,
		left: (marge.left ?? 0) + extra
	});

	onMount(() => {
		let fini = false;
		(async () => {
			const maplibregl = await import('maplibre-gl');
			if (fini) return;
			maplibregl.setWorkerUrl(workerUrl);
			const m = new maplibregl.Map({
				container,
				style: STYLE,
				bounds: CANTON,
				fitBoundsOptions: { padding: 20 },
				attributionControl: false,
				maxBounds: [4.5, 45.5, 8.5, 47.6]
			});
			m.addControl(new maplibregl.AttributionControl({ compact: true }));
			m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');

			fetch(asset('communes-limites.json'))
				.then((r) => r.json())
				.then((l) => (limites = l));

			m.on('load', () => {
				const police = (m.getStyle().layers.find((l) => l.type === 'symbol' && l.layout?.['text-font']) as
					| { layout: { 'text-font': string[] } }
					| undefined)?.layout['text-font'] ?? ['Frutiger Neue Regular'];

				m.addSource('commune-ouverte', { type: 'geojson', data: vide });
				m.addLayer({
					id: 'commune-fond',
					type: 'fill',
					source: 'commune-ouverte',
					paint: { 'fill-color': '#1f3a5f', 'fill-opacity': 0.06 }
				});
				m.addLayer({
					id: 'commune-ligne',
					type: 'line',
					source: 'commune-ouverte',
					paint: { 'line-color': '#1f3a5f', 'line-width': 2, 'line-dasharray': [3, 2] }
				});

				m.addSource('permis', { type: 'geojson', data: vide });
				m.addLayer({
					id: 'permis',
					type: 'circle',
					source: 'permis',
					paint: {
						'circle-color': couleur,
						'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 3, 13, 5, 17, 8],
						'circle-stroke-color': '#fff',
						'circle-stroke-width': 1,
						'circle-opacity': 1,
						'circle-stroke-opacity': 1,
						'circle-opacity-transition': { duration: 350 },
						'circle-stroke-opacity-transition': { duration: 350 }
					}
				});
				m.addSource('dossier', { type: 'geojson', data: vide });
				m.addLayer({
					id: 'dossier',
					type: 'circle',
					source: 'dossier',
					paint: { 'circle-radius': 13, 'circle-color': 'transparent', 'circle-stroke-color': '#1f6feb', 'circle-stroke-width': 3 }
				});

				// Hôtels de ville : couche permanente, dessinée au-dessus des autres (ticket #5).
				m.addSource('hdv', { type: 'geojson', data: vide });
				m.addLayer({
					id: 'hdv',
					type: 'circle',
					source: 'hdv',
					paint: {
						'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, ['case', ['get', 'ouverte'], 7, 3.5], 13, ['case', ['get', 'ouverte'], 11, 7]],
						'circle-color': ['case', ['get', 'ouverte'], '#ffb38a', '#1f3a5f'],
						'circle-stroke-color': ['case', ['get', 'ouverte'], '#1f3a5f', '#fff'],
						'circle-stroke-width': ['case', ['get', 'ouverte'], 3, 1.5]
					}
				});
				m.addLayer({
					id: 'hdv-nom',
					type: 'symbol',
					source: 'hdv',
					minzoom: 10.5,
					layout: {
						'text-field': ['get', 'nom'],
						'text-font': police,
						'text-size': 12,
						'text-offset': [0, 1.1],
						'text-anchor': 'top',
						'text-optional': true
					},
					paint: { 'text-color': '#1f3a5f', 'text-halo-color': '#fff', 'text-halo-width': 1.5 }
				});

				const gc = document.createElement('button');
				gc.className = 'proto-gc';
				gc.title = 'Grand Conseil (Parlement vaudois)';
				gc.innerHTML = '<span>⌂</span> Grand Conseil';
				gc.onclick = (e) => {
					e.stopPropagation();
					p.ouvrirGrandConseil();
				};
				new maplibregl.Marker({ element: gc, anchor: 'bottom' }).setLngLat(GRAND_CONSEIL).addTo(m);

				for (const id of ['hdv', 'permis']) {
					m.on('mouseenter', id, () => (m.getCanvas().style.cursor = 'pointer'));
					m.on('mouseleave', id, () => (m.getCanvas().style.cursor = ''));
				}
				m.on('click', (e) => {
					const [f] = m.queryRenderedFeatures(e.point, { layers: p.permis ? ['hdv', 'permis'] : ['hdv'] });
					if (!f) return;
					if (f.layer.id === 'hdv') {
						const c = p.communes.find((c) => c.slug === f.properties.slug);
						if (c) p.ouvrirCommune(c);
					} else {
						const d = p.actifs.find((d) => d.id === f.properties.id);
						if (d) p.ouvrirDossier(d);
					}
				});
				map = m;
				pret = true;
			});
		})();
		return () => {
			fini = true;
			map?.remove();
		};
	});

	// Couche Permis : données, filtres, et fondu à l'activation.
	$effect(() => {
		if (!pret || !map) return;
		const ds = p.actifs.filter((d) => p.statuts.includes(d.statut) && (!p.nature || d.nature === p.nature));
		(map.getSource('permis') as GeoJSONSource).setData({
			type: 'FeatureCollection',
			features: ds.map((d) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: [d.lon, d.lat] },
				properties: { id: d.id, statut: d.statut }
			}))
		});
	});
	$effect(() => {
		if (!pret || !map) return;
		const o = p.permis ? 1 : 0;
		map.setPaintProperty('permis', 'circle-opacity', o);
		map.setPaintProperty('permis', 'circle-stroke-opacity', o);
	});

	$effect(() => {
		if (!pret || !map) return;
		const ouverte = p.commune?.slug;
		(map.getSource('hdv') as GeoJSONSource).setData({
			type: 'FeatureCollection',
			features: p.communes.map((c) => ({
				type: 'Feature',
				geometry: { type: 'Point', coordinates: hdv(c) },
				properties: { slug: c.slug, nom: c.nom, ouverte: c.slug === ouverte }
			}))
		});
	});

	// Commune ouverte : contour, puis vol vers son hôtel de ville et cadrage sur ses limites.
	$effect(() => {
		if (!pret || !map) return;
		const c = p.commune;
		const l = c && limites[c.bfs];
		(map.getSource('commune-ouverte') as GeoJSONSource).setData(
			l ? { type: 'Feature', geometry: { type: 'MultiPolygon', coordinates: l }, properties: {} } : vide
		);
		if (!c || p.dossier) return;
		const cam = map.cameraForBounds(c.bbox, { padding: padding(30) });
		if (cam) map.flyTo({ ...cam, curve: 1.5, speed: 1.2, padding: { top: 0, right: 0, bottom: 0, left: 0 } });
	});

	$effect(() => {
		if (!pret || !map) return;
		const d = p.dossier;
		(map.getSource('dossier') as GeoJSONSource).setData(
			d ? { type: 'Feature', geometry: { type: 'Point', coordinates: [d.lon, d.lat] }, properties: {} } : vide
		);
		if (d) map.flyTo({ center: [d.lon, d.lat], zoom: Math.max(map.getZoom(), 16), padding: padding(), speed: 1.1 });
	});

	$effect(() => {
		if (!pret || !map || !p.gc) return;
		map.flyTo({ center: GRAND_CONSEIL, zoom: 16, padding: padding(), speed: 1.1 });
	});

	// Les panneaux changent de taille : la carte suit sans saut.
	$effect(() => {
		marge.top;
		marge.right;
		marge.bottom;
		marge.left;
		map?.resize();
	});

	export function vueCanton() {
		map?.fitBounds(CANTON, { padding: padding(20), duration: 900 });
	}
</script>

<div class="carte" bind:this={container}></div>

<style>
	.carte {
		position: absolute;
		inset: 0;
	}
	:global(.proto-gc) {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 8px;
		border: 2px solid #fff;
		border-radius: 999px;
		background: #7a1f2b;
		color: #fff;
		font: 600 12px system-ui, sans-serif;
		box-shadow: 0 2px 6px rgb(0 0 0 / 0.3);
		cursor: pointer;
	}
	:global(.proto-gc span) {
		font-size: 14px;
	}
</style>
