<script lang="ts">
	/*
	 * PROTOTYPE jetable, ticket #7 « Carte, panneau des couches et fiche commune, sur bureau et sur mobile ».
	 * Trois variantes de la carte de J0, switchables via `?variant=` sur /prototype-carte (serveur de dev seulement).
	 *   A : une colonne à gauche, couches en haut, fiches qui se remplacent.
	 *   B : carte pleine, couches en menu flottant, fiches en cartes empilées à droite.
	 *   C : rail des couches à gauche, fiche commune en colonne à droite, dossier ouvert dans l'onglet.
	 * Données réelles (dossiers en cours, communes) ; hôtels de ville au centre de l'emprise de chaque commune.
	 */
	import { page } from '$app/state';
	import PrototypeSwitcher from '#lib/components/PrototypeSwitcher.svelte';
	import { Proto } from './proto.svelte.js';
	import VariantA from './VariantA.svelte';
	import VariantB from './VariantB.svelte';
	import VariantC from './VariantC.svelte';

	const p = new Proto();
	const variantes = [
		{ cle: 'A', nom: 'Colonne unique, fiches remplacées' },
		{ cle: 'B', nom: 'Carte pleine, fiches empilées' },
		{ cle: 'C', nom: 'Rail des couches, dossier dans l’onglet' }
	];
	const variant = $derived(page.url.searchParams.get('variant') ?? 'A');
</script>

<svelte:head><title>Prototype carte J0 ({variant}) – Vigie Vaud</title></svelte:head>

{#key variant}
	{#if variant === 'B'}<VariantB {p} />
	{:else if variant === 'C'}<VariantC {p} />
	{:else}<VariantA {p} />{/if}
{/key}

<PrototypeSwitcher {variantes}>
	<code title="URL qu'aurait la page">{p.url}</code>
	<label><input type="checkbox" bind:checked={p.futures} /> onglets futurs</label>
</PrototypeSwitcher>

<style>
	code {
		color: #9fe0a8;
		font-size: 12px;
	}
	label {
		display: flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
	}
</style>
