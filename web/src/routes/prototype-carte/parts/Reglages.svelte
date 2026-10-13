<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : réglages de la couche Permis (statuts, nature, historique).
	import { NATURES, STATUTS } from '#lib/labels.js';
	import { STATUTS_EN_COURS } from '#lib/etat.js';
	import type { Statut } from '#lib/types.js';
	import type { Proto } from '../proto.svelte.js';
	let { p }: { p: Proto } = $props();
	const basculer = (s: Statut) =>
		(p.statuts = p.statuts.includes(s) ? p.statuts.filter((x) => x !== s) : [...p.statuts, s]);
</script>

<div class="reglages">
	<div class="puces">
		{#each STATUTS_EN_COURS as s (s)}
			<button type="button" class="puce" class:off={!p.statuts.includes(s)} style:--c={STATUTS[s].couleur} onclick={() => basculer(s)}>
				<span></span>{STATUTS[s].court}
			</button>
		{/each}
	</div>
	<select bind:value={p.nature} aria-label="Nature des travaux">
		<option value="">Toutes natures</option>
		{#each Object.entries(NATURES) as [k, v] (k)}<option value={k}>{v}</option>{/each}
	</select>
	<label class="histo"><input type="checkbox" disabled /> Historique depuis 1999 <small>(non branché)</small></label>
</div>

<style>
	.reglages {
		display: flex;
		flex-direction: column;
		gap: 8px;
		font-size: 13px;
	}
	.puces {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.puce {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		border-radius: 999px;
		border: 1px solid var(--c);
		background: var(--surface);
		font: inherit;
		color: inherit;
		cursor: pointer;
	}
	.puce span {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--c);
	}
	.puce.off {
		border-color: var(--line);
		color: var(--muted);
	}
	.puce.off span {
		background: transparent;
		box-shadow: inset 0 0 0 1.5px var(--c);
	}
	select {
		padding: 6px 8px;
		border-radius: 8px;
		border: 1px solid var(--line);
		background: var(--surface);
		font: inherit;
	}
	.histo {
		display: flex;
		gap: 6px;
		align-items: center;
		color: var(--muted);
	}
</style>
