<script lang="ts">
	/*
	 * Rail des couches : une icône par couche inscrite, dans l'ordre du registre, pleine si la couche est
	 * activée et cerclée sinon. Un clic ouvre ou ferme son volet.
	 */
	import type { Registre } from './registre.svelte.js';

	let { registre }: { registre: Registre } = $props();

	const basculer = (id: string) => (registre.volet = registre.volet === id ? null : id);
</script>

<nav class="rail" aria-label="Couches">
	{#each registre.couches as c (c.id)}
		{@const active = registre.active(c.id)}
		<button
			type="button"
			data-couche={c.id}
			class:ouvert={registre.volet === c.id}
			aria-expanded={registre.volet === c.id}
			aria-controls={registre.volet === c.id ? `volet-${c.id}` : undefined}
			title="{c.nom} : {active ? 'affichée' : 'masquée'}"
			onclick={() => basculer(c.id)}
		>
			<span class="icone" class:off={!active} style:--c={c.icone.couleur} aria-hidden="true">{c.icone.signe}</span>
			<span class="nom">{c.nom}</span>
			<span class="etat">{active ? '' : '(masquée)'}</span>
		</button>
	{/each}
</nav>

<style>
	.rail {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 8px 4px;
		background: var(--surface);
		border-right: 1px solid var(--line);
		overflow-y: auto;
	}
	button {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 8px 2px;
		border: 0;
		border-radius: 8px;
		background: none;
		font: inherit;
		font-size: 11px;
		color: var(--text);
		cursor: pointer;
		text-align: center;
	}
	button:hover {
		background: var(--bg);
	}
	button.ouvert {
		background: #e8edf5;
	}
	.icone {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: var(--c);
		color: #fff;
		font-weight: 700;
		font-size: 15px;
		transition:
			background 0.2s,
			color 0.2s;
	}
	.icone.off {
		background: var(--surface);
		color: var(--c);
		box-shadow: inset 0 0 0 2px var(--c);
	}
	/* Pour les lecteurs d'écran seulement : l'icône cerclée le dit aux yeux. */
	.etat {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
