<script lang="ts">
	/*
	 * « Objets récents » d'un conseil : les 8 derniers, puis « Tous les objets (n) », qui les montre tous et lit
	 * l'année suivante ; ensuite, une année à la fois. Les listes sont lues par année (`objetsRecents`,
	 * `objetsSuivants`).
	 */
	import { untrack } from 'svelte';
	import type { ConseilIndexe } from '#lib/schema.js';
	import { conseils, OBJETS_RECENTS, type PageObjets } from './donnees.js';
	import LigneObjet from './LigneObjet.svelte';

	let { conseil, ouvrir }: { conseil: ConseilIndexe; ouvrir?: (cle: string) => void } = $props();

	let page = $state.raw<PageObjets | null>(null);
	let echec = $state(false);
	let tous = $state(false);
	let suite = $state<'attente' | 'echec' | null>(null);

	function charger() {
		echec = false;
		conseils.objetsRecents(conseil).then(
			(p) => (page = p),
			() => (echec = true)
		);
	}
	untrack(charger);

	async function lireSuivante() {
		if (!page || page.suivante === null) return;
		suite = 'attente';
		try {
			page = await conseils.objetsSuivants(conseil, page);
			suite = null;
		} catch {
			suite = 'echec';
		}
	}

	function toutMontrer() {
		tous = true;
		lireSuivante();
	}

	const montres = $derived(page ? (tous ? page.objets : page.objets.slice(0, OBJETS_RECENTS)) : []);
	const resteAMontrer = $derived(page !== null && (page.objets.length > OBJETS_RECENTS || page.suivante !== null));
</script>

<section aria-labelledby="objets-{conseil.cle}">
	<h4 id="objets-{conseil.cle}">Objets récents</h4>
	{#if echec}
		<p class="erreur" role="alert">
			Les objets n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
		</p>
	{:else if !page}
		<p class="note" aria-busy="true">Lecture des objets…</p>
	{:else if page.objets.length === 0}
		<p class="note">Aucun objet.</p>
	{:else}
		<ul>
			{#each montres as objet (objet.cle)}<LigneObjet {objet} {ouvrir} />{/each}
		</ul>
		{#if !tous && resteAMontrer}
			<button class="plus" type="button" onclick={toutMontrer}>Tous les objets ({conseil.objets})</button>
		{:else if tous && suite === 'attente'}
			<p class="note" aria-busy="true">Lecture des objets de {page.suivante}…</p>
		{:else if tous && suite === 'echec'}
			<p class="erreur" role="alert">
				Les objets de {page.suivante} n’ont pas pu être chargés.
				<button class="bouton secondaire petit" type="button" onclick={lireSuivante}>Réessayer</button>
			</p>
		{:else if tous && page.suivante !== null}
			<button class="plus" type="button" onclick={lireSuivante}>
				Objets de {page.suivante} ({conseil.objets_par_annee[page.suivante]})
			</button>
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
