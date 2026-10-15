<script lang="ts">
	// La carte et la fiche de la commune sont dans la coquille (../../+layout.svelte) : cette page ne porte que le <head>.
	import { COUCHES } from '#lib/registre/couches.js';
	import { lienCommune } from '#lib/registre/liens.js';
	import { teteCommune } from '#lib/registre/tete.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const tete = $derived(teteCommune(data.commune, COUCHES));
</script>

<svelte:head>
	<title>{tete.titre}</title>
	<meta name="description" content={tete.description} />
	<meta property="og:title" content={tete.titre} />
	<meta property="og:description" content={tete.description} />
	<!-- Sans paramètres : la mesure d'audience (GoatCounter suit ce lien) ne reçoit pas la vue de la carte. -->
	<link rel="canonical" href={lienCommune(data.commune.slug)} />
</svelte:head>
