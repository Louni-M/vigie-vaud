<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { getActive, SOURCE } from '#lib/data.js';
	import { normaliser } from '#lib/labels.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	/** Enquêtes en cours par commune, lues en direct sur le service du canton. */
	let enquetes: Record<string, number> = $state({});
	onMount(() => {
		getActive(fetch).then(
			(ds) => {
				const n: Record<string, number> = {};
				for (const d of ds) if (d.statut === 'enquete') n[d.slug] = (n[d.slug] ?? 0) + 1;
				enquetes = n;
			},
			() => {}
		);
	});
	let filtre = $state('');

	const liste = $derived(data.communes.filter((c) => normaliser(c.nom).includes(normaliser(filtre))));
</script>

<svelte:head>
	<title>Mises à l’enquête par commune – Vigie Vaud</title>
	<meta name="description" content="Les demandes de permis de construire des 300 communes vaudoises : enquêtes en cours et historique." />
</svelte:head>

<main class="page">
	<h1>Les {data.communes.length} communes vaudoises</h1>
	<input type="search" placeholder="Filtrer les communes" bind:value={filtre} aria-label="Filtrer les communes" />
	<p class="resultat" role="status">
		{#if filtre.trim() && !liste.length}
			Aucune commune ne correspond à « {filtre.trim()} ».
		{:else if filtre.trim()}
			{liste.length} commune{liste.length > 1 ? 's' : ''}
		{/if}
	</p>
	<ul>
		{#each liste as c (c.slug)}
			<li>
				<a href={resolve('/commune/[slug]', { slug: c.slug })}>{c.nom}</a>
				{#if enquetes[c.slug]}
					<span class="enq">{enquetes[c.slug]} à l’enquête</span>
				{/if}
			</li>
		{/each}
	</ul>
	<p class="source">
		{SOURCE} depuis votre navigateur. Sans foi publique : seule la FAO fait foi.
		<a href={resolve('/infos-legales')}>Informations légales</a>
	</p>
</main>

<style>
	input {
		width: 100%;
		max-width: 360px;
		min-height: 44px;
		padding: 10px 12px;
		font-size: 16px;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: var(--surface);
		color: inherit;
	}
	.resultat {
		min-height: 1.2em;
		margin: 8px 0 0;
		font-size: 14px;
		color: var(--muted);
	}
	ul {
		list-style: none;
		padding: 0;
		columns: 3 220px;
		gap: 24px;
	}
	li {
		padding: 3px 0;
		break-inside: avoid;
	}
	.enq {
		font-size: 12px;
		color: var(--enquete-texte);
		margin-left: 4px;
	}
	/* Lignes plus hautes au doigt (zones tactiles d'environ 44 px). */
	@media (pointer: coarse), (max-width: 760px) {
		li {
			padding: 0;
		}
		li a {
			display: inline-block;
			padding: 12px 0;
		}
	}
</style>
