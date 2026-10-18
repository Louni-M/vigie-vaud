<script lang="ts">
	/*
	 * Carte de la couche Routes : un tracé par restriction de circulation, coloré par sorte sur un liseré blanc ; les
	 * déviations en tirets plus fins, toujours visibles ; l'à venir plus pâle, et l'en cours dessiné au-dessus de lui.
	 * Sous le zoom 11, un point par restriction au milieu de son tracé, sauf les déviations. Fondu à l'activation.
	 * Un clic ouvre le tracé le plus contraignant sous le doigt (la carte vole vers lui tout de suite), et la
	 * restriction ouverte est soulignée d'un contour noir, sous ses couleurs. Les puces du volet filtrent les calques :
	 * un tracé masqué n'est ni dessiné ni cliquable.
	 */
	import { onMount, untrack } from 'svelte';
	import type {
		ExpressionSpecification,
		GeoJSONSource,
		GeoJSONSourceSpecification,
		LayerSpecification,
		MapMouseEvent
	} from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { retirerDeLaCarte } from '#lib/socle/carte.js';
	import { routes, type Restriction } from './donnees.svelte.js';
	import type { EtatRestriction } from './etats.js';
	import { ouvrirRestriction, restrictionOuverte } from './index.js';
	import { puces } from './puces.svelte.js';
	import { plusContraignante, SORTES, type Sorte } from './sortes.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	// La carte et le calque d'ancrage ne changent pas pendant la vie de la couche.
	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const TRACES = 'routes-traces';
	const MILIEUX = 'routes-milieux';
	const SELECTION = 'routes-selection';
	/** Sous ce zoom, un point par restriction s'ajoute aux tracés, trop fins pour être vus à l'échelle du canton. */
	const ZOOM_POINTS = 11;
	/** Fondu à l'activation et à la désactivation, sauf si le visiteur a demandé moins d'animations. */
	const FONDU = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 350;
	const transition = { duration: FONDU, delay: 0 };

	const couleur = [
		'match',
		['get', 'sorte'],
		...(Object.keys(SORTES) as Sorte[]).flatMap((s) => [s, SORTES[s].couleur]),
		SORTES.autre.couleur
	] as unknown as ExpressionSpecification;
	const deviation = ['==', ['get', 'sorte'], 'deviation'] as unknown as ExpressionSpecification;
	const pasDeviation = ['!=', ['get', 'sorte'], 'deviation'] as unknown as ExpressionSpecification;
	const etatEst = (e: EtatRestriction) => ['==', ['get', 'etat'], e] as unknown as ExpressionSpecification;
	/** Largeur selon le zoom : au zoom 8, 13 et 17. */
	const largeur = (petit: unknown, moyen: unknown, grand: unknown) =>
		['interpolate', ['linear'], ['zoom'], 8, petit, 13, moyen, 17, grand] as unknown as ExpressionSpecification;
	/** Une valeur pour les déviations, une autre pour le reste. */
	const siDeviation = (d: number, autre: number) => ['case', deviation, d, autre];

	type Opacite = 'line-opacity' | 'circle-opacity' | 'circle-stroke-opacity';
	/** Calques ajoutés, du dessous au dessus, avec leurs opacités pleines : le fondu les multiplie par 0 ou 1. */
	const calques: { spec: LayerSpecification; opacites: [Opacite, number][] }[] = [];

	// Le contour noir de la restriction ouverte, sous tout le reste : il déborde du liseré blanc de chaque côté.
	calques.push({
		spec: {
			id: SELECTION,
			type: 'line',
			source: SELECTION,
			layout: { 'line-cap': 'round', 'line-join': 'round' },
			paint: { 'line-color': '#111', 'line-width': largeur(7, 10, 16) }
		},
		opacites: [['line-opacity', 0.85]]
	});

	/*
	 * Les calques d'un état : liseré blanc, tracés pleins, déviations en tirets, puis points au petit zoom. L'à venir
	 * est posé d'abord, l'en cours ensuite : il le recouvre là où deux phases se superposent.
	 */
	for (const etat of ['a_venir', 'en_cours'] as const) {
		const pale = etat === 'a_venir';
		calques.push(
			{
				spec: {
					id: `routes-lisere-${etat}`,
					type: 'line',
					source: TRACES,
					filter: etatEst(etat),
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: { 'line-color': '#fff', 'line-width': largeur(siDeviation(3.5, 4), siDeviation(5.5, 7), siDeviation(9, 12)) }
				},
				opacites: [['line-opacity', pale ? 0.8 : 1]]
			},
			{
				spec: {
					id: `routes-pleins-${etat}`,
					type: 'line',
					source: TRACES,
					filter: ['all', etatEst(etat), pasDeviation] as unknown as ExpressionSpecification,
					layout: { 'line-cap': 'round', 'line-join': 'round' },
					paint: { 'line-color': couleur, 'line-width': largeur(2.5, 4.5, 8) }
				},
				opacites: [['line-opacity', pale ? 0.5 : 1]]
			},
			{
				spec: {
					id: `routes-tirets-${etat}`,
					type: 'line',
					source: TRACES,
					filter: ['all', etatEst(etat), deviation] as unknown as ExpressionSpecification,
					layout: { 'line-join': 'round' },
					paint: { 'line-color': couleur, 'line-width': largeur(2, 3.5, 6), 'line-dasharray': [2, 1.5] }
				},
				opacites: [['line-opacity', pale ? 0.5 : 1]]
			},
			{
				spec: {
					id: `routes-points-${etat}`,
					type: 'circle',
					source: MILIEUX,
					maxzoom: ZOOM_POINTS,
					filter: ['all', etatEst(etat), pasDeviation] as unknown as ExpressionSpecification,
					paint: {
						'circle-color': couleur,
						'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 3.5, ZOOM_POINTS, 5],
						'circle-stroke-color': '#fff',
						'circle-stroke-width': 1.5
					}
				},
				opacites: [
					['circle-opacity', pale ? 0.55 : 1],
					['circle-stroke-opacity', pale ? 0.7 : 1]
				]
			}
		);
	}

	function traces(rs: Restriction[]): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: rs.map((r) => ({
				type: 'Feature',
				id: r.id,
				geometry: { type: 'MultiLineString', coordinates: r.lignes },
				properties: { id: r.id, sorte: r.sorte, etat: r.etat }
			}))
		};
	}
	function milieux(rs: Restriction[]): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: rs.map((r) => ({
				type: 'Feature',
				id: r.id,
				geometry: { type: 'Point', coordinates: r.milieu },
				properties: { id: r.id, sorte: r.sorte, etat: r.etat }
			}))
		};
	}

	// Calques ajoutés transparents : le premier passage de l'effet du fondu les fait apparaître.
	map.addSource(TRACES, { type: 'geojson', data: traces(routes.restrictions) });
	map.addSource(MILIEUX, { type: 'geojson', data: milieux(routes.restrictions) });
	map.addSource(SELECTION, { type: 'geojson', data: traces([]) });
	for (const { spec, opacites } of calques) {
		const paint = { ...spec.paint } as Record<string, unknown>;
		for (const [prop] of opacites) {
			paint[prop] = 0;
			paint[`${prop}-transition`] = transition;
		}
		map.addLayer({ ...spec, paint } as LayerSpecification, avant);
	}
	const ids = calques.map((c) => c.spec.id);
	/** Les calques qu'un clic peut toucher : le liseré élargit la prise, au doigt surtout. */
	const cliquables = ids.filter((id) => id !== SELECTION);

	/*
	 * Clic sur la carte : parmi les tracés à quelques pixels, le plus contraignant s'ouvre (fermeture, feux,
	 * restriction particulière, autre, déviation), et la carte vole vers le milieu de son tracé sans attendre sa fiche.
	 */
	function clic(e: MapMouseEvent) {
		// Un hôtel de ville sous le clic, dessiné au-dessus, l'emporte sur les tracés voisins.
		if (!ctx.active || ctx.recouvert([e.point.x, e.point.y])) return;
		const r = 8;
		const touches = map.queryRenderedFeatures(
			[
				[e.point.x - r, e.point.y - r],
				[e.point.x + r, e.point.y + r]
			],
			{ layers: cliquables }
		);
		const touchees = new Set(touches.map((f) => Number(f.properties?.id)));
		const choisie = plusContraignante(routes.restrictions.filter((x) => touchees.has(x.id)));
		if (choisie) ouvrirRestriction(ctx, choisie);
	}
	const pointeur = () => (map.getCanvas().style.cursor = ctx.active ? 'pointer' : '');
	const sansPointeur = () => (map.getCanvas().style.cursor = '');
	map.on('click', clic);
	for (const id of cliquables) {
		map.on('mouseenter', id, pointeur);
		map.on('mouseleave', id, sansPointeur);
	}

	/** Le tracé de la restriction ouverte : celui déjà chargé, sinon celui que le registre vient de chercher. */
	let ouverte = $state.raw<Restriction | null>(null);
	$effect(() => {
		const id = restrictionOuverte(ctx.ouvert);
		if (id === null) return void (ouverte = null);
		const chargee = routes.restrictions.find((x) => x.id === id);
		if (chargee) return void (ouverte = chargee);
		let actuelle = true;
		routes.restriction(id).then(
			(x) => actuelle && (ouverte = x),
			() => {}
		);
		return () => (actuelle = false);
	});
	$effect(() => {
		(map.getSource(SELECTION) as GeoJSONSource).setData(traces(ctx.active && ouverte ? [ouverte] : []));
	});

	/*
	 * Puces du volet : chaque calque garde son propre filtre (état, déviation ou non) et ne montre que les sortes et
	 * les états allumés. Filtrer les calques plutôt que les sources rend les tracés masqués incliquables. Le contour
	 * de la restriction ouverte reste, elle, toujours visible.
	 */
	$effect(() => {
		const { sortes, etats } = puces.filtres;
		const montre = [
			['in', ['get', 'sorte'], ['literal', [...sortes]]],
			['in', ['get', 'etat'], ['literal', [...etats]]]
		];
		for (const { spec } of calques) {
			if (spec.id === SELECTION || !('filter' in spec) || !spec.filter) continue;
			map.setFilter(spec.id, ['all', spec.filter, ...montre] as unknown as ExpressionSpecification);
		}
	});

	onMount(() => {
		// Un échec est signalé par le badge et le volet, qui propose de réessayer.
		routes.charger().catch(() => {});
		return () => {
			map.off('click', clic);
			for (const id of cliquables) {
				map.off('mouseenter', id, pointeur);
				map.off('mouseleave', id, sansPointeur);
			}
			retirerDeLaCarte(map, ids, [TRACES, MILIEUX, SELECTION]);
		};
	});

	$effect(() => {
		const rs = routes.restrictions;
		(map.getSource(TRACES) as GeoJSONSource).setData(traces(rs));
		(map.getSource(MILIEUX) as GeoJSONSource).setData(milieux(rs));
	});

	// Fondu : les tracés apparaissent ou disparaissent, puis les calques désactivés sont retirés du rendu.
	$effect(() => {
		const active = ctx.active;
		if (active) for (const id of ids) map.setLayoutProperty(id, 'visibility', 'visible');
		for (const { spec, opacites } of calques)
			for (const [prop, pleine] of opacites) map.setPaintProperty(spec.id, prop, active ? pleine : 0);
		if (active) return;
		const t = setTimeout(() => {
			for (const id of ids) map.setLayoutProperty(id, 'visibility', 'none');
		}, FONDU);
		return () => clearTimeout(t);
	});
</script>
