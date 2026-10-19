<script lang="ts">
	/*
	 * La carte d'une restriction de circulation, partagée par l'onglet Routes, la liste du volet et l'aperçu sur
	 * téléphone : la sorte et ses communes, le nom de la source, la période, l'échéance et la plage de nuit, la
	 * remarque sur une ligne coupée. Sans `onclick`, elle ne s'ouvre pas. Rendue dans le navigateur seulement (les
	 * restrictions y sont lues) : l'échéance est comptée depuis le jour du visiteur, à Lausanne.
	 */
	import type { Snippet } from 'svelte';
	import { jourDe } from '#lib/fil/fil.js';
	import { carteRestriction } from './cartes.js';
	import type { Restriction } from './donnees.svelte.js';

	let {
		r,
		commune,
		actif = false,
		onclick,
		children
	}: {
		r: Restriction;
		/** Slug de la commune de l'onglet : la carte y dit la longueur parcourue quand il y en a plusieurs. */
		commune?: string;
		actif?: boolean;
		onclick?: () => void;
		/** Une dernière ligne propre à l'endroit (« Voir la fiche › » de l'aperçu sur téléphone). */
		children?: Snippet;
	} = $props();

	const c = $derived(carteRestriction(r, { aujourdhui: jourDe(new Date()), commune }));
</script>

<svelte:element
	this={onclick ? 'button' : 'div'}
	type={onclick ? 'button' : undefined}
	role={onclick ? 'button' : undefined}
	class="carte"
	class:ouvrable={!!onclick}
	class:actif
	class:avenir={c.aVenir}
	style:--c={c.couleur}
	{onclick}
>
	<span class="haut">
		<span class="trait" class:tirets={c.tirets}></span>
		<strong>{c.sorte}</strong>
		{#if c.aVenir}<span class="etiquette">À venir</span>{/if}
		{#if c.communes}<span class="communes">{c.communes}</span>{/if}
	</span>
	<span class="quand">
		<span>{c.periode}</span>
		<span class="muted">· {c.echeance}</span>
		{#if c.plage}<span class="plage">· {c.plage}</span>{/if}
	</span>
	{#if c.remarque}<span class="remarque" title={c.remarque}>{c.remarque}</span>{/if}
	<span class="bas">
		{#if c.dansLaCommune}<span>{c.dansLaCommune}</span>{/if}
		<span class="source">{c.source}</span>
	</span>
	{@render children?.()}
</svelte:element>

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 3px;
		width: 100%;
		min-width: 0;
		text-align: left;
		padding: 10px 12px;
		border: 1px solid var(--line);
		border-left: 4px solid var(--c);
		border-radius: 10px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		font-size: 13.5px;
	}
	.ouvrable {
		cursor: pointer;
	}
	.ouvrable:hover,
	.actif {
		border-color: var(--accent);
		border-left-color: var(--c);
		box-shadow: 0 0 0 1px var(--accent);
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
		background: var(--bg);
		border: 1px solid var(--line);
		font-size: 11.5px;
	}
	.communes {
		margin-left: auto;
		color: var(--muted);
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
		color: var(--muted);
	}
	.bas {
		display: flex;
		gap: 6px;
		font-size: 12px;
		color: var(--muted);
	}
	.source {
		margin-left: auto;
	}
	.muted {
		color: var(--muted);
	}
</style>
