<script lang="ts" module>
	/** Calque du repère, au-dessus de tout : le registre range les couches juste en dessous. */
	export const CALQUE_REPERE = 'repere';
</script>

<script lang="ts">
	/*
	 * Carte du socle : fond (plan swisstopo et SWISSIMAGE), vue, zone visible et repère. Elle ne connaît
	 * aucune couche : celles-ci reçoivent la carte MapLibre (`onpret`) et y ajoutent leurs propres calques.
	 */
	import { onMount } from 'svelte';
	import 'maplibre-gl/dist/maplibre-gl.css';
	// MapLibre 6 calcule l'URL de son worker à l'exécution : Vite ne le copie pas dans le build.
	// On l'importe explicitement comme fichier, sinon les cartes restent vides en production.
	import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
	import type {
		AttributionControl,
		GeoJSONSource,
		GeoJSONSourceSpecification,
		LngLatBoundsLike,
		Map as MlMap
	} from 'maplibre-gl';
	import type { Centre, Zone } from '#lib/types.js';
	import { TELEPHONE } from './telephone.js';

	/** Emprise du canton : vue de départ, et retour par le logo. */
	const CANTON: LngLatBoundsLike = [5.9, 46.18, 7.25, 46.99];

	interface Props {
		/** Adresse cherchée ou position « autour de moi » : reste dans le navigateur, jamais dans l'URL. */
		repere?: [number, number] | null;
		/** Attributions en HTML, dans l'ordre d'affichage (fond de carte d'abord). */
		attribution?: string[];
		bounds?: LngLatBoundsLike;
		interactive?: boolean;
		/** La carte MapLibre est chargée, fond compris : les couches peuvent y ajouter leurs calques. */
		onpret?: (map: MlMap) => void;
		/**
		 * Fin d'un déplacement. `parDefaut` : la vue du canton (au chargement, ou rétablie par `vueCanton`),
		 * qui n'est pas un choix du visiteur. `parLaPersonne` : le visiteur a glissé, zoomé (molette, doigts,
		 * clavier ou boutons) ; faux pour les vols et cadrages demandés à la carte.
		 */
		onvue?: (zone: Zone, centre: Centre, parDefaut: boolean, parLaPersonne: boolean) => void;
	}

	let { repere = null, attribution = [], bounds = CANTON, interactive = true, onpret, onvue }: Props = $props();

	let container: HTMLDivElement;
	let map: MlMap | undefined = $state();
	let pret = $state(false);
	/** Vue demandée avant que la carte soit prête (lien partagé, retour arrière). */
	let enAttente: Centre | null = null;
	let cadreEnAttente: LngLatBoundsLike | null = null;
	/** Le cadre en attente mène à une vue par défaut. */
	let cadreParDefaut = false;
	/** La vue en attente (`enAttente`) n'est pas un choix du visiteur : fiche propre qu'on vient d'ouvrir. */
	let vueParDefaut = false;
	let maplibre: typeof import('maplibre-gl') | undefined;
	let controle: AttributionControl | undefined;
	/** Le prochain déplacement terminé mène à une vue par défaut (canton, commune cadrée) : elle n'entre pas dans l'adresse. */
	let versDefaut = false;

	const STYLE = 'https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json';
	const SWISSIMAGE = 'https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg';

	function unPoint(p: [number, number] | null): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: p ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }] : []
		};
	}

	function emitView(parDefaut = false, parLaPersonne = false) {
		if (!map || !onvue) return;
		parDefaut ||= versDefaut;
		versDefaut = false;
		const b = map.getBounds();
		const c = map.getCenter();
		onvue(
			[b.getWest(), b.getSouth(), b.getEast(), b.getNorth()],
			{ lon: c.lng, lat: c.lat, zoom: map.getZoom() },
			parDefaut,
			parLaPersonne
		);
	}

	/**
	 * Centre la carte sur un point (recherche d'adresse, géolocalisation, sélection), en un vol souple :
	 * dézoom léger puis approche. `decalage` (px) remonte le point au-dessus d'un aperçu en bas de carte.
	 * MapLibre remplace l'animation par un saut si le visiteur a demandé moins d'animations. `parDefaut` : la vue
	 * obtenue n'est pas un choix du visiteur (fiche propre qu'on vient d'ouvrir).
	 */
	export function voler(lon: number, lat: number, zoom = 16, decalage = 0, parDefaut = false) {
		if (!map) {
			aller({ lon, lat, zoom });
			vueParDefaut = parDefaut;
			return;
		}
		versDefaut = parDefaut;
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

	/*
	 * `cadrer`, `vueCanton` et `aller` suivent l'adresse : la fiche commune vient peut-être d'ouvrir ou de fermer
	 * sa colonne, et la carte relit sa taille avant de bouger, sans attendre son observateur de taille.
	 */

	/**
	 * Cadre une emprise. `parDefaut` : la vue obtenue n'est pas un choix du visiteur (commune qu'on vient
	 * d'ouvrir).
	 */
	export function cadrer(b: LngLatBoundsLike, anime = true, parDefaut = false) {
		if (!map) {
			cadreEnAttente = b;
			cadreParDefaut = parDefaut;
			enAttente = null;
			return;
		}
		map.resize();
		versDefaut = parDefaut;
		map.fitBounds(b, { padding: 40, duration: anime ? 600 : 0 });
	}

	/** Revient à la vue d'ensemble du canton, en un vol souple. */
	export function vueCanton() {
		if (!map) return cadrer(CANTON, false);
		map.resize();
		versDefaut = true;
		map.fitBounds(CANTON, { padding: 20, duration: 1200, easing: (t) => 1 - Math.pow(1 - t, 3) });
	}

	/** Rétablit une vue précise (URL, retour arrière) ; gardée pour le chargement si la carte n'est pas prête. */
	export function aller(c: Centre, anime = true) {
		if (!map) {
			enAttente = c;
			vueParDefaut = false;
			cadreEnAttente = null;
			return;
		}
		map.resize();
		map.easeTo({ center: [c.lon, c.lat], zoom: c.zoom, duration: anime ? 500 : 0 });
	}

	onMount(() => {
		let disposed = false;
		(async () => {
			const maplibregl = await import('maplibre-gl');
			if (disposed) return;
			maplibregl.setWorkerUrl(workerUrl);
			maplibre = maplibregl;

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
			if (interactive) m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

			m.on('load', () => {
				// Fond aérien (SWISSIMAGE) toujours affiché, sous les étiquettes du fond swisstopo.
				const premierSymbole = m.getStyle().layers.find((l: { type: string }) => l.type === 'symbol')?.id;
				m.addSource('swissimage', { type: 'raster', tiles: [SWISSIMAGE], tileSize: 256, maxzoom: 20 });
				m.addLayer({ id: 'swissimage', type: 'raster', source: 'swissimage' }, premierSymbole);

				m.addSource(CALQUE_REPERE, { type: 'geojson', data: unPoint(repere) });
				m.addLayer({
					id: CALQUE_REPERE,
					type: 'circle',
					source: CALQUE_REPERE,
					paint: {
						'circle-radius': 7,
						'circle-color': '#1f6feb',
						'circle-stroke-width': 3,
						'circle-stroke-color': '#fff'
					}
				});

				// MapLibre joint l'évènement du navigateur aux déplacements faits par le visiteur, pas aux vols demandés
				// ni aux changements de taille. Il l'omet parfois pour la molette : un tour de molette juste avant compte.
				let geste = false;
				let molette = -Infinity;
				container.addEventListener('wheel', () => (molette = performance.now()), { capture: true, passive: true });
				m.on('movestart', (e) => (geste = !!e.originalEvent || performance.now() - molette < 500));
				m.on('moveend', (e) => emitView(false, geste || !!e.originalEvent));
				map = m;
				// Vue demandée pendant le chargement du style.
				// Une vue demandée (lien partagé) est un choix du visiteur : elle reste dans l'adresse.
				const parDefaut = enAttente ? vueParDefaut : !cadreEnAttente || cadreParDefaut;
				if (enAttente) m.jumpTo({ center: [enAttente.lon, enAttente.lat], zoom: enAttente.zoom });
				else if (cadreEnAttente) m.fitBounds(cadreEnAttente, { padding: 40, duration: 0 });
				enAttente = cadreEnAttente = null;
				if (import.meta.env.DEV) (window as unknown as { __carte: MlMap }).__carte = m;
				pret = true;
				onpret?.(m);
				emitView(parDefaut);
			});
		})();
		return () => {
			disposed = true;
			map?.remove();
		};
	});

	// Contrôle d'attribution, refait quand la liste change (couche activée ou désactivée).
	$effect(() => {
		const textes = attribution;
		if (!pret || !map || !maplibre) return;
		if (controle) map.removeControl(controle);
		controle = new maplibre.AttributionControl({ compact: true, customAttribution: textes });
		map.addControl(controle);
		// MapLibre déplie les sources jusqu'au premier glissement : sur téléphone, elles passeraient sous les liens
		// et l'aperçu. Elles restent derrière le bouton « i », comme après un glissement.
		if (matchMedia(TELEPHONE).matches) {
			map.getContainer().querySelector('.maplibregl-ctrl-attrib')?.classList.remove('maplibregl-compact-show');
		}
	});

	$effect(() => {
		if (!pret || !map) return;
		(map.getSource(CALQUE_REPERE) as GeoJSONSource).setData(unPoint(repere));
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
	/* Téléphone : les sources ouvertes par le bouton « i » passent devant l'aperçu et les liens, le temps de les lire. */
	@media (max-width: 760px) {
		:global(.maplibregl-ctrl-bottom-right:has(.maplibregl-compact-show)) {
			z-index: 5;
		}
	}
</style>
