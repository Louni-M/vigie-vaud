<script lang="ts">
	// La carte et ses couches sont dans la coquille (+layout.svelte) : cette page ne porte que le <head>.
	import { resolve } from '$app/paths';
</script>

<svelte:head>
	<title>Carte des mises à l’enquête du canton de Vaud – Vigie Vaud</title>
	<meta
		name="description"
		content="Toutes les demandes de permis de construire du canton de Vaud sur une carte : enquêtes publiques en cours, dates de consultation des dossiers, historique depuis 1999."
	/>
	<!-- Sans paramètres : la mesure d'audience (GoatCounter suit ce lien) ne reçoit pas le centre de la carte. -->
	<link rel="canonical" href={resolve('/(carte)')} />
</svelte:head>
