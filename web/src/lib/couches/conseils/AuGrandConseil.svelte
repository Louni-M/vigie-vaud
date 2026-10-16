<script lang="ts">
	/*
	 * « Au Grand Conseil », à la fin de l'onglet Conseil d'une commune, couverte ou non : les Objets du Grand Conseil
	 * rattachés à la commune, par date de dernière étape décroissante, les 10 derniers puis « Tous (n) ». Chaque
	 * ligne dit comment l'Objet est rattaché à la commune (« nommée dans le titre », « citée dans un document »).
	 * Sous le titre, toujours, la mention du rattachement automatique, vers la méthode dans l'À propos. Une commune
	 * qu'aucun Objet ne nomme le dit d'après l'index seul (`auGrandConseil`) : une absence ne passe pas pour une
	 * panne.
	 */
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import type { LigneObjet as Ligne } from '#lib/schema.js';
	import type { Commune } from '#lib/types.js';
	import { conseils } from './donnees.js';
	import LigneObjet from './LigneObjet.svelte';
	import { origineDans } from './rattachements.js';

	/** Objets montrés d'emblée. */
	const PREMIERS = 10;

	let {
		commune,
		communes,
		ouvrir
	}: { commune: Commune; communes: readonly Commune[]; ouvrir?: (cle: string) => void } = $props();

	let objets = $state.raw<Ligne[] | null>(null);
	let echec = $state(false);
	let tous = $state(false);

	function charger() {
		echec = false;
		conseils.auGrandConseil(commune.bfs).then(
			(o) => (objets = o),
			() => (echec = true)
		);
	}
	untrack(charger);

	const montres = $derived(objets && !tous ? objets.slice(0, PREMIERS) : (objets ?? []));
</script>

<section aria-labelledby="au-grand-conseil">
	<h3 id="au-grand-conseil">Au Grand Conseil</h3>
	<p class="mention">
		Rattachés automatiquement par le nom de la commune : des erreurs sont possibles.
		<a href="{resolve('/a-propos')}#rattachement">En savoir plus ›</a>
	</p>
	{#if echec}
		<p class="erreur" role="alert">
			Les objets du Grand Conseil n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
		</p>
	{:else if !objets}
		<p class="note" aria-busy="true">Lecture des objets du Grand Conseil…</p>
	{:else if objets.length === 0}
		<p class="note">Aucun objet du Grand Conseil ne nomme {commune.nom}.</p>
	{:else}
		<ul>
			{#each montres as objet (objet.cle)}
				<LigneObjet {objet} {ouvrir} {communes} origine={origineDans(objet, commune.bfs)} />
			{/each}
		</ul>
		{#if !tous && objets.length > PREMIERS}
			<button class="plus" type="button" onclick={() => (tous = true)}>Tous ({objets.length})</button>
		{/if}
	{/if}
</section>

<style>
	h3 {
		margin: 0 0 2px;
		font-size: 16px;
	}
	ul {
		margin: 0;
		padding: 0;
	}
	.mention,
	.note {
		margin: 2px 0 6px;
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
