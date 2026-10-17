<script lang="ts">
	/* PROTOTYPE : aperçu sur téléphone, la carte de l'élément de la variante ; la toucher montre la fiche. */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import ElementA from './ElementA.svelte';
	import ElementB from './ElementB.svelte';
	import ElementC from './ElementC.svelte';
	import { routes } from './donnees.svelte.js';
	import type { Parametres } from './index.js';

	let { ctx, voir }: { ctx: Contexte<Parametres>; voir: () => void } = $props();
	const id = Number(untrack(() => ctx.ouvert?.element));
	const r = $derived(routes.restriction(id));
</script>

{#if r}
	{#if ctx.parametres.variant === 'B'}
		<ElementB g={routes.groupeDe(r)} onclick={voir} />
	{:else if ctx.parametres.variant === 'C'}
		<div class="fond"><ElementC {r} onclick={voir} /></div>
	{:else}
		<ElementA {r} onclick={voir} />
	{/if}
{:else}
	<button type="button" onclick={voir}>Restriction n° {id} · Voir la fiche ›</button>
{/if}

<style>
	.fond {
		padding-left: 8px;
		border-radius: 10px;
		background: var(--surface);
		border: 1px solid var(--line);
	}
</style>
