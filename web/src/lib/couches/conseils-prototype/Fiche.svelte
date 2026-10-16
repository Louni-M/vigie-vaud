<script lang="ts">
	// PROTOTYPE (ticket #51) : la fiche d'un objet ou d'une séance, dans l'onglet Conseil de sa commune.
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { charger, conseils, element } from './donnees.svelte.js';
	import FicheElement from './FicheElement.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	charger(untrack(() => ctx.communes));
	const x = $derived(element(ctx.ouvert?.element ?? ''));
	const nom = (s: string) => ctx.communes.find((c) => c.slug === s)?.nom ?? s;
</script>

{#if x}
	<FicheElement {x} {nom} ouvrir={(id) => ctx.ouvrir({ couche: 'conseils', element: id })} />
{:else if conseils.charge}
	<p>Élément inconnu.</p>
{/if}
