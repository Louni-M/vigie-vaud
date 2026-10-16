<script lang="ts">
	/*
	 * Une ligne de Séance : pastille cerclée, sa date et son nombre de points, puis son nom composé (« Séance du
	 * mardi 6 octobre 2026 », avec l'heure si elle est connue). Sans `ouvrir`, la ligne n'est pas cliquable.
	 */
	import type { LigneSeance } from '#lib/schema.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { dateSeance, nomSeance } from './lignes.js';

	let { seance, ouvrir }: { seance: LigneSeance; ouvrir?: (cle: string) => void } = $props();

	const points = $derived(seance.points === 1 ? '1 point' : `${seance.points} points`);
</script>

<li style:--c={COULEUR_CONSEILS}>
	{#if ouvrir}
		<button type="button" class="ligne" onclick={() => ouvrir(seance.cle)}>{@render contenu()}</button>
	{:else}
		<div class="ligne">{@render contenu()}</div>
	{/if}
</li>

{#snippet contenu()}
	<span class="meta"><span class="pastille" aria-hidden="true"></span>{dateSeance(seance.date)} · {points}</span>
	<span class="titre">{nomSeance(seance.date)}</span>
{/snippet}

<style>
	li {
		list-style: none;
		border-bottom: 1px solid var(--line);
	}
	.ligne {
		display: grid;
		gap: 2px;
		width: 100%;
		box-sizing: border-box;
		padding: 7px 4px;
		border: 0;
		background: none;
		font: inherit;
		text-align: left;
		color: inherit;
	}
	button.ligne {
		cursor: pointer;
	}
	button.ligne:hover {
		background: var(--bg);
	}
	.meta {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		font-weight: 600;
		color: var(--c);
	}
	.pastille {
		flex: none;
		width: 10px;
		height: 10px;
		box-sizing: border-box;
		border-radius: 50%;
		border: 2px solid var(--c);
	}
	.titre {
		font-size: 14px;
	}
</style>
