<script lang="ts">
	/*
	 * Carte d'un dossier dans une liste : un lien quand elle a une adresse, sinon un bouton. Chacun porte son rôle
	 * natif ; le contenu, commun, est un extrait.
	 */
	import { STATUTS, natureLabel } from '#lib/labels.js';
	import { dateCourte } from '#lib/dates.js';
	import type { Dossier } from '#lib/types.js';
	import Compte from './Compte.svelte';

	let {
		d,
		actif = false,
		href,
		onclick
	}: { d: Dossier; actif?: boolean; href?: string; onclick?: () => void } = $props();
</script>

{#snippet contenu()}
	<span class="haut">
		<span class="pastille" style:background={STATUTS[d.statut].couleur}></span>
		<span class="statut">{STATUTS[d.statut].court}</span>
		<span class="commune">{d.commune}</span>
	</span>
	<span class="nature">{natureLabel(d.nature)}</span>
	<span class="desc">{d.description ?? 'Sans description'}</span>
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
	<a {href} class="carte" class:actif {onclick}>{@render contenu()}</a>
{:else}
	<button type="button" class="carte" class:actif {onclick}>{@render contenu()}</button>
{/if}

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		text-align: left;
		padding: 10px 12px;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: var(--surface);
		color: inherit;
		text-decoration: none;
		font: inherit;
		cursor: pointer;
	}
	.carte:hover,
	.actif {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
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
		color: var(--muted);
	}
	.nature {
		font-weight: 600;
		font-size: 14px;
	}
	.desc {
		font-size: 13.5px;
		line-height: 1.35;
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	.muted {
		color: var(--muted);
	}
</style>
