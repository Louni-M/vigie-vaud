<script lang="ts">
	import { onMount } from 'svelte';
	import { dateLongue, joursRestants } from '#lib/dates.js';

	let { fin, compact = false }: { fin?: string; compact?: boolean } = $props();

	// Calculé dans le navigateur : une page pré-générée serait sinon figée au jour du build.
	let jours: number | null = $state(null);
	onMount(() => (jours = joursRestants(fin)));

	// Formulation neutre : le délai sert d'abord à consulter le dossier.
	const reste = (j: number) => (j === 1 ? 'encore 1 jour' : `encore ${j} jours`);
</script>

{#if fin}
	{#if jours === null}
		<span class="compte">Enquête jusqu’au {dateLongue(fin)}</span>
	{:else if jours < 0}
		<span class="compte fini">Enquête terminée le {dateLongue(fin)}</span>
	{:else if compact}
		<span class="compte">
			{jours === 0 ? 'Fin d’enquête aujourd’hui' : jours === 1 ? 'Fin d’enquête demain' : `Fin d’enquête dans ${jours} jours`}
		</span>
	{:else}
		<span class="compte">
			{#if jours === 0}
				Dernier jour de l’enquête publique ({dateLongue(fin)}) : le dossier est consultable à la commune.
			{:else}
				Enquête publique jusqu’au {dateLongue(fin)} ({reste(jours)}) : le dossier est consultable à la
				commune pendant ce délai.
			{/if}
		</span>
	{/if}
{/if}

<style>
	.compte {
		color: var(--enquete-texte);
		font-weight: 500;
	}
	.fini {
		color: var(--muted);
		font-weight: 400;
	}
</style>
