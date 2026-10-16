<script lang="ts">
	// PROTOTYPE (ticket #51) : aperçu d'un objet ou d'une séance, en bas de la carte sur téléphone.
	import type { Contexte } from '#lib/registre/types.js';
	import { dateDe, element, jourCourt, nomConseil } from './donnees.svelte.js';

	let { ctx, voir }: { ctx: Contexte<undefined>; voir: () => void } = $props();
	const x = $derived(element(ctx.ouvert?.element ?? ''));
</script>

<button type="button" class="apercu" onclick={voir}>
	{#if x}
		<span class="meta">{x.type} · {nomConseil(x)} · {jourCourt.format(dateDe(x))}</span>
		<span class="titre">{x.titre}</span>
	{/if}
	<span class="voir">{ctx.commune?.nom} · Voir la fiche ›</span>
</button>

<style>
	.apercu { display: grid; gap: 3px; width: 100%; padding: 10px 14px; border: 0; border-radius: 10px; background: var(--surface); font: inherit; text-align: left; cursor: pointer; }
	.meta { font-size: 12px; color: #0b7285; font-weight: 600; }
	.titre { font-size: 15px; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
	.voir { font-size: 14px; color: var(--accent); font-weight: 600; }
</style>
