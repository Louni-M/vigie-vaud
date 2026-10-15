<script lang="ts">
	/*
	 * Carte de la couche Permis : sources MapLibre des dossiers en cours et de l'historique, filtres, et fondu
	 * à l'activation. L'ouverture d'un dossier (clic, anneau de sélection) viendra avec l'onglet Permis.
	 */
	import { onMount, untrack } from 'svelte';
	import type {
		ExpressionSpecification,
		GeoJSONSource,
		GeoJSONSourceSpecification
	} from 'maplibre-gl';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Dossier, PointHisto } from '#lib/types.js';
	import { permis, type Parametres } from './donnees.svelte.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	// La carte et le calque d'ancrage ne changent pas pendant la vie de la couche.
	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const ACTIFS = 'permis-actifs';
	const HISTO = 'permis-historique';
	/** Fondu à l'activation et à la désactivation, sauf si le visiteur a demandé moins d'animations. */
	const FONDU = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 350;
	/** Opacités pleines des calques ; le fondu les multiplie par 0 ou 1. */
	const OPACITES: [string, 'circle-opacity' | 'circle-stroke-opacity', number][] = [
		[ACTIFS, 'circle-opacity', 1],
		[ACTIFS, 'circle-stroke-opacity', 1],
		[HISTO, 'circle-opacity', 0.9],
		[HISTO, 'circle-stroke-opacity', 0.8]
	];

	const couleur = (prop: string) =>
		[
			'match',
			['get', prop],
			...STATUTS_ORDRE.flatMap((s) => [s, STATUTS[s].couleur]),
			STATUTS.autre.couleur
		] as unknown as ExpressionSpecification;

	function versGeoJSON(ds: Dossier[]): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: ds.map((d) => ({
				type: 'Feature',
				id: d.id,
				geometry: { type: 'Point', coordinates: [d.lon, d.lat] },
				properties: { id: d.id, statut: d.statut, nature: d.nature }
			}))
		};
	}

	const versHisto = (d: PointHisto) => ({
		type: 'Feature' as const,
		id: d.id,
		geometry: { type: 'Point' as const, coordinates: [d.lon, d.lat] },
		properties: { id: d.id, s: d.statut, n: d.nature, y: Number(d.debut?.slice(0, 4) ?? 0) }
	});

	function filtre(statutProp: string, natureProp: string, avecAnnee: boolean): ExpressionSpecification {
		const { statuts, nature, depuis } = ctx.parametres;
		const conds: ExpressionSpecification[] = [['in', ['get', statutProp], ['literal', statuts]]];
		if (nature) conds.push(['==', ['get', natureProp], nature]);
		if (avecAnnee) conds.push(['>=', ['get', 'y'], depuis]);
		return ['all', ...conds];
	}

	const transition = { duration: FONDU, delay: 0 };

	// Calques ajoutés transparents : le premier passage de l'effet du fondu les fait apparaître.
	map.addSource(HISTO, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
	map.addLayer(
		{
			id: HISTO,
			type: 'circle',
			source: HISTO,
			layout: { visibility: 'none' },
			paint: {
				'circle-color': couleur('s'),
				'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 2, 13, 4, 17, 8],
				'circle-opacity': 0,
				'circle-opacity-transition': transition,
				// Liseré blanc à toutes les échelles : sans lui, les points se perdent dans la photo aérienne.
				'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 8, 0.5, 12, 0.8, 15, 1.2],
				'circle-stroke-color': '#fff',
				'circle-stroke-opacity': 0,
				'circle-stroke-opacity-transition': transition
			}
		},
		avant
	);
	map.addSource(ACTIFS, { type: 'geojson', data: versGeoJSON(permis.actifs) });
	map.addLayer(
		{
			id: ACTIFS,
			type: 'circle',
			source: ACTIFS,
			paint: {
				'circle-color': couleur('statut'),
				'circle-radius': [
					'interpolate', ['linear'], ['zoom'],
					8, ['match', ['get', 'statut'], 'enquete', 4, 2.5],
					14, ['match', ['get', 'statut'], 'enquete', 8, 5],
					17, ['match', ['get', 'statut'], 'enquete', 12, 8]
				],
				'circle-opacity': 0,
				'circle-opacity-transition': transition,
				'circle-stroke-width': 1.5,
				'circle-stroke-color': '#fff',
				'circle-stroke-opacity': 0,
				'circle-stroke-opacity-transition': transition
			}
		},
		avant
	);

	onMount(() => {
		// Un échec est signalé par le volet, qui propose de réessayer.
		permis.chargerActifs().catch(() => {});
		return () => {
			// La carte du socle a pu être détruite avant cette couche (fin de la coquille).
			try {
				for (const id of [ACTIFS, HISTO]) {
					map.removeLayer(id);
					map.removeSource(id);
				}
			} catch {
				/* carte déjà détruite */
			}
		};
	});

	$effect(() => {
		(map.getSource(ACTIFS) as GeoJSONSource).setData(versGeoJSON(permis.actifs));
	});

	/** Points d'historique déjà transmis à la carte : seuls les nouveaux sont ajoutés. */
	let envoyes = 0;
	let premierEnvoye: number | undefined;
	$effect(() => {
		const histo = permis.histo;
		const source = map.getSource(HISTO) as GeoJSONSource;
		if (histo.length >= envoyes && envoyes > 0 && histo[0]?.id === premierEnvoye) {
			if (histo.length > envoyes) source.updateData({ add: histo.slice(envoyes).map(versHisto) });
		} else source.setData({ type: 'FeatureCollection', features: histo.map(versHisto) });
		envoyes = histo.length;
		premierEnvoye = histo[0]?.id;
	});

	$effect(() => {
		map.setFilter(ACTIFS, filtre('statut', 'nature', false));
		map.setFilter(HISTO, filtre('s', 'n', true));
	});

	/*
	 * Historique : points légers lus sur le service du canton, une année à la fois, de l'année en cours
	 * jusqu'à « depuis ». Le curseur des années passe par toutes les valeurs : on attend qu'il s'arrête.
	 */
	$effect(() => {
		if (!ctx.active || !ctx.parametres.historique) return;
		const depuis = ctx.parametres.depuis;
		const t = setTimeout(() => permis.chargerHisto(depuis), 250);
		return () => clearTimeout(t);
	});

	// Fondu : les points apparaissent ou disparaissent, puis les calques désactivés sont retirés du rendu.
	$effect(() => {
		const active = ctx.active;
		const historique = ctx.parametres.historique;
		if (active) {
			map.setLayoutProperty(ACTIFS, 'visibility', 'visible');
			map.setLayoutProperty(HISTO, 'visibility', historique ? 'visible' : 'none');
		}
		for (const [id, prop, pleine] of OPACITES) map.setPaintProperty(id, prop, active ? pleine : 0);
		if (active) return;
		const t = setTimeout(() => {
			for (const id of [ACTIFS, HISTO]) map.setLayoutProperty(id, 'visibility', 'none');
		}, FONDU);
		return () => clearTimeout(t);
	});
</script>
