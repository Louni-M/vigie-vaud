<script lang="ts">
	// La carte et ses couches sont dans la coquille (+layout.svelte) : cette page ne porte que le <head>.
	import { canonique } from '#lib/indexation.js';
</script>

<svelte:head>
	<title>Carte des mises à l’enquête du canton de Vaud – Vigie Vaud</title>
	<meta
		name="description"
		content="Toutes les demandes de permis de construire du canton de Vaud sur une carte : enquêtes publiques en cours, dates de consultation des dossiers, historique depuis 1999."
	/>
	<!-- Sans paramètres : un lien partagé ou indexé mène à la carte, pas à son centre du moment. -->
	<link rel="canonical" href={canonique('/')} />
</svelte:head>
