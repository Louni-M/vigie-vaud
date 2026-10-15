<script lang="ts">
	/*
	 * Carte de la couche Hôtels de ville : un marqueur par commune actuelle (les anciennes communes n'en ont pas),
	 * celui de la commune ouverte plus grand. Au survol, une bulle donne le nom et l'adresse (sans adresse pour
	 * une position approximative) ; un clic ouvre la fiche de la commune.
	 */
	import { onMount, untrack } from 'svelte';
	import type {
		ExpressionSpecification,
		GeoJSONSource,
		GeoJSONSourceSpecification,
		MapLayerMouseEvent,
		Popup
	} from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { getCommunes } from '#lib/socle/communes.js';
	import type { Commune } from '#lib/types.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const SOURCE = 'hotels-de-ville';
	const MARQUEURS = 'hotels-de-ville';
	const COULEUR = '#1f3a5f';

	function versGeoJSON(communes: readonly Commune[]): GeoJSONSourceSpecification['data'] {
		return {
			type: 'FeatureCollection',
			features: communes.map((c) => ({
				type: 'Feature',
				id: c.bfs,
				geometry: { type: 'Point', coordinates: c.hotel },
				properties: { slug: c.slug, nom: c.nom, adresse: c.adresse }
			}))
		};
	}

	map.addSource(SOURCE, { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
	map.addLayer(
		{
			id: MARQUEURS,
			type: 'circle',
			source: SOURCE,
			paint: { 'circle-color': COULEUR, 'circle-stroke-color': '#fff' }
		},
		avant
	);

	/*
	 * Le marqueur de la commune ouverte est plus grand, sans calque à part : tout ce que ce calque dessine reçoit
	 * le clic, et un anneau autour du marqueur rendrait inaccessibles les dossiers voisins.
	 */
	$effect(() => {
		const ouvert: ExpressionSpecification = ['==', ['get', 'slug'], ctx.commune?.slug ?? ''];
		/** Par niveau de zoom : [zoom, valeur pour la commune ouverte, valeur pour les autres]. */
		const selon = (zooms: [number, number, number][]) =>
			[
				'interpolate',
				['linear'],
				['zoom'],
				...zooms.flatMap(([z, o, n]) => [z, ['case', ouvert, o, n]])
			] as ExpressionSpecification;
		map.setPaintProperty(MARQUEURS, 'circle-radius', selon([[8, 6, 4], [13, 10, 7], [17, 13, 10]]));
		map.setPaintProperty(MARQUEURS, 'circle-stroke-width', selon([[8, 2.5, 1.5], [13, 3.5, 2.5], [17, 3.5, 2.5]]));
	});

	onMount(() => {
		let detruit = false;
		let bulle: Popup | undefined;

		getCommunes(fetch)
			.then((communes) => {
				if (!detruit) (map.getSource(SOURCE) as GeoJSONSource).setData(versGeoJSON(communes));
			})
			.catch(() => {
				/* l'index des communes est déjà chargé par la coquille : un échec ici ne se produit pas */
			});

		function survol(e: MapLayerMouseEvent) {
			const f = e.features?.[0];
			if (!f || !bulle) return;
			const { nom, adresse } = f.properties as { nom: string; adresse: string };
			const contenu = document.createElement('div');
			contenu.className = 'bulle-hotel';
			const titre = document.createElement('strong');
			titre.textContent = nom;
			contenu.append(titre);
			if (adresse) {
				const ligne = document.createElement('span');
				ligne.textContent = adresse;
				contenu.append(ligne);
			}
			map.getCanvas().style.cursor = 'pointer';
			bulle
				.setLngLat((f.geometry as { coordinates: [number, number] }).coordinates)
				.setDOMContent(contenu)
				.addTo(map);
		}

		function quitter() {
			map.getCanvas().style.cursor = '';
			bulle?.remove();
		}

		function clic(e: MapLayerMouseEvent) {
			const slug = e.features?.[0]?.properties?.slug;
			quitter();
			if (typeof slug === 'string') ctx.ouvrir({ commune: slug });
		}

		import('maplibre-gl').then(({ Popup }) => {
			if (!detruit) bulle = new Popup({ closeButton: false, closeOnClick: false, offset: 10 });
		});
		map.on('mousemove', MARQUEURS, survol);
		map.on('mouseleave', MARQUEURS, quitter);
		map.on('click', MARQUEURS, clic);
		// La carte qui vole vers une commune emporte le marqueur sous la souris sans `mouseleave`.
		map.on('movestart', quitter);

		return () => {
			detruit = true;
			bulle?.remove();
			// La carte du socle a pu être détruite avant cette couche (fin de la coquille).
			try {
				map.off('mousemove', MARQUEURS, survol);
				map.off('mouseleave', MARQUEURS, quitter);
				map.off('click', MARQUEURS, clic);
				map.off('movestart', quitter);
				map.removeLayer(MARQUEURS);
				map.removeSource(SOURCE);
			} catch {
				/* carte déjà détruite */
			}
		};
	});
</script>

<style>
	:global(.bulle-hotel) {
		display: flex;
		flex-direction: column;
		gap: 2px;
		font-size: 13px;
	}
	:global(.bulle-hotel span) {
		color: var(--muted);
	}
</style>
