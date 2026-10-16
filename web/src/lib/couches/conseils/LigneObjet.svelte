<script lang="ts">
	/*
	 * Une ligne d'Objet, dans l'onglet Conseil et la fiche du Grand Conseil : pastille pleine, type et
	 * numéro, date ; le titre sur 3 lignes au plus ; les auteur·e·s (2, puis « et al. ») avec leur parti, et le
	 * statut. Pour un Objet du Grand Conseil, avec l'index `communes`, « → communes nommées » ; avec `origine`
	 * (dans « Au Grand Conseil »), comment il est rattaché à la commune de l'onglet. Sans `ouvrir`, la ligne n'est
	 * pas cliquable.
	 */
	import type { LigneObjet } from '#lib/schema.js';
	import type { Commune } from '#lib/types.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { auteursObjet, dateObjet } from './lignes.js';
	import { communesNommees } from './rattachements.js';

	let {
		objet,
		ouvrir,
		communes = [],
		origine = null
	}: {
		objet: LigneObjet;
		ouvrir?: (cle: string) => void;
		communes?: readonly Commune[];
		origine?: string | null;
	} = $props();

	const auteurs = $derived(auteursObjet(objet));
	const date = $derived(dateObjet(objet));
	const nommees = $derived(communesNommees(objet.communes, communes));
</script>

<li style:--c={COULEUR_CONSEILS}>
	{#if ouvrir}
		<button type="button" class="ligne" onclick={() => ouvrir(objet.cle)}>{@render contenu()}</button>
	{:else}
		<div class="ligne">{@render contenu()}</div>
	{/if}
</li>

{#snippet contenu()}
	<span class="meta"><span class="pastille" aria-hidden="true"></span>{objet.type} {objet.numero}{date ? ` · ${date}` : ''}</span>
	<span class="titre">{objet.titre}</span>
	{#if auteurs || objet.statut}
		<span class="sous">
			{auteurs}{#if objet.statut}{auteurs ? ' · ' : ''}<em>{objet.statut.libelle}</em>{/if}
		</span>
	{/if}
	{#if nommees.length}<span class="sous">→ {nommees.join(', ')}</span>{/if}
	{#if origine}<span class="origine">{origine}</span>{/if}
{/snippet}

<style>
	li {
		list-style: none;
		border-bottom: 1px solid var(--line);
	}
	.ligne {
		display: grid;
		gap: 2px;
		width: 100%;
		box-sizing: border-box;
		padding: 7px 4px;
		border: 0;
		background: none;
		font: inherit;
		text-align: left;
		color: inherit;
	}
	button.ligne {
		cursor: pointer;
	}
	button.ligne:hover {
		background: var(--bg);
	}
	.meta {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		font-weight: 600;
		color: var(--c);
	}
	.pastille {
		flex: none;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--c);
	}
	.titre {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 14px;
	}
	.sous {
		font-size: 12px;
		color: var(--muted);
	}
	.origine {
		font-size: 12px;
		font-style: italic;
		color: var(--c);
	}
</style>
