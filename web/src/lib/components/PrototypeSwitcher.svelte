<script lang="ts">
	// PROTOTYPE jetable : barre flottante pour passer d'une variante à l'autre (?variant=), absente des builds de production.
	import type { Snippet } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	let { variantes, children }: { variantes: { cle: string; nom: string }[]; children?: Snippet } = $props();

	const courante = $derived(
		Math.max(0, variantes.findIndex((v) => v.cle === (page.url.searchParams.get('variant') ?? variantes[0].cle)))
	);

	function aller(pas: number) {
		const v = variantes[(courante + pas + variantes.length) % variantes.length];
		const q = new URLSearchParams(page.url.search);
		q.set('variant', v.cle);
		goto(`${page.url.pathname}?${q}`, { replace: true, reset: false });
	}

	function clavier(e: KeyboardEvent) {
		const t = e.target as HTMLElement;
		if (t.closest('input, textarea, select, [contenteditable]')) return;
		if (e.key === 'ArrowLeft') aller(-1);
		if (e.key === 'ArrowRight') aller(1);
	}
</script>

<svelte:window onkeydown={clavier} />

{#if import.meta.env.DEV}
	<div class="barre">
		<button type="button" onclick={() => aller(-1)} aria-label="Variante précédente">←</button>
		<span><strong>{variantes[courante].cle}</strong> ({variantes[courante].nom})</span>
		<button type="button" onclick={() => aller(1)} aria-label="Variante suivante">→</button>
		{#if children}<span class="sep"></span>{@render children()}{/if}
	</div>
{/if}

<style>
	.barre {
		position: fixed;
		z-index: 1000;
		left: 50%;
		bottom: 14px;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 10px;
		max-width: calc(100vw - 16px);
		padding: 6px 10px;
		border-radius: 999px;
		background: #111;
		color: #fff;
		font: 13px system-ui, sans-serif;
		box-shadow: 0 6px 20px rgb(0 0 0 / 0.35);
		white-space: nowrap;
		overflow-x: auto;
	}
	/* Sur téléphone, le bas de l'écran appartient aux tiroirs : la barre passe en haut. */
	@media (max-width: 760px) {
		.barre {
			bottom: auto;
			top: 4px;
			font-size: 11px;
			gap: 6px;
		}
	}
	button {
		width: 30px;
		height: 30px;
		border: 0;
		border-radius: 50%;
		background: #333;
		color: #fff;
		font-size: 15px;
		cursor: pointer;
	}
	.sep {
		width: 1px;
		align-self: stretch;
		background: #444;
	}
</style>
