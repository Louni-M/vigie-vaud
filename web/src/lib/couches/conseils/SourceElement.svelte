<script lang="ts">
	/* La source, au pied de la fiche d'un Objet ou d'une Séance : l'attribution de la source de son conseil. */
	import { piedDeFiche } from './source.js';

	let { conseil }: { conseil: string } = $props();

	const pied = $derived(piedDeFiche(conseil));
</script>

{#if pied}
	<p class="source"><a href={pied.lien} target="_blank" rel="noopener">{pied.texte}</a></p>
{/if}

<style>
	.source {
		margin: 0;
		font-size: 12px;
		color: var(--muted);
	}
	.source a {
		color: inherit;
	}
</style>
