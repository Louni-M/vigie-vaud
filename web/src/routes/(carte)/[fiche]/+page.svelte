<script lang="ts">
	// La carte et la fiche propre sont dans la coquille (../+layout.svelte) : cette page ne porte que le <head>.
	import { canonique } from '#lib/indexation.js';
	import { registreCourant } from '#lib/registre/registre.svelte.js';
	import { teteFiche } from '#lib/registre/tete.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const registre = registreCourant();
	const tete = $derived(teteFiche(data.fiche));
</script>

<svelte:head>
	<!-- Le titre suit l'élément ouvert (« Objet 26_INT_140 – Grand Conseil – Vigie Vaud ») ; la page pré-générée porte celui de la fiche. -->
	<title>{registre.titre ?? tete.titre}</title>
	<meta name="description" content={tete.description} />
	<meta property="og:title" content={tete.titre} />
	<meta property="og:description" content={tete.description} />
	<!-- Sans paramètres : un lien partagé ou indexé mène à la fiche, pas à un élément ni à une vue de la carte. -->
	<link rel="canonical" href={canonique(data.fiche.chemin)} />
</svelte:head>
