<script lang="ts">
	// La carte et la fiche de la commune sont dans la coquille (../../+layout.svelte) : cette page ne porte que le <head>.
	import { COUCHES } from '#lib/registre/couches.js';
	import { canonique, cheminCommune } from '#lib/indexation.js';
	import { registreCourant } from '#lib/registre/registre.svelte.js';
	import { teteCommune } from '#lib/registre/tete.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const registre = registreCourant();
	const tete = $derived(teteCommune(data.commune, COUCHES));
</script>

<svelte:head>
	<!-- Le titre suit la fiche ouverte (« Dossier n° 248845 – Lutry – Vigie Vaud ») ; la page pré-générée porte celui de la commune. -->
	<title>{registre.titre ?? tete.titre}</title>
	<meta name="description" content={tete.description} />
	<meta property="og:title" content={tete.titre} />
	<meta property="og:description" content={tete.description} />
	<!-- Sans paramètres : un lien partagé ou indexé mène à la commune, pas à une vue de la carte. -->
	<link rel="canonical" href={canonique(cheminCommune(data.commune.slug))} />
</svelte:head>
