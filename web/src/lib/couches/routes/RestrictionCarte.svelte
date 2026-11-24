<script lang="ts">
	/*
	 * La carte d'une restriction de circulation, partagée par l'onglet Routes, la liste du volet et l'aperçu sur
	 * téléphone : la sorte et ses communes, le nom de la source, la période, l'échéance et la plage de nuit, la
	 * remarque sur une ligne coupée. Sans `onclick`, elle ne s'ouvre pas. Rendue dans le navigateur seulement (les
	 * restrictions y sont lues) : l'échéance est comptée depuis le jour du visiteur, à Lausanne.
	 */
	import type { Snippet } from 'svelte';
	import { typographier } from '#lib/almanach/typographie.js';
	import { jourDe } from '#lib/dates.js';
	import { carteRestriction } from './cartes.js';
	import type { Restriction } from './donnees.svelte.js';

	let {
		r,
		commune,
		actif = false,
		enListe = false,
		onclick,
		children
	}: {
		r: Restriction;
		/** Slug de la commune de l'onglet : la carte y dit la longueur parcourue quand il y en a plusieurs. */
		commune?: string;
		actif?: boolean;
		/** Dans une liste, une ligne réglée quand elle s'ouvre ; seule (l'aperçu du téléphone), une carte encadrée. */
		enListe?: boolean;
		onclick?: () => void;
		/** Une dernière ligne propre à l'endroit (« Voir la fiche › » de l'aperçu sur téléphone). */
		children?: Snippet;
	} = $props();

	const c = $derived(carteRestriction(r, { aujourdhui: jourDe(new Date()), commune }));
</script>

<!-- Un vrai bouton quand elle s'ouvre, sans rôle ARIA à ajouter ; sinon un simple bloc. -->
{#if onclick}
	<button
		type="button"
		class="carte ouvrable"
		class:actif
		class:en-liste={enListe}
		class:avenir={c.aVenir}
		style:--c={c.couleur}
		{onclick}
	>
		{@render contenu()}
	</button>
{:else}
	<div class="carte" class:actif class:avenir={c.aVenir} style:--c={c.couleur}>{@render contenu()}</div>
{/if}

{#snippet contenu()}
	<span class="haut">
		<span class="trait" class:tirets={c.tirets}></span>
		<strong>{c.sorte}</strong>
		{#if c.aVenir}<span class="etiquette">À venir</span>{/if}
		{#if c.communes}<span class="communes">{typographier(c.communes)}</span>{/if}
	</span>
	<span class="quand">
		<span>{c.periode}</span>
		<span class="muted">· {c.echeance}</span>
		{#if c.plage}<span class="plage">· {c.plage}</span>{/if}
	</span>
	{#if c.remarque}<span class="remarque" title={typographier(c.remarque)}>{typographier(c.remarque)}</span>{/if}
	<span class="bas">
		{#if c.dansLaCommune}<span>{c.dansLaCommune}</span>{/if}
		<span class="source">{c.source}</span>
	</span>
	{@render children?.()}
{/snippet}

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 3px;
		width: 100%;
		min-width: 0;
		text-align: left;
		padding: 10px 12px;
		border: 1px solid var(--color-rule);
		border-left: 4px solid var(--c);
		border-radius: 10px;
		background: var(--color-sheet);
		color: inherit;
		font: inherit;
		font-size: 13.5px;
	}
	.ouvrable {
		cursor: pointer;
	}
	.ouvrable:hover,
	.actif {
		border-color: var(--color-rule-2);
		border-left-color: var(--c);
		box-shadow: 0 0 0 1px var(--color-rule-2);
	}
	.actif:hover {
		box-shadow: 0 0 0 2px var(--color-rule-2);
	}
	.avenir {
		border-left-style: dashed;
	}
	.haut {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
	}
	.trait {
		flex: none;
		width: 18px;
		height: 4px;
		border-radius: 2px;
		background: var(--c);
	}
	.trait.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 5px, transparent 5px 8px);
	}
	.etiquette {
		padding: 1px 6px;
		border-radius: 4px;
		background: var(--color-paper);
		border: 1px solid var(--color-rule);
		font-size: 11.5px;
	}
	.communes {
		margin-left: auto;
		color: var(--color-muted);
		text-align: right;
	}
	.quand {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.plage {
		color: #5f3dc4;
	}
	/* Sans largeur propre (`contain`) : la ligne entière élargirait la carte, et la grille du volet avec elle. */
	.remarque {
		contain: inline-size;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--color-muted);
	}
	.bas {
		display: flex;
		gap: 6px;
		font-size: 12px;
		color: var(--color-muted);
	}
	.source {
		margin-left: auto;
	}
	/* Dans une liste, plus de carte encadrée : une ligne réglée par restriction ; celle survolée ou ouverte est posée
	   sur le papier et marquée d'un trait orange. */
	.en-liste {
		padding: var(--space-sm) var(--space-xs) var(--space-sm) var(--space-sm);
		border: 0;
		border-radius: 0;
		background: none;
	}
	.en-liste:hover,
	.en-liste.actif {
		border: 0;
		background: var(--color-paper);
		box-shadow: inset var(--rule-bar) 0 0 var(--color-accent);
	}
	/* La restriction ouverte, survolée : le papier fonce d'un ton. */
	.en-liste.actif:hover {
		background: var(--color-paper-2);
	}
</style>
