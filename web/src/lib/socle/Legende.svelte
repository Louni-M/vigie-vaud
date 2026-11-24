<script lang="ts">
	/*
	 * La légende de la carte : un bloc dépliable posé sur la carte, qui dit ce que montre chaque marqueur visible. Les
	 * entrées viennent du registre (ce que dessinent les couches) : le socle ne fait que les montrer, en texte, chaque
	 * signe masqué aux lecteurs d'écran. Ouverte à l'arrivée sur bureau, repliée sur téléphone, où l'écran est petit ;
	 * le bouton « Légende » annonce son état.
	 */
	import type { Legende } from '#lib/registre/dessin.js';
	import type { EntreeLegende } from '#lib/registre/types.js';

	let { legende, ouverte = $bindable(true) }: { legende: Legende; ouverte?: boolean } = $props();
</script>

<section class="legende" aria-label="Légende de la carte">
	<button
		type="button"
		class="bascule"
		aria-expanded={ouverte}
		aria-controls="legende-entrees"
		onclick={() => (ouverte = !ouverte)}
	>
		Légende
	</button>
	<ul id="legende-entrees" hidden={!ouverte}>
		{#each legende.toujours as e (e.texte)}{@render entree(e)}{/each}
		{#if legende.sujet}
			<li class="sujet">{legende.sujet}</li>
			{#each legende.dessinee as e (e.texte)}{@render entree(e)}{/each}
		{/if}
	</ul>
</section>

{#snippet entree(e: EntreeLegende)}
	<li>
		<span class="signe {e.signe}" style:--c={e.couleur} aria-hidden="true"></span>
		<span>{e.texte}</span>
	</li>
{/snippet}

<style>
	.legende {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 4px;
		max-width: 280px;
		font-size: 12px;
		line-height: 1.35;
		color: var(--color-ink-2);
	}
	.bascule {
		min-height: 32px;
		padding: 4px 12px;
		border: 1px solid var(--color-rule-2);
		border-radius: var(--radius-pill);
		background: var(--color-sheet);
		font: inherit;
		font-weight: 600;
		color: var(--color-ink);
		cursor: pointer;
	}
	ul {
		display: grid;
		gap: 6px;
		margin: 0;
		padding: 8px 10px;
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		list-style: none;
	}
	ul[hidden] {
		display: none;
	}
	.sujet {
		margin-top: 2px;
		font-weight: 600;
		color: var(--color-ink);
	}
	li {
		display: flex;
		align-items: flex-start;
		gap: 8px;
	}
	.signe {
		flex: none;
		width: 18px;
		height: 14px;
		margin-top: 1px;
		box-sizing: border-box;
	}
	.rond {
		width: 12px;
		height: 12px;
		margin: 2px 3px 0;
		border-radius: 50%;
		background: var(--c);
	}
	.hotel {
		width: 14px;
		height: 14px;
		margin: 1px 2px 0;
		border-radius: 50%;
		border: 2px solid #fff;
		background: var(--c);
		box-shadow: 0 0 0 1px var(--c);
	}
	.fronton {
		clip-path: polygon(50% 0, 100% 35%, 100% 100%, 0 100%, 0 35%);
		background: var(--c);
	}
	.trait,
	.tirets {
		height: 0;
		margin-top: 7px;
		border-top: 3px solid var(--c);
	}
	.tirets {
		border-top-style: dashed;
	}
	.aplat {
		background: var(--c);
		opacity: 0.45;
	}
	@media (pointer: coarse) {
		.bascule {
			min-height: 44px;
		}
	}
</style>
