<script lang="ts">
	/*
	 * « Séances passées » d'un conseil, lues dans `conseils/<cle>/seances.json` : les 4 dernières d'avant
	 * aujourd'hui (à Lausanne), puis « Toutes les séances (n) ».
	 */
	import { untrack } from 'svelte';
	import { jourDe } from '#lib/fil/fil.js';
	import type { ConseilIndexe, LigneSeance } from '#lib/schema.js';
	import { conseils } from './donnees.js';
	import LigneSeanceC from './LigneSeance.svelte';
	import { seancesPassees } from './lignes.js';

	let { conseil, ouvrir }: { conseil: ConseilIndexe; ouvrir?: (cle: string) => void } = $props();

	/** Séances montrées d'emblée. */
	const DERNIERES = 4;

	let passees = $state.raw<LigneSeance[] | null>(null);
	let echec = $state(false);
	let toutes = $state(false);

	function charger() {
		echec = false;
		conseils.seances(conseil.cle).then(
			(l) => (passees = seancesPassees(l.seances, jourDe(new Date()))),
			() => (echec = true)
		);
	}
	untrack(charger);
</script>

<section aria-labelledby="seances-{conseil.cle}">
	<h4 id="seances-{conseil.cle}">Séances passées</h4>
	{#if echec}
		<p class="erreur" role="alert">
			Les séances n’ont pas pu être chargées.
			<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
		</p>
	{:else if !passees}
		<p class="note" aria-busy="true">Lecture des séances…</p>
	{:else if passees.length === 0}
		<p class="note">Aucune séance passée.</p>
	{:else}
		<ul>
			{#each toutes ? passees : passees.slice(0, DERNIERES) as seance (seance.cle)}
				<LigneSeanceC {seance} {ouvrir} />
			{/each}
		</ul>
		{#if !toutes && passees.length > DERNIERES}
			<button class="plus" type="button" onclick={() => (toutes = true)}>Toutes les séances ({passees.length})</button>
		{/if}
	{/if}
</section>

<style>
	h4 {
		margin: 18px 0 2px;
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--muted);
	}
	ul {
		margin: 0;
		padding: 0;
	}
	.note {
		margin: 4px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	.erreur {
		margin: 4px 0 0;
		color: var(--erreur);
	}
	.petit {
		margin-left: 6px;
		padding: 6px 10px;
		font-size: 13px;
	}
	.plus {
		margin-top: 6px;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		font-size: 13px;
		color: var(--accent);
		cursor: pointer;
	}
	@media (pointer: coarse) {
		.plus,
		.petit {
			min-height: 44px;
		}
	}
</style>
