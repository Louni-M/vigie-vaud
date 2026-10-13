<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import Map from '#lib/components/Map.svelte';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import { getCommuneDossiers } from '#lib/data.js';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import { dateLongue } from '#lib/dates.js';
	import { lienCarteCommune } from '#lib/etat.js';
	import type { Dossier } from '#lib/types.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const c = $derived(data.commune);
	const enquetes = $derived(data.actifs.filter((d) => d.statut === 'enquete'));
	const attente = $derived(data.actifs.filter((d) => d.statut === 'procedure'));

	let tout: Dossier[] | null = $state(null);
	let chargement = $state(false);
	let echec = $state(false);
	async function chargerTout() {
		chargement = true;
		echec = false;
		try {
			// Les dossiers en cours sont déjà listés plus haut.
			const enCours = new Set(data.actifs.map((d) => d.id));
			tout = (await getCommuneDossiers(fetch, c.slug)).filter((d) => !enCours.has(d.id));
		} catch {
			echec = true;
		} finally {
			chargement = false;
		}
	}

	const annees = $derived(Object.entries(data.parAnnee).sort().slice(-12));
	const maxAnnee = $derived(Math.max(1, ...annees.map(([, n]) => n)));
	const lienDossier = (d: Dossier) => resolve('/dossier/[id]', { id: String(d.id) });
	const resumeAnnees = $derived(annees.map(([a, n]) => `${a} : ${n}`).join(', '));
</script>

<svelte:head>
	<title>Mises à l’enquête à {c.nom} – Chantiers Vaud</title>
	<meta
		name="description"
		content="{c.statuts.enquete} demande{c.statuts.enquete > 1 ? 's' : ''} de permis de construire à l’enquête publique à {c.nom} (VD), et {c.total} dossiers depuis 1999."
	/>
</svelte:head>

<main class="page">
	<p class="fil"><a href={resolve('/commune')}>Communes</a> › {c.nom}</p>
	<h1>Mises à l’enquête à {c.nom}</h1>
	<p class="vers-carte"><a href={lienCarteCommune(c.slug)}>Voir {c.nom} sur la grande carte</a></p>

	<div class="mini-carte">
		<Map
			dossiers={data.actifs}
			bounds={c.bbox}
			statuts={['enquete', 'procedure']}
			onselect={(id) => goto(resolve('/dossier/[id]', { id: String(id) }))}
		/>
	</div>

	<div class="chiffres">
		{#each STATUTS_ORDRE as s (s)}
			<div style:--c={STATUTS[s].couleur}>
				<strong>{s === 'procedure' ? attente.length : (c.statuts[s] ?? 0)}</strong>
				<span>{STATUTS[s].court}</span>
			</div>
		{/each}
	</div>

	<h2>À l’enquête en ce moment ({enquetes.length})</h2>
	{#if enquetes.length}
		<ul class="grille">
			{#each enquetes as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
	{:else}
		<p class="muted">Aucune demande de permis à l’enquête publique actuellement.</p>
	{/if}

	{#if attente.length}
		<h2>Enquête terminée, décision attendue ({attente.length})</h2>
		<ul class="grille">
			{#each attente as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
	{/if}

	<h2>Demandes par année</h2>
	<div class="barres" role="img" aria-label="Demandes de permis par année – {resumeAnnees}">
		{#each annees as [annee, n] (annee)}
			<div class="barre" title="{n} demandes en {annee}">
				<span style:height="{(n / maxAnnee) * 100}%"></span>
				<small>{annee.slice(2)}</small>
			</div>
		{/each}
	</div>

	<h2>Historique</h2>
	{#if tout}
		<p class="muted">{tout.length} dossier{tout.length > 1 ? 's' : ''} depuis 1999, hors dossiers en cours listés plus haut.</p>
		<ul class="grille">
			{#each tout as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
	{:else}
		<ul class="grille">
			{#each data.recents as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
		{#if c.total > data.actifs.length + data.recents.length}
			<p>
				<button class="bouton secondaire" type="button" onclick={chargerTout} disabled={chargement}>
					{chargement ? 'Chargement…' : `Afficher tout l’historique (${c.total - data.actifs.length} dossiers depuis 1999)`}
				</button>
			</p>
			{#if echec}
				<p class="erreur" role="alert">L’historique n’a pas pu être chargé. Réessayez dans un instant.</p>
			{/if}
		{/if}
	{/if}

	<p class="source">
		{data.meta.source}. Mis à jour le {dateLongue(data.meta.mise_a_jour)}. Sans foi publique : seule la FAO fait foi.
		Rattachement aux communes actuelles (limites swisstopo).
		<a href={resolve('/infos-legales')}>Informations légales</a>
	</p>
</main>

<style>
	.fil {
		font-size: 14px;
		color: var(--muted);
		margin: 0;
	}
	h1 {
		margin: 6px 0 6px;
	}
	.vers-carte {
		margin: 0 0 12px;
		font-size: 14px;
	}
	h2 {
		font-size: 18px;
		margin: 28px 0 10px;
	}
	.mini-carte {
		position: relative;
		height: 300px;
		border-radius: 12px;
		overflow: hidden;
		border: 1px solid var(--line);
	}
	.chiffres {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 8px;
		margin-top: 12px;
	}
	.chiffres div {
		background: var(--surface);
		border: 1px solid var(--line);
		border-top: 3px solid var(--c);
		border-radius: 8px;
		padding: 8px 10px;
		display: grid;
	}
	.chiffres strong {
		font-size: 20px;
	}
	.chiffres span {
		font-size: 12.5px;
		color: var(--muted);
	}
	.grille {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 8px;
	}
	.barres {
		display: flex;
		align-items: flex-end;
		gap: 6px;
		height: 120px;
	}
	.barre {
		flex: 1;
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
		gap: 4px;
	}
	.barre span {
		width: 100%;
		background: var(--accent);
		border-radius: 3px 3px 0 0;
		min-height: 2px;
	}
	.barre small {
		font-size: 11px;
		color: var(--muted);
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin-top: 32px;
	}
</style>
