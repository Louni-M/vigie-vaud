<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Map from '#lib/components/Map.svelte';
	import DossierFiche from '#lib/components/DossierFiche.svelte';
	import { STATUTS, natureLabel } from '#lib/labels.js';
	import { dateLongue } from '#lib/dates.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const d = $derived(data.dossier);
	const titre = $derived(`${natureLabel(d.nature)} à ${d.commune} – ${STATUTS[d.statut].court}`);
	const resume = $derived(
		`${d.description ?? ''} Enquête publique du ${dateLongue(d.debut)} au ${dateLongue(d.fin)}.`.trim()
	);
	const delta = 0.004;
</script>

<svelte:head>
	<title>{titre} – Chantiers Vaud</title>
	<meta name="description" content={resume} />
	<meta property="og:type" content="article" />
	<meta property="og:title" content={titre} />
	<meta property="og:description" content={resume} />
	<meta property="og:url" content={page.url.href} />
	<meta name="twitter:card" content="summary" />
</svelte:head>

<main class="page">
	<p class="fil">
		<a href={resolve('/commune')}>Communes</a> ›
		<a href={resolve('/commune/[slug]', { slug: d.slug })}>{d.commune}</a> › Dossier {d.id}
	</p>
	<div class="grille">
		<DossierFiche {d} lienCarte />
		<div class="mini-carte">
			{#key d.id}
				<Map
					dossiers={[d]}
					statuts={[d.statut]}
					selection={d.id}
					bounds={[d.lon - delta, d.lat - delta * 0.7, d.lon + delta, d.lat + delta * 0.7]}
				/>
			{/key}
		</div>
	</div>
	<p class="source">
		{data.meta.source}. Mis à jour le {dateLongue(data.meta.mise_a_jour)}. Ces données n’ont pas de foi
		publique : seule la publication dans la Feuille des avis officiels (FAO) fait foi. L’emplacement est
		indicatif. <a href={resolve('/infos-legales')}>Informations légales</a>
	</p>
</main>

<style>
	.fil {
		font-size: 14px;
		color: var(--muted);
		margin: 0 0 14px;
	}
	.grille {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 20px;
		align-items: start;
	}
	.mini-carte {
		position: relative;
		height: 360px;
		border-radius: 12px;
		overflow: hidden;
		border: 1px solid var(--line);
		position: sticky;
		top: calc(var(--header-h) + 16px);
	}
	.source {
		margin-top: 28px;
	}
	@media (max-width: 760px) {
		.grille {
			grid-template-columns: 1fr;
		}
		.mini-carte {
			position: relative;
			top: 0;
			height: 260px;
			order: -1;
		}
	}
</style>
