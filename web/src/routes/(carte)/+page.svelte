<script lang="ts">
	// La carte et ses couches sont dans la coquille (+layout.svelte) : cette page ne porte que le <head>.
	import { canonique } from '#lib/indexation.js';
</script>

<svelte:head>
	<title>Vigie Vaud – permis, routes, conseils communaux et Grand Conseil du canton de Vaud</title>
	<meta
		name="description"
		content="Ce qui se passe dans chaque commune du canton de Vaud, sur une carte : permis de construire à l’enquête, fermetures de routes, séances des conseils communaux et textes du Grand Conseil."
	/>
	<!-- Sans paramètres : un lien partagé ou indexé mène à la carte, pas à son centre du moment. -->
	<link rel="canonical" href={canonique('/')} />
</svelte:head>
