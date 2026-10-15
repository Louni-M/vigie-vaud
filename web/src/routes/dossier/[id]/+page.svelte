<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Map from '#lib/components/Map.svelte';
	import DossierFiche from '#lib/components/DossierFiche.svelte';
	import { ErreurApi } from '#lib/api.js';
	import { SOURCE } from '#lib/couches/permis/donnees.svelte.js';
	import { STATUTS, natureLabel } from '#lib/labels.js';
	import { dateLongue } from '#lib/dates.js';
	import type { Dossier } from '#lib/types.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let d: Dossier | undefined = $state();
	let etat: 'chargement' | 'trouve' | 'absent' | 'erreur' = $state('chargement');
	let message = $state('');

	$effect(() => {
		const p = data.dossier;
		etat = 'chargement';
		p.then(
			(r) => {
				if (p !== data.dossier) return;
				d = r;
				etat = r ? 'trouve' : 'absent';
			},
			(e) => {
				if (p !== data.dossier) return;
				etat = 'erreur';
				message = e instanceof ErreurApi ? e.message : 'Le dossier n’a pas pu être chargé.';
			}
		);
	});

	function reessayer() {
		// Le cache mémoire a oublié l'échec : recharger la page relance la requête.
		location.reload();
	}

	const titre = $derived(d ? `${natureLabel(d.nature)} à ${d.commune} – ${STATUTS[d.statut].court}` : `Dossier ${data.id}`);
	const resume = $derived(
		d ? `${d.description ?? ''} Enquête publique du ${dateLongue(d.debut)} au ${dateLongue(d.fin)}.`.trim() : ''
	);
	const delta = 0.004;
</script>

<svelte:head>
	<title>{titre} – Vigie Vaud</title>
	{#if resume}<meta name="description" content={resume} />{/if}
	<meta property="og:type" content="article" />
	<meta property="og:title" content={titre} />
	<meta property="og:url" content={page.url.href} />
</svelte:head>

<main class="page">
	<p class="fil">
		<a href={resolve('/commune')}>Communes</a> ›
		{#if d}<a href={resolve('/commune/[slug]', { slug: d.slug })}>{d.commune}</a> ›{/if}
		Dossier {data.id}
	</p>

	{#if etat === 'trouve' && d}
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
	{:else if etat === 'chargement'}
		<div class="grille" aria-busy="true">
			<div class="squelette">
				<p class="muted">Chargement du dossier n° {data.id} auprès du service du canton…</p>
				<span style:width="35%"></span>
				<span style:width="70%" class="grand"></span>
				<span style:width="95%"></span>
				<span style:width="90%"></span>
				<span style:width="60%"></span>
			</div>
			<div class="mini-carte vide"></div>
		</div>
	{:else if etat === 'absent'}
		<h1>Dossier introuvable</h1>
		<p>Aucun dossier n° {data.id} dans la couche du canton (les n° CAMAC ont 5 ou 6 chiffres).</p>
	{:else}
		<h1>Dossier indisponible</h1>
		<p class="erreur" role="alert">
			{message} Les dossiers sont lus en direct sur le service du canton (ogc.vd.ch).
		</p>
		<p><button class="bouton secondaire" type="button" onclick={reessayer}>Réessayer</button></p>
	{/if}

	<p class="source">
		{SOURCE} depuis votre navigateur ; ce site ne les stocke pas. Ces données n’ont pas de foi
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
	.squelette {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.squelette span {
		display: block;
		height: 14px;
		border-radius: 7px;
		background: var(--line);
	}
	.squelette .grand {
		height: 24px;
	}
	.mini-carte.vide {
		background: var(--surface-2);
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
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
