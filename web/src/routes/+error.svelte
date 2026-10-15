<script lang="ts">
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { COUCHES } from '#lib/registre/couches.js';
	import { lienCommune, lienElement, lienVue } from '#lib/registre/liens.js';
	import { resultatsCouches } from '#lib/registre/recherche.js';
	import { ancienneAdresse } from '#lib/socle/anciens.js';
	import { getCommunes } from '#lib/socle/communes.js';
	import Recherche from '#lib/socle/Recherche.svelte';
	import type { Commune, Resultat } from '#lib/types.js';

	const introuvable = $derived(page.status === 404);
	// Message de nos fonctions load (« Dossier introuvable »…) ; celui de SvelteKit est en anglais (« Not Found »).
	const titre = $derived(
		introuvable
			? page.error?.message && page.error.message !== 'Not Found'
				? page.error.message
				: 'Page introuvable'
			: 'Une erreur est survenue'
	);

	/*
	 * Chargées dans le navigateur : la 404 du site statique (404.html) est une page vide qui ne connaît pas
	 * l'adresse demandée. La recherche n'apparaît qu'une fois les communes là.
	 */
	let communes: Commune[] = $state([]);
	$effect(() => {
		getCommunes(fetch).then(
			(c) => (communes = c),
			() => {}
		);
	});

	// `/commune/cully` : pas de page d'alias, mais la 404 renvoie vers la commune actuelle.
	const racine = resolve('/(carte)');
	const ancienne = $derived.by(() => {
		const chemin = page.url.pathname;
		return introuvable ? ancienneAdresse(communes, chemin.startsWith(racine) ? chemin.slice(racine.length - 1) : chemin) : null;
	});

	// La 404 n'a pas de carte : choisir un résultat mène à la carte, qui l'ouvre ou s'y centre.
	function choix(r: Resultat) {
		if (r.type === 'commune') goto(lienCommune(r.commune.slug));
		else if (r.type === 'element') goto(lienElement(r.couche, r.element));
		else goto(lienVue({ lon: r.lon, lat: r.lat, zoom: r.genre === 'Position' ? 15 : 16 }));
	}
</script>

<svelte:head>
	<title>{titre} – Vigie Vaud</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="page">
	<h1>{titre}</h1>
	{#if ancienne}
		<p class="ancienne">
			{ancienne.phrase} : <a href={lienCommune(ancienne.commune.slug)}>voir la fiche de {ancienne.commune.nom}</a>.
		</p>
	{:else if introuvable}
		<p>Cette adresse ne correspond à aucune page du site.</p>
	{:else}
		<p>La page n’a pas pu être affichée ({page.status}). Réessayez dans un instant.</p>
	{/if}
	{#if communes.length}
		<div class="recherche">
			<Recherche {communes} chercherCouches={(texte) => resultatsCouches(COUCHES, texte)} onchoix={choix} />
		</div>
	{/if}
	<p class="actions">
		<a class="bouton" href={resolve('/(carte)')}>Retour à la carte</a>
	</p>
</main>

<style>
	.ancienne {
		font-size: 1.1em;
	}
	.recherche {
		max-width: 480px;
		margin: 16px 0;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
</style>
