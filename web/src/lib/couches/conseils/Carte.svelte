<script lang="ts">
	/*
	 * Carte de la couche Conseils : le seul marqueur du Grand Conseil, un fronton sarcelle, au Parlement. Aux petits
	 * zooms, il est décalé à l'écran vers le nord-est, pour qu'on puisse cliquer aussi sur l'hôtel de ville de Lausanne
	 * tout proche ; le décalage s'annule vers le zoom 14. C'est un calque de la carte, et non un marqueur HTML : les
	 * hôtels de ville, dessinés au-dessus de toutes les couches, restent ainsi au-dessus de lui. Fondu à l'activation.
	 * Le clic viendra avec la fiche du Grand Conseil.
	 */
	import { onMount, untrack } from 'svelte';
	import type { ExpressionSpecification } from 'maplibre-gl';
	import type { Contexte } from '#lib/registre/types.js';
	import { retirerDeLaCarte } from '#lib/socle/carte.js';
	import { COULEUR_CONSEILS, PARLEMENT } from './index.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	const map = untrack(() => ctx.map);
	const avant = untrack(() => ctx.avant);
	const SOURCE = 'conseils-grand-conseil';
	const MARQUEUR = 'conseils-grand-conseil';
	const IMAGE = 'conseils-fronton';
	const FONDU = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 350;

	/** Décalage à l'écran (px), du zoom du canton au zoom 14 où il s'annule : une quinzaine de pixels vers le nord-est. */
	const DECALAGE: ExpressionSpecification = [
		'interpolate',
		['linear'],
		['zoom'],
		8,
		['literal', [11, -11]],
		14,
		['literal', [0, 0]]
	];

	/**
	 * Le fronton du Parlement, sarcelle à liseré blanc, avec « GC » : 34 × 30 px, plus une marge pour l'ombre.
	 * Dessiné au double de la résolution, pour les écrans à haute densité.
	 */
	function fronton(): { image: ImageData; marge: number } {
		const r = 2;
		const [l, h, marge] = [34, 30, 4];
		const canvas = document.createElement('canvas');
		canvas.width = (l + 2 * marge) * r;
		canvas.height = (h + 2 * marge) * r;
		const g = canvas.getContext('2d')!;
		g.scale(r, r);
		g.translate(marge, marge);
		g.beginPath();
		g.moveTo(l / 2, 1);
		g.lineTo(l - 1, h * 0.3);
		g.lineTo(l - 1, h - 1);
		g.lineTo(1, h - 1);
		g.lineTo(1, h * 0.3);
		g.closePath();
		g.shadowColor = 'rgb(0 0 0 / 0.35)';
		g.shadowBlur = 4;
		g.shadowOffsetY = 1;
		g.fillStyle = COULEUR_CONSEILS;
		g.fill();
		g.shadowColor = 'transparent';
		g.lineJoin = 'round';
		g.lineWidth = 2;
		g.strokeStyle = '#fff';
		g.stroke();
		g.fillStyle = '#fff';
		g.font = '700 12px system-ui, sans-serif';
		g.textAlign = 'center';
		g.textBaseline = 'middle';
		g.fillText('GC', l / 2, h * 0.64);
		return { image: g.getImageData(0, 0, canvas.width, canvas.height), marge };
	}

	const { image, marge } = fronton();
	map.addImage(IMAGE, image, { pixelRatio: 2 });
	map.addSource(SOURCE, {
		type: 'geojson',
		data: {
			type: 'FeatureCollection',
			features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: PARLEMENT }, properties: {} }]
		}
	});
	map.addLayer(
		{
			id: MARQUEUR,
			type: 'symbol',
			source: SOURCE,
			layout: {
				'icon-image': IMAGE,
				// La base du fronton sur le Parlement (sans la marge de l'ombre).
				'icon-anchor': 'bottom',
				'icon-offset': [0, marge],
				'icon-allow-overlap': true,
				'icon-ignore-placement': true
			},
			paint: {
				'icon-translate': DECALAGE,
				'icon-translate-anchor': 'viewport',
				'icon-opacity': 0,
				'icon-opacity-transition': { duration: FONDU, delay: 0 }
			}
		},
		avant
	);

	// Fondu : le marqueur apparaît ou disparaît, puis il est retiré du rendu.
	$effect(() => {
		const active = ctx.active;
		if (active) map.setLayoutProperty(MARQUEUR, 'visibility', 'visible');
		map.setPaintProperty(MARQUEUR, 'icon-opacity', active ? 1 : 0);
		if (active) return;
		const t = setTimeout(() => map.setLayoutProperty(MARQUEUR, 'visibility', 'none'), FONDU);
		return () => clearTimeout(t);
	});

	onMount(() => () => {
		retirerDeLaCarte(map, [MARQUEUR], [SOURCE]);
		if (map.style && map.hasImage(IMAGE)) map.removeImage(IMAGE);
	});
</script>
