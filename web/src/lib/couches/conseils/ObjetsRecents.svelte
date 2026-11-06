<script lang="ts">
	/*
	 * « Objets récents » d'un conseil : les 8 derniers, puis « Tous les objets (n) », qui les montre tous et lit
	 * l'année suivante ; ensuite, une année à la fois. Les listes sont lues par année (`objetsRecents`,
	 * `objetsSuivants`). Avec `choisir` (fiche du Grand Conseil) : les puces « Tous · Nomment une commune · Sans
	 * commune » filtrent les Objets déjà lus, par leurs communes rattachées ; la puce choisie, `puce`, est un réglage
	 * de la couche, dans l'adresse (`?communes=`). Le bouton cliqué disparaît : le focus va à la première ligne
	 * nouvellement affichée, une fois l'année suivante lue s'il le faut. La lecture d'une année est annoncée dans une
	 * zone `aria-live` toujours présente.
	 */
	import { tick, untrack } from 'svelte';
	import { nombre } from '#lib/almanach/typographie.js';
	import type { ConseilIndexe } from '#lib/schema.js';
	import type { Commune } from '#lib/types.js';
	import { conseils, OBJETS_RECENTS, type PageObjets } from './donnees.js';
	import { focaliserLigne, focusLibre } from './focus.js';
	import { COULEUR_CONSEILS } from './index.js';
	import LigneObjet from './LigneObjet.svelte';
	import { filtrerObjets, PUCES_OBJETS, type PuceObjets } from './lignes.js';

	let {
		conseil,
		ouvrir,
		puce = 'tous',
		choisir,
		communes = [],
		niveau = 4
	}: {
		conseil: ConseilIndexe;
		ouvrir?: (cle: string) => void;
		/** La puce choisie ; sans `choisir`, toujours « Tous ». */
		puce?: PuceObjets;
		/** Montre les puces, et reçoit celle qu'on choisit. */
		choisir?: (puce: PuceObjets) => void;
		/** L'index des communes, pour nommer celles que nomment les Objets du Grand Conseil. */
		communes?: readonly Commune[];
		/** Niveau du titre « Objets récents » : 3 dans la fiche du Grand Conseil, où aucun h3 ne le précède. */
		niveau?: 3 | 4;
	} = $props();

	let section = $state<HTMLElement>();
	let liste = $state<HTMLElement>();

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

	/**
	 * Le focus va à la `i`-ième ligne, la première nouvellement affichée ; sans elle (la puce n'en garde aucune), au
	 * bouton qui lit la suite, ou au titre de la section. Seulement si le focus est perdu ou resté dans la section.
	 */
	async function focaliserApres(i: number) {
		await tick();
		if (!focusLibre(section) || focaliserLigne(liste, i)) return;
		(section?.querySelector<HTMLElement>('.plus') ?? section?.querySelector<HTMLElement>('.titre-section'))?.focus();
	}

	/** Lit l'année suivante ; avec `focus`, l'indice de la première ligne nouvelle, le focus y va une fois lue. */
	async function lireSuivante(focus: number | null) {
		if (!page || page.suivante === null) return;
		suite = 'attente';
		try {
			page = await conseils.objetsSuivants(conseil, page);
			suite = null;
		} catch {
			suite = 'echec';
			await tick();
			if (focus !== null && focusLibre(section)) section?.querySelector<HTMLElement>('.erreur button')?.focus();
			return;
		}
		if (focus !== null) focaliserApres(focus);
	}

	async function toutMontrer() {
		const avant = montres.length;
		tous = true;
		await tick();
		// Les Objets déjà lus au-delà des 8 premiers sont là tout de suite ; sinon, ceux de l'année suivante.
		const deja = montres.length > avant;
		if (deja) focaliserApres(avant);
		lireSuivante(deja ? null : avant);
	}

	const filtres = $derived(page ? filtrerObjets(page.objets, puce) : []);
	const montres = $derived(tous ? filtres : filtres.slice(0, OBJETS_RECENTS));
	const resteAMontrer = $derived(page !== null && (filtres.length > OBJETS_RECENTS || page.suivante !== null));
</script>

<section aria-labelledby="objets-{conseil.cle}" style:--c={COULEUR_CONSEILS} bind:this={section}>
	<svelte:element this={`h${niveau}`} class="titre-section" id="objets-{conseil.cle}" tabindex="-1"
		>Objets récents</svelte:element
	>
	{#if choisir}
		<div class="puces" role="group" aria-label="Communes nommées">
			{#each PUCES_OBJETS as p (p.id)}
				<button type="button" aria-pressed={puce === p.id} onclick={() => choisir(p.id)}>{p.nom}</button>
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
		<ul class="objets" bind:this={liste}>
			{#each montres as objet (objet.cle)}<LigneObjet {objet} {ouvrir} {communes} />{/each}
		</ul>
		{#if !tous && resteAMontrer}
			<button class="plus" type="button" onclick={toutMontrer}>
				Tous les objets{puce === 'tous' ? ` (${nombre.format(conseil.objets)})` : ''}
			</button>
		{:else if tous && suite === 'echec'}
			<p class="erreur" role="alert">
				Les objets de {page.suivante} n’ont pas pu être chargés.
				<button class="bouton secondaire petit" type="button" onclick={() => lireSuivante(montres.length)}>
					Réessayer
				</button>
			</p>
		{:else if tous && suite === null && page.suivante !== null}
			<button class="plus" type="button" onclick={() => lireSuivante(montres.length)}>
				Objets de {page.suivante} ({nombre.format(conseil.objets_par_annee[page.suivante] ?? 0)})
			</button>
		{/if}
	{/if}
	<!-- Toujours présente, pour que la lecture d'une année soit annoncée ; vide, elle ne prend pas de place. -->
	<p class="note lecture" role="status" aria-live="polite">
		{#if page && tous && suite === 'attente'}Lecture des objets de {page.suivante}…{/if}
	</p>
</section>

<style>
	.titre-section {
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
	.puces button:hover {
		background: color-mix(in oklab, var(--c), white 88%);
	}
	.puces button[aria-pressed='true'] {
		background: var(--c);
		color: #fff;
	}
	.puces button[aria-pressed='true']:hover {
		background: color-mix(in oklab, var(--c), black 18%);
	}
	/*
	 * Une liste qui grossit d'une année à chaque clic : les lignes hors de l'écran ne sont pas mises en page. Sur le
	 * lien de la ligne et non sur le `li`, dont le confinement couperait l'anneau du focus.
	 */
	.objets > :global(li > .ligne) {
		content-visibility: auto;
		contain-intrinsic-size: auto 88px;
	}
	.lecture:empty {
		margin: 0;
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
	.plus:hover {
		text-decoration: underline;
	}
	@media (pointer: coarse) {
		.puces button,
		.plus,
		.petit {
			min-height: 44px;
		}
	}
</style>
