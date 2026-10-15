<script lang="ts">
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	// MapLibre 6 calcule l'URL de son worker à l'exécution : Vite ne le copie pas dans le build.
	// On l'importe explicitement comme fichier, sinon les cartes restent vides en production.
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
	import type {
		Map as MlMap,
		GeoJSONSource,
		GeoJSONSourceSpecification,
		ExpressionSpecification,
		LngLatBoundsLike,
		MapMouseEvent
	} from 'maplibre-gl';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import { attributionHtml, source } from '#lib/sources.js';
	import type { Centre, Dossier, PointHisto, Statut } from '#lib/types.js';

	/** Emprise du canton : vue de départ, et retour par le logo. */
	const CANTON: LngLatBoundsLike = [5.9, 46.18, 7.25, 46.99];

	interface Props {
		dossiers: Dossier[];
		/** Affiche aussi l'historique (`histo`). */
		historique?: boolean;
		/** Points de l'historique chargés jusqu'ici ; la liste ne fait que s'allonger (ajouts incrémentaux). */
		histo?: PointHisto[];
		statuts?: Statut[];
		nature?: string;
		anneeMin?: number;
		selection?: number | null;
		/** Position du dossier sélectionné, marquée d'un anneau (y compris pour un dossier de l'historique). */
		point?: [number, number] | null;
		/** Adresse cherchée ou position « autour de moi » : reste dans le navigateur, jamais dans l'URL. */
		repere?: [number, number] | null;
		bounds?: LngLatBoundsLike;
		interactive?: boolean;
		/** Clic sur un point : n° du dossier et position du point. */
		onselect?: (id: number, position: [number, number]) => void;
		onview?: (b: [number, number, number, number], centre: Centre) => void;
	}

	let {
		dossiers,
		historique = false,
		histo = [],
		statuts = STATUTS_ORDRE,
		nature = '',
		anneeMin = 1999,
		selection = null,
		point = null,
		repere = null,
		bounds = CANTON,
		interactive = true,
		onselect,
		onview
	}: Props = $props();

	let container: HTMLDivElement;
	let map: MlMap | undefined = $state();
	let pret = $state(false);
	/** Vue demandée avant que la carte soit prête (lien partagé, retour arrière). */
	let enAttente: Centre | null = null;
	let cadreEnAttente: LngLatBoundsLike | null = null;

	const STYLE = 'https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json';
	const SWISSIMAGE = 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg';
	/** Contrôle d'attribution, tiré de sources.json : le fond de carte, puis la source des permis. */
	const ATTRIBUTION = ['swisstopo-fond', 'camac-permis'].map((id) => attributionHtml(source(id)));

	const couleur = (prop: string) =>
		[
			'match',
			['get', prop],
			...STATUTS_ORDRE.flatMap((s) => [s, STATUTS[s].couleur]),
			STATUTS.autre.couleur
		] as unknown as ExpressionSpecification;

	function toGeoJSON(ds: Dossier[]): GeoJSONSourceSpecification['data'] {
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

	function unPoint(p: [number, number] | null): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: p ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }] : []
		};
	}

	function filtre(statutProp: string, natureProp: string, avecAnnee: boolean): ExpressionSpecification {
		const conds: ExpressionSpecification[] = [['in', ['get', statutProp], ['literal', statuts]]];
		if (nature) conds.push(['==', ['get', natureProp], nature]);
		if (avecAnnee) conds.push(['>=', ['get', 'y'], anneeMin]);
		return ['all', ...conds];
	}

	function emitView() {
		if (!map || !onview) return;
		const b = map.getBounds();
		const c = map.getCenter();
		onview([b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], { lon: c.lng, lat: c.lat, zoom: map.getZoom() });
	}

	/**
	 * Centre la carte sur un point (recherche d'adresse, géolocalisation, sélection), en un vol souple :
	 * dézoom léger puis approche. `decalage` (px) remonte le point au-dessus d'un aperçu en bas de carte.
	 * MapLibre remplace l'animation par un saut si le visiteur a demandé moins d'animations.
	 */
	export function voler(lon: number, lat: number, zoom = 16, decalage = 0) {
		if (!map) return aller({ lon, lat, zoom });
		const cible = Math.max(map.getZoom(), zoom);
		const loin = cible - map.getZoom() > 4;
		map.flyTo({
			center: [lon, lat],
			zoom: cible,
			offset: [0, -decalage],
			curve: 1.6,
			speed: loin ? 1.4 : 0.9,
			easing: (t) => 1 - Math.pow(1 - t, 3)
		});
	}

	export function cadrer(b: LngLatBoundsLike, anime = true) {
		if (!map) {
			cadreEnAttente = b;
			enAttente = null;
			return;
		}
		map.fitBounds(b, { padding: 40, duration: anime ? 600 : 0 });
	}

	/** Revient à la vue d'ensemble du canton, en un vol souple. */
	export function vueCanton() {
		if (!map) return cadrer(CANTON, false);
		map.fitBounds(CANTON, { padding: 20, duration: 1200, easing: (t) => 1 - Math.pow(1 - t, 3) });
	}

	/** Rétablit une vue précise (URL, retour à la liste) ; gardée pour le chargement si la carte n'est pas prête. */
	export function aller(c: Centre, anime = true) {
		if (!map) {
			enAttente = c;
			cadreEnAttente = null;
			return;
		}
		map.easeTo({ center: [c.lon, c.lat], zoom: c.zoom, duration: anime ? 500 : 0 });
	}

	onMount(() => {
		let disposed = false;
		(async () => {
			const maplibregl = await import('maplibre-gl');
			if (disposed) return;
			maplibregl.setWorkerUrl(workerUrl);

			const m = new maplibregl.Map({
				container,
				style: STYLE,
				...(enAttente
					? { center: [enAttente.lon, enAttente.lat] as [number, number], zoom: enAttente.zoom }
					: { bounds: cadreEnAttente ?? bounds, fitBoundsOptions: { padding: 20 } }),
				interactive,
				attributionControl: false,
				locale: {
					'Map.Title': 'Carte',
					'NavigationControl.ZoomIn': 'Zoom avant',
					'NavigationControl.ZoomOut': 'Zoom arrière',
					'AttributionControl.ToggleAttribution': 'Afficher ou masquer les sources'
				},
				maxBounds: [4.5, 45.5, 8.5, 47.6]
			});
			m.addControl(
				new maplibregl.AttributionControl({
					compact: true,
					customAttribution: ATTRIBUTION
				})
			);
			if (interactive) m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

			m.on('load', () => {
				// Fond aérien (SWISSIMAGE) toujours affiché, sous les étiquettes du fond swisstopo.
				const premierSymbole = m.getStyle().layers.find((l: { type: string }) => l.type === 'symbol')?.id;
				m.addSource('swissimage', { type: 'raster', tiles: [SWISSIMAGE], tileSize: 256, maxzoom: 20 });
				m.addLayer({ id: 'swissimage', type: 'raster', source: 'swissimage' }, premierSymbole);

				// Historique lu en direct sur le service du canton, une année après l'autre (voir `histo`).
				m.addSource('historique', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
				envoyes = 0;
				m.addLayer({
					id: 'historique',
					type: 'circle',
					source: 'historique',
					layout: { visibility: 'none' },
					paint: {
						'circle-color': couleur('s'),
						'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 2, 13, 4, 17, 8],
						'circle-opacity': 0.9,
						// Liseré blanc à toutes les échelles : sans lui, les points se perdent dans la photo aérienne.
						'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 8, 0.5, 12, 0.8, 15, 1.2],
						'circle-stroke-color': '#fff',
						'circle-stroke-opacity': 0.8
					}
				});

				m.addSource('actifs', { type: 'geojson', data: toGeoJSON(dossiers) });
				m.addLayer({
					id: 'actifs',
					type: 'circle',
					source: 'actifs',
					paint: {
						'circle-color': couleur('statut'),
						'circle-radius': [
							'interpolate', ['linear'], ['zoom'],
							8, ['match', ['get', 'statut'], 'enquete', 4, 2.5],
							14, ['match', ['get', 'statut'], 'enquete', 8, 5],
							17, ['match', ['get', 'statut'], 'enquete', 12, 8]
						],
						'circle-stroke-width': ['case', ['boolean', ['feature-state', 'sel'], false], 3, 1.5],
						'circle-stroke-color': ['case', ['boolean', ['feature-state', 'sel'], false], '#111', '#fff']
					}
				});

				m.addSource('selection', { type: 'geojson', data: unPoint(point) });
				m.addLayer({
					id: 'selection',
					type: 'circle',
					source: 'selection',
					paint: {
						'circle-radius': ['interpolate', ['linear'], ['zoom'], 8, 9, 17, 16],
						'circle-opacity': 0,
						'circle-stroke-width': 3,
						'circle-stroke-color': '#111'
					}
				});

				m.addSource('repere', { type: 'geojson', data: unPoint(repere) });
				m.addLayer({
					id: 'repere',
					type: 'circle',
					source: 'repere',
					paint: {
						'circle-radius': 7,
						'circle-color': '#1f6feb',
						'circle-stroke-width': 3,
						'circle-stroke-color': '#fff'
					}
				});

				if (onselect) {
					// Tolérance de quelques pixels autour du clic : les points sont petits, surtout au doigt.
					// Le point le plus proche l'emporte ; à égalité, les dossiers actifs (couche du dessus).
					m.on('click', (e: MapMouseEvent) => {
						const r = 8;
						const proches = m.queryRenderedFeatures(
							[[e.point.x - r, e.point.y - r], [e.point.x + r, e.point.y + r]],
							{ layers: ['actifs', 'historique'] }
						);
						const distance = (f: (typeof proches)[number]) => {
							const p = m.project((f.geometry as unknown as { coordinates: [number, number] }).coordinates);
							return Math.hypot(p.x - e.point.x, p.y - e.point.y);
						};
						const f = proches.sort((a, b) => distance(a) - distance(b))[0];
						const id = f?.properties?.id;
						const position = (f?.geometry as unknown as { coordinates: [number, number] })?.coordinates;
						if (id != null) onselect?.(Number(id), position);
					});
					for (const layer of ['actifs', 'historique']) {
						m.on('mouseenter', layer, () => (m.getCanvas().style.cursor = 'pointer'));
						m.on('mouseleave', layer, () => (m.getCanvas().style.cursor = ''));
					}
				}
				m.on('moveend', emitView);
				map = m;
				// Vue demandée pendant le chargement du style.
				if (enAttente) m.jumpTo({ center: [enAttente.lon, enAttente.lat], zoom: enAttente.zoom });
				else if (cadreEnAttente) m.fitBounds(cadreEnAttente, { padding: 40, duration: 0 });
				enAttente = cadreEnAttente = null;
				if (import.meta.env.DEV) (window as unknown as { __carte: MlMap }).__carte = m;
				pret = true;
				emitView();
			});
		})();
		return () => {
			disposed = true;
			map?.remove();
		};
	});

	$effect(() => {
		if (!pret || !map) return;
		(map.getSource('actifs') as GeoJSONSource).setData(toGeoJSON(dossiers));
	});

	/** Points d'historique déjà transmis à la carte : seuls les nouveaux sont ajoutés. */
	let envoyes = 0;
	let premierEnvoye: number | undefined;
	$effect(() => {
		if (!pret || !map) return;
		const source = map.getSource('historique') as GeoJSONSource;
		if (histo.length >= envoyes && envoyes > 0 && histo[0]?.id === premierEnvoye) {
			if (histo.length > envoyes) source.updateData({ add: histo.slice(envoyes).map(versHisto) });
		} else source.setData({ type: 'FeatureCollection', features: histo.map(versHisto) });
		envoyes = histo.length;
		premierEnvoye = histo[0]?.id;
	});

	$effect(() => {
		if (!pret || !map) return;
		map.setFilter('actifs', filtre('statut', 'nature', false));
		map.setFilter('historique', filtre('s', 'n', true));
		map.setLayoutProperty('historique', 'visibility', historique ? 'visible' : 'none');
	});

	$effect(() => {
		if (!pret || !map) return;
		(map.getSource('selection') as GeoJSONSource).setData(unPoint(point));
	});

	$effect(() => {
		if (!pret || !map) return;
		(map.getSource('repere') as GeoJSONSource).setData(unPoint(repere));
	});

	let precedent: number | null = null;
	$effect(() => {
		if (!pret || !map) return;
		if (precedent != null) map.setFeatureState({ source: 'actifs', id: precedent }, { sel: false });
		if (selection != null) map.setFeatureState({ source: 'actifs', id: selection }, { sel: true });
		precedent = selection;
	});
</script>

<div class="carte" bind:this={container}></div>

<style>
	.carte {
		position: absolute;
		inset: 0;
	}
	:global(.maplibregl-ctrl-attrib) {
		font-size: 11px;
	}
	/* Boutons de zoom d'au moins 44 px au doigt (29 px par défaut). */
	@media (pointer: coarse), (max-width: 760px) {
		:global(.maplibregl-ctrl-group button) {
			width: 44px;
			height: 44px;
		}
	}
</style>
