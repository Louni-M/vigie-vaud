<script lang="ts">
	/* PROTOTYPE, variante C : une ligne d'agenda (date à gauche, échéance en couleur). */
	import { aujourdhui, echeance, heure, joursEntre, plageTexte, SORTES, type Restriction } from './donnees.svelte.js';

	let { r, actif = false, onclick }: { r: Restriction; actif?: boolean; onclick?: () => void } = $props();

	const couleur = $derived(
		r.quand === 'en-cours' ? '#c92a2a' : joursEntre(aujourdhui(), r.debut.jour) <= 7 ? '#f08c00' : '#868e96'
	);
	const jour = (j: string) => new Date(`${j}T12:00:00Z`);
	const mois = (j: string) => jour(j).toLocaleDateString('fr-CH', { month: 'short', timeZone: 'UTC' });
</script>

<button type="button" class="ligne" class:actif {onclick} style:--c={couleur}>
	<span class="date">
		{#if r.quand === 'en-cours'}
			<small>jusqu’au</small><strong>{jour(r.fin.jour).getUTCDate()}</strong><small>{mois(r.fin.jour)}</small>
		{:else}
			<small>dès le</small><strong>{jour(r.debut.jour).getUTCDate()}</strong><small>{mois(r.debut.jour)}</small>
		{/if}
	</span>
	<span class="corps">
		<span class="quoi">
			<span class="sorte" class:tirets={r.sorte === 'deviation'}>{SORTES[r.sorte].nom}</span>
			{r.communes[0]?.commune.nom}{r.communes.length > 1 ? ` +${r.communes.length - 1}` : ''}
		</span>
		<span class="nom">{r.nom}</span>
		<span class="quand">
			{echeance(r)}
			{#if r.quand === 'a-venir' && r.debut.heure}· dès {heure(r.debut)}{:else if r.quand === 'en-cours' && r.fin.heure}· jusqu’à {heure(r.fin)}{/if}
			{#if r.plage}· la nuit, {plageTexte(r.plage)}{/if}
			{#if r.weekEnd === false}· pas le week-end{/if}
		</span>
	</span>
</button>

<style>
	.ligne {
		display: grid;
		grid-template-columns: 52px 1fr;
		gap: 10px;
		width: 100%;
		text-align: left;
		padding: 8px 10px 8px 0;
		border: 0;
		border-bottom: 1px solid var(--line);
		background: none;
		color: inherit;
		font: inherit;
		font-size: 14px;
		cursor: pointer;
	}
	.ligne:hover,
	.actif {
		background: var(--bg);
	}
	.actif {
		box-shadow: inset 3px 0 0 var(--accent);
	}
	.date {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		border-radius: 8px;
		background: color-mix(in srgb, var(--c) 14%, transparent);
		border: 1.5px solid var(--c);
		line-height: 1.05;
		padding: 4px 0;
	}
	.date strong {
		font-size: 18px;
	}
	.date small {
		font-size: 10.5px;
		color: var(--muted);
	}
	.corps {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.quoi {
		font-size: 12.5px;
		color: var(--muted);
	}
	.sorte {
		color: var(--text);
		font-weight: 600;
		border-bottom: 2px solid var(--text);
	}
	.sorte.tirets {
		border-bottom-style: dashed;
	}
	.nom {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.quand {
		font-size: 12.5px;
		color: var(--muted);
	}
</style>
