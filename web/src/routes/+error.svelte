<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';

	const introuvable = $derived(page.status === 404);
	// Message de nos fonctions load (« Dossier introuvable »…) ; celui de SvelteKit est en anglais (« Not Found »).
	const titre = $derived(
		introuvable
			? page.error?.message && page.error.message !== 'Not Found'
				? page.error.message
				: 'Page introuvable'
			: 'Une erreur est survenue'
	);
</script>

<svelte:head>
	<title>{titre} – Vigie Vaud</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="page">
	<h1>{titre}</h1>
	{#if introuvable && page.route.id === '/dossier/[id]'}
		<p>
			Ce numéro ne correspond à aucun dossier des données actuelles. Les numéros de dossier CAMAC comptent 5 ou 6
			chiffres ; un dossier très récent peut n’apparaître qu’à la prochaine mise à jour quotidienne.
		</p>
	{:else if introuvable}
		<p>Cette adresse ne correspond à aucune page du site.</p>
	{:else}
		<p>La page n’a pas pu être affichée ({page.status}). Réessayez dans un instant.</p>
	{/if}
	<p class="actions">
		<a class="bouton" href={resolve('/(carte)')}>Retour à la carte</a>
	</p>
</main>

<style>
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
</style>
