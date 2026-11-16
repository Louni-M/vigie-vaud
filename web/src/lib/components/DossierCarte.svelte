<script lang="ts">
	/*
	 * Carte d'un dossier dans une liste : un lien quand elle a une adresse, sinon un bouton. Chacun porte son rôle
	 * natif ; le contenu, commun, est un extrait.
	 */
	import { typographier } from '#lib/almanach/typographie.js';
	import { STATUTS, natureLabel } from '#lib/labels.js';
	import { dateCourte } from '#lib/dates.js';
	import type { Dossier } from '#lib/types.js';
	import Compte from './Compte.svelte';

	let {
		d,
		actif = false,
		enListe = false,
		href,
		onclick
	}: {
		d: Dossier;
		actif?: boolean;
		/** Dans une liste, une ligne réglée ; seule (l'aperçu du téléphone, qui flotte sur la carte), une carte encadrée. */
		enListe?: boolean;
		href?: string;
		onclick?: () => void;
	} = $props();
</script>

{#snippet contenu()}
	<span class="haut">
		<span class="pastille" style:background={STATUTS[d.statut].couleur}></span>
		<span class="statut">{STATUTS[d.statut].court}</span>
		<span class="commune">{typographier(d.commune)}</span>
	</span>
	<span class="nature">{natureLabel(d.nature)}</span>
	<span class="desc">{d.description ? typographier(d.description) : 'Sans description'}</span>
	<span class="bas">
		{#if d.statut === 'enquete'}
			<Compte fin={d.fin} compact />
		{:else}
			<span class="muted">Enquête du {dateCourte(d.debut)}</span>
		{/if}
		<span class="muted">n°&nbsp;{d.id}</span>
	</span>
{/snippet}

{#if href}
	<a {href} class="carte" class:actif class:en-liste={enListe} {onclick}>{@render contenu()}</a>
{:else}
	<button type="button" class="carte" class:actif class:en-liste={enListe} {onclick}>{@render contenu()}</button>
{/if}

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		text-align: left;
		padding: 10px 12px;
		border: 1px solid var(--color-rule);
		border-radius: 10px;
		background: var(--color-sheet);
		color: inherit;
		text-decoration: none;
		font: inherit;
		cursor: pointer;
	}
	.carte:hover,
	.actif {
		border-color: var(--color-rule-2);
		box-shadow: 0 0 0 1px var(--color-rule-2);
	}
	.actif:hover {
		box-shadow: 0 0 0 2px var(--color-rule-2);
	}
	/* Dans une liste, plus de carte encadrée : une ligne réglée par dossier ; le dossier survolé ou ouvert est posé sur
	   le papier et marqué d'un trait orange. */
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
	/* Le dossier ouvert, survolé : le papier fonce d'un ton. */
	.en-liste.actif:hover {
		background: var(--color-paper-2);
	}
	.haut,
	.bas {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
	}
	.bas {
		justify-content: space-between;
		margin-top: 4px;
	}
	.pastille {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		flex: none;
	}
	.statut {
		font-weight: 600;
	}
	.commune {
		margin-left: auto;
		color: var(--color-muted);
	}
	.nature {
		font-weight: 600;
		font-size: var(--text-md);
		color: var(--color-ink);
	}
	/* La description se lit en serif, comme un texte. */
	.desc {
		font-family: var(--font-body);
		font-size: 0.9375rem;
		line-height: 1.4;
		color: var(--color-ink-2);
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.muted {
		color: var(--color-muted);
	}
	.bas .muted:last-child {
		font-family: var(--font-outlier);
		font-size: var(--text-xs);
	}
</style>
