<script lang="ts">
	/*
	 * « Objets récents » d'un conseil : les 8 derniers, puis « Tous les objets (n) », qui les montre tous et lit
	 * l'année suivante ; ensuite, une année à la fois. Les listes sont lues par année (`objetsRecents`,
	 * `objetsSuivants`). Avec `puces` (fiche du Grand Conseil) : « Tous · Nomment une commune · Sans commune »
	 * filtrent les Objets déjà lus, par leurs communes rattachées.
	 */
	import { untrack } from 'svelte';
	import type { ConseilIndexe } from '#lib/schema.js';
	import type { Commune } from '#lib/types.js';
	import { conseils, OBJETS_RECENTS, type PageObjets } from './donnees.js';
	import { COULEUR_CONSEILS } from './index.js';
	import LigneObjet from './LigneObjet.svelte';
	import { filtrerObjets, PUCES_OBJETS, type PuceObjets } from './lignes.js';

	let {
		conseil,
		ouvrir,
		puces = false,
		communes = []
	}: {
		conseil: ConseilIndexe;
		ouvrir?: (cle: string) => void;
		puces?: boolean;
		/** L'index des communes, pour nommer celles que nomment les Objets du Grand Conseil. */
		communes?: readonly Commune[];
	} = $props();

	let puce = $state<PuceObjets>('tous');

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

	const filtres = $derived(page ? filtrerObjets(page.objets, puce) : []);
	const montres = $derived(tous ? filtres : filtres.slice(0, OBJETS_RECENTS));
	const resteAMontrer = $derived(page !== null && (filtres.length > OBJETS_RECENTS || page.suivante !== null));
</script>

<section aria-labelledby="objets-{conseil.cle}" style:--c={COULEUR_CONSEILS}>
	<h4 id="objets-{conseil.cle}">Objets récents</h4>
	{#if puces}
		<div class="puces" role="group" aria-label="Communes nommées">
			{#each PUCES_OBJETS as p (p.id)}
				<button type="button" aria-pressed={puce === p.id} onclick={() => (puce = p.id)}>{p.nom}</button>
			{/each}
		</div>
	{/if}
	{#if echec}
		<p class="erreur" role="alert">
			Les objets n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
		</p>
	{:else if !page}
		<p class="note" aria-busy="true">Lecture des objets…</p>
	{:else if page.objets.length === 0}
		<p class="note">Aucun objet.</p>
	{:else if montres.length === 0 && page.suivante === null}
		<p class="note">Aucun objet {puce === 'avec' ? 'ne nomme une commune' : 'sans commune'}.</p>
	{:else}
		<ul>
			{#each montres as objet (objet.cle)}<LigneObjet {objet} {ouvrir} {communes} />{/each}
		</ul>
		{#if !tous && resteAMontrer}
			<button class="plus" type="button" onclick={toutMontrer}>
				Tous les objets{puce === 'tous' ? ` (${conseil.objets})` : ''}
			</button>
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
	.puces {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin: 4px 0;
	}
	.puces button {
		padding: 3px 9px;
		border: 1px solid var(--c);
		border-radius: 999px;
		background: var(--surface);
		font: inherit;
		font-size: 12px;
		color: var(--c);
		cursor: pointer;
	}
	.puces button[aria-pressed='true'] {
		background: var(--c);
		color: #fff;
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
		.puces button,
		.plus,
		.petit {
			min-height: 44px;
		}
	}
</style>
