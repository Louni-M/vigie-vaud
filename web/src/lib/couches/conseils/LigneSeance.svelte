<script lang="ts">
	/*
	 * Une ligne de Séance : pastille cerclée, sa date et son nombre de points, puis son nom composé (« Séance du
	 * mardi 6 octobre 2026 », avec l'heure si elle est connue). Sans `ouvrir`, la ligne n'est pas cliquable.
	 * Une Séance sans points montre ses documents en lien à la place du nombre de points ; un lien ne pouvant être
	 * dans un bouton, c'est alors son nom qui ouvre la Séance.
	 */
	import type { LigneSeance } from '#lib/schema.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { dateSeance, detailSeance, nomSeance } from './lignes.js';

	let { seance, ouvrir }: { seance: LigneSeance; ouvrir?: (cle: string) => void } = $props();

	const detail = $derived(detailSeance(seance));
</script>

<li style:--c={COULEUR_CONSEILS}>
	{#if 'documents' in detail}
		<div class="ligne">
			<span class="meta">
				<span class="pastille" aria-hidden="true"></span>{dateSeance(seance.date)}
				{#each detail.documents as d, i (i)}
					<span>· <a href={d.lien} target="_blank" rel="noopener">{d.texte}</a></span>
				{/each}
			</span>
			{#if ouvrir}
				<button type="button" class="titre nom" onclick={() => ouvrir(seance.cle)}>{nomSeance(seance.date)}</button>
			{:else}
				<span class="titre">{nomSeance(seance.date)}</span>
			{/if}
		</div>
	{:else if ouvrir}
		<button type="button" class="ligne" onclick={() => ouvrir(seance.cle)}>{@render contenu(detail.points)}</button>
	{:else}
		<div class="ligne">{@render contenu(detail.points)}</div>
	{/if}
</li>

{#snippet contenu(points: string)}
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
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		font-weight: 600;
		color: var(--c);
	}
	.meta a {
		color: var(--accent);
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
	.nom {
		justify-self: start;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		font-size: 14px;
		text-align: left;
		color: inherit;
		cursor: pointer;
	}
	.nom:hover {
		text-decoration: underline;
	}
</style>
