<script lang="ts">
	/*
	 * PROTOTYPE : carte de la couche Routes, dessinée selon la variante (`?variant=`), et la barre flottante qui
	 * passe d'une variante à l'autre. A : couleur par sorte, points au petit zoom. B : la restriction principale de
	 * chaque groupe, ses déviations au survol ou à l'ouverture, un marqueur par groupe au petit zoom. C : couleur par
	 * échéance, halo au petit zoom.
	 */
	import { onMount, untrack } from 'svelte';
	import type { ExpressionSpecification, GeoJSONSource, LayerSpecification, MapMouseEvent } from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { retirerDeLaCarte } from '#lib/socle/carte.js';
	import Switcher from './Switcher.svelte';
	import {
		aujourdhui,
		joursEntre,
		retenue,
		routes,
		SORTES,
		SORTES_ORDRE,
		type Restriction,
		type Variante
	} from './donnees.svelte.js';
	import type { Parametres } from './index.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const LIGNES = 'routes-proto-lignes';
	const POINTS = 'routes-proto-points';
	const SELECTION = 'routes-proto-selection';
	const SOURCES = [LIGNES, POINTS, SELECTION];

	const variante = $derived(ctx.parametres.variant);

	const parSorte = [
		'match',
		['get', 'sorte'],
		...SORTES_ORDRE.flatMap((s) => [s, SORTES[s].couleur]),
		'#868e96'
	] as unknown as ExpressionSpecification;
	const parEcheance = [
		'match',
		['get', 'echeance'],
		'en-cours', '#c92a2a',
		'semaine', '#f08c00',
		'#868e96'
	] as unknown as ExpressionSpecification;

	function echeance(r: Restriction) {
		if (r.quand === 'en-cours') return 'en-cours';
		return joursEntre(aujourdhui(), r.debut.jour) <= 7 ? 'semaine' : 'plus-tard';
	}

	const vide = { type: 'FeatureCollection' as const, features: [] };
	function lignes(rs: Restriction[]) {
		return {
			type: 'FeatureCollection' as const,
			features: rs.map((r) => ({
				type: 'Feature' as const,
				id: r.id,
				geometry: { type: 'MultiLineString' as const, coordinates: r.lignes },
				properties: {
					id: r.id,
					sorte: r.sorte,
					quand: r.quand,
					echeance: echeance(r),
					groupe: r.groupe,
					principale: routes.groupeDe(r).principale.id === r.id
				}
			}))
		};
	}
	function points(rs: Restriction[], v: Variante) {
		const choisis = v === 'B' ? rs.filter((r) => routes.groupeDe(r).principale.id === r.id) : rs;
		return {
			type: 'FeatureCollection' as const,
			features: choisis.map((r) => ({
				type: 'Feature' as const,
				geometry: { type: 'Point' as const, coordinates: r.milieu },
				properties: {
					id: r.id,
					sorte: r.sorte,
					quand: r.quand,
					echeance: echeance(r),
					groupe: r.groupe,
					n: routes.groupeDe(r).restrictions.length
				}
			}))
		};
	}

	map.addSource(LIGNES, { type: 'geojson', data: vide });
	map.addSource(POINTS, { type: 'geojson', data: vide });
	map.addSource(SELECTION, { type: 'geojson', data: vide });

	const largeur = (petit: number, moyen: number, grand: number) =>
		['interpolate', ['linear'], ['zoom'], 8, petit, 13, moyen, 17, grand] as unknown as ExpressionSpecification;
	const aVenir = ['==', ['get', 'quand'], 'a-venir'] as unknown as ExpressionSpecification;
	const deviation = ['==', ['get', 'sorte'], 'deviation'] as unknown as ExpressionSpecification;
	const pasDeviation = ['!=', ['get', 'sorte'], 'deviation'] as unknown as ExpressionSpecification;

	/** Calques de chaque variante, du dessous au dessus. */
	function calques(v: Variante): LayerSpecification[] {
		const selection: LayerSpecification = {
			id: 'routes-proto-sel',
			type: 'line',
			source: SELECTION,
			layout: { 'line-cap': 'round', 'line-join': 'round' },
			paint: { 'line-color': '#111', 'line-width': largeur(6, 10, 16), 'line-opacity': 0.85 }
		};
		if (v === 'A')
			return [
				selection,
				{
					id: 'routes-proto-a-liseré',
					type: 'line',
					source: LIGNES,
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: { 'line-color': '#fff', 'line-width': largeur(4, 7, 12) }
				},
				{
					id: 'routes-proto-a-pleines',
					type: 'line',
					source: LIGNES,
					filter: pasDeviation,
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: {
						'line-color': parSorte,
						'line-width': largeur(2.5, 4.5, 8),
						'line-opacity': ['case', aVenir, 0.5, 1] as unknown as ExpressionSpecification
					}
				},
				{
					id: 'routes-proto-a-tirets',
					type: 'line',
					source: LIGNES,
					filter: deviation,
					layout: { 'line-join': 'round' },
					paint: {
						'line-color': parSorte,
						'line-width': largeur(2, 3.5, 6),
						'line-dasharray': [2, 1.5],
						'line-opacity': ['case', aVenir, 0.5, 1] as unknown as ExpressionSpecification
					}
				},
				{
					id: 'routes-proto-a-points',
					type: 'circle',
					source: POINTS,
					maxzoom: 11,
					filter: pasDeviation,
					paint: {
						'circle-color': parSorte,
						'circle-radius': 5,
						'circle-stroke-color': '#fff',
						'circle-stroke-width': 1.5,
						'circle-opacity': ['case', aVenir, 0.55, 1] as unknown as ExpressionSpecification
					}
				}
			];
		if (v === 'B')
			return [
				selection,
				{
					id: 'routes-proto-b-deviations',
					type: 'line',
					source: LIGNES,
					filter: deviation,
					layout: { 'line-join': 'round' },
					paint: {
						'line-color': SORTES.deviation.couleur,
						'line-width': largeur(2, 3.5, 6),
						'line-dasharray': [2, 1.5],
						// Cachées, sauf celles du groupe survolé ou ouvert (filtre posé plus bas).
						'line-opacity': 0.95
					}
				},
				{
					id: 'routes-proto-b-liseré',
					type: 'line',
					source: LIGNES,
					filter: pasDeviation,
					minzoom: 10.5,
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: { 'line-color': '#fff', 'line-width': largeur(5, 9, 14) }
				},
				{
					id: 'routes-proto-b-principales',
					type: 'line',
					source: LIGNES,
					filter: pasDeviation,
					minzoom: 10.5,
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: { 'line-color': parSorte, 'line-width': largeur(3, 6, 10) }
				},
				{
					id: 'routes-proto-b-marqueurs',
					type: 'circle',
					source: POINTS,
					maxzoom: 10.5,
					paint: {
						'circle-color': parSorte,
						'circle-radius': 7,
						'circle-stroke-color': ['case', aVenir, '#868e96', '#fff'] as unknown as ExpressionSpecification,
						'circle-stroke-width': 2.5
					}
				}
			];
		return [
			selection,
			{
				id: 'routes-proto-c-halo',
				type: 'line',
				source: LIGNES,
				maxzoom: 12,
				filter: ['!=', ['get', 'echeance'], 'plus-tard'] as unknown as ExpressionSpecification,
				layout: { 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': parEcheance, 'line-width': 14, 'line-blur': 6, 'line-opacity': 0.35 }
			},
			{
				id: 'routes-proto-c-pleines',
				type: 'line',
				source: LIGNES,
				filter: pasDeviation,
				layout: { 'line-cap': 'round', 'line-join': 'round' },
				paint: { 'line-color': parEcheance, 'line-width': largeur(3, 5, 8) }
			},
			{
				id: 'routes-proto-c-tirets',
				type: 'line',
				source: LIGNES,
				filter: deviation,
				layout: { 'line-join': 'round' },
				paint: { 'line-color': parEcheance, 'line-width': largeur(2, 3, 5), 'line-dasharray': [1.5, 1.5] }
			}
		];
	}

	let poses: string[] = [];
	function dessiner(v: Variante) {
		for (const id of poses) if (map.getLayer(id)) map.removeLayer(id);
		poses = [];
		for (const c of calques(v)) {
			map.addLayer(c, avant);
			poses.push(c.id);
		}
	}

	/** Restrictions qui passent les réglages du volet. */
	const affichees = $derived(routes.restrictions.filter((r) => retenue(r, variante)));

	$effect(() => {
		dessiner(variante);
		untrack(() => {
			(map.getSource(LIGNES) as GeoJSONSource).setData(lignes(affichees));
			(map.getSource(POINTS) as GeoJSONSource).setData(points(affichees, variante));
		});
	});
	$effect(() => {
		(map.getSource(LIGNES) as GeoJSONSource).setData(lignes(affichees));
		(map.getSource(POINTS) as GeoJSONSource).setData(points(affichees, untrack(() => variante)));
	});

	const ouverte = $derived(
		ctx.ouvert?.couche === 'routes' ? (routes.restriction(Number(ctx.ouvert.element)) ?? null) : null
	);

	// Contour noir de l'élément ouvert : la restriction (A, C) ou tout son groupe (B).
	$effect(() => {
		const r = ouverte;
		const membres = !r || !ctx.active ? [] : variante === 'B' ? routes.groupeDe(r).restrictions : [r];
		(map.getSource(SELECTION) as GeoJSONSource).setData(lignes(membres));
	});

	// B : les déviations du groupe survolé ou ouvert, seules.
	$effect(() => {
		if (variante !== 'B' || !map.getLayer('routes-proto-b-deviations')) return;
		const groupes = [routes.survol, ouverte?.groupe].filter(Boolean) as string[];
		map.setFilter('routes-proto-b-deviations', [
			'all',
			deviation,
			['in', ['get', 'groupe'], ['literal', groupes]]
		] as unknown as ExpressionSpecification);
	});

	$effect(() => {
		const vis = ctx.active ? 'visible' : 'none';
		for (const id of poses) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis);
		void variante;
	});

	function sous(e: MapMouseEvent) {
		const r = 6;
		return map.queryRenderedFeatures(
			[
				[e.point.x - r, e.point.y - r],
				[e.point.x + r, e.point.y + r]
			],
			{ layers: poses.filter((id) => id !== 'routes-proto-sel' && map.getLayer(id)) }
		);
	}
	function clic(e: MapMouseEvent) {
		if (!ctx.active || ctx.recouvert([e.point.x, e.point.y])) return;
		const f = sous(e).find((f) => f.properties?.id != null);
		if (!f) return;
		let r = routes.restriction(Number(f.properties.id));
		if (!r) return;
		if (variante === 'B') r = routes.groupeDe(r).principale;
		ctx.ouvrir({ couche: 'routes', element: String(r.id), position: r.milieu });
	}
	function survol(e: MapMouseEvent) {
		if (!ctx.active) return;
		const f = sous(e)[0];
		map.getCanvas().style.cursor = f ? 'pointer' : '';
		if (variante === 'B') routes.survol = (f?.properties?.groupe as string) ?? null;
	}

	onMount(() => {
		routes.charger(ctx.communes).catch(() => {});
		map.on('click', clic);
		map.on('mousemove', survol);
		return () => {
			map.off('click', clic);
			map.off('mousemove', survol);
			for (const id of poses) if (map.getLayer(id)) map.removeLayer(id);
			retirerDeLaCarte(map, [], SOURCES);
		};
	});
</script>

{#if import.meta.env.DEV}
	<Switcher
		variantes={[
			['A', 'Tracés'],
			['B', 'Groupes'],
			['C', 'Calendrier']
		]}
		courante={variante}
		choisir={(v) => ctx.regler({ variant: v as Variante })}
	/>
{/if}
