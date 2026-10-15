<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import { ErreurApi } from '#lib/api.js';
	import { permis, SOURCE, type ChiffresCommune } from '#lib/couches/permis/donnees.svelte.js';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import { lienVue } from '#lib/registre/liens.js';
	import type { Dossier } from '#lib/types.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const RECENTS = 60;
	const c = $derived(data.commune);

	// Tout est lu en direct sur le service du canton, dans le navigateur.
	let actifs = $state<Dossier[] | null>(null);
	let chiffres = $state<ChiffresCommune | null>(null);
	let recents = $state<Dossier[] | null>(null);
	let echec = $state('');

	const enquetes = $derived(actifs?.filter((d) => d.statut === 'enquete') ?? []);
	const attente = $derived(actifs?.filter((d) => d.statut === 'procedure') ?? []);

	const message = (e: unknown) =>
		`${e instanceof ErreurApi ? e.message : 'Les données n’ont pas pu être chargées.'} Les dossiers sont lus en direct sur ogc.vd.ch : réessayez dans un instant.`;

	function charger() {
		echec = '';
		const commune = c;
		permis.chargerActifs().then(
			(ds) => (actifs = ds.filter((d) => d.slug === commune.slug)),
			(e) => (echec = message(e))
		);
		permis
			.chiffres(commune)
			.then((r) => {
				chiffres = r;
				return permis.fiches(r.historique.slice(0, RECENTS).map((d) => d.id));
			})
			.then(
				(r) => (recents = r),
				(e) => (echec = message(e))
			);
	}
	onMount(charger);

	let tout = $state<Dossier[] | null>(null);
	let chargement = $state(false);
	let echecTout = $state(false);

	async function chargerTout() {
		chargement = true;
		echecTout = false;
		try {
			tout = await permis.fiches(chiffres?.historique.map((d) => d.id) ?? []);
		} catch {
			echecTout = true;
		} finally {
			chargement = false;
		}
	}

	const annees = $derived(Object.entries(chiffres?.parAnnee ?? {}).sort().slice(-12));
	const maxAnnee = $derived(Math.max(1, ...annees.map(([, n]) => n)));
	const lienDossier = (d: Dossier) => resolve('/dossier/[id]', { id: String(d.id) });
	const resumeAnnees = $derived(annees.map(([a, n]) => `${a} : ${n}`).join(', '));
	const totalHisto = $derived(chiffres?.historique.length ?? 0);

	/** Vue de la grande carte sur la commune : son centre, à un zoom qui la contient à peu près. */
	const vueCommune = $derived.by(() => {
		const [w, s, e, n] = c.bbox;
		const etendue = Math.max(e - w, (n - s) * 1.45);
		return { lon: (w + e) / 2, lat: (s + n) / 2, zoom: Math.min(15, Math.max(9, 9.6 + Math.log2(0.4 / etendue))) };
	});
</script>

<svelte:head>
	<title>Mises à l’enquête à {c.nom} – Vigie Vaud</title>
	<meta
		name="description"
		content="Demandes de permis de construire à l’enquête publique à {c.nom} (VD) : dossiers en cours, chiffres et historique depuis 1999."
	/>
</svelte:head>

<main class="page">
	<p class="fil"><a href={resolve('/commune')}>Communes</a> › {c.nom}</p>
	<h1>Mises à l’enquête à {c.nom}</h1>
	<p class="vers-carte"><a href={lienVue(vueCommune)}>Voir {c.nom} sur la grande carte</a></p>

	{#if echec}
		<p class="erreur" role="alert">
			{echec}
			<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
		</p>
	{/if}

	<div class="chiffres" aria-busy={!chiffres || !actifs}>
		{#each STATUTS_ORDRE as s (s)}
			<div style:--c={STATUTS[s].couleur}>
				<strong>
					<!-- En cours : comptés sur les listes ci-dessous (dossiers rattachés à la commune, procédures récentes). -->
					{#if s === 'enquete'}{actifs ? enquetes.length : '…'}
					{:else if s === 'procedure'}{actifs ? attente.length : '…'}
					{:else}{chiffres ? chiffres.statuts[s] : '…'}{/if}
				</strong>
				<span>{STATUTS[s].court}</span>
			</div>
		{/each}
	</div>

	<h2>À l’enquête en ce moment{actifs ? ` (${enquetes.length})` : ''}</h2>
	{#if !actifs}
		<ul class="grille" aria-busy="true"><li class="attente"></li><li class="attente"></li></ul>
	{:else if enquetes.length}
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
	{#if chiffres}
		<div class="barres" role="img" aria-label="Demandes de permis par année – {resumeAnnees}">
			{#each annees as [annee, n] (annee)}
				<div class="barre" title="{n} demandes en {annee}">
					<span style:height="{(n / maxAnnee) * 100}%"></span>
					<small>{annee.slice(2)}</small>
				</div>
			{/each}
		</div>
	{:else}
		<div class="barres attente" aria-busy="true"></div>
	{/if}

	<h2>Historique</h2>
	{#if tout}
		<p class="muted">{tout.length} dossier{tout.length > 1 ? 's' : ''} depuis 1999, hors dossiers en cours listés plus haut.</p>
		<ul class="grille">
			{#each tout as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
	{:else if !recents || !actifs}
		<ul class="grille" aria-busy="true"><li class="attente"></li><li class="attente"></li><li class="attente"></li></ul>
	{:else}
		<ul class="grille">
			{#each recents as d (d.id)}<li><DossierCarte {d} href={lienDossier(d)} /></li>{/each}
		</ul>
		{#if totalHisto > recents.length}
			<p>
				<button class="bouton secondaire" type="button" onclick={chargerTout} disabled={chargement}>
					{chargement
						? 'Chargement…'
						: `Afficher tout l’historique (${totalHisto} dossiers depuis 1999)`}
				</button>
			</p>
			{#if echecTout}
				<p class="erreur" role="alert">L’historique n’a pas pu être chargé. Réessayez dans un instant.</p>
			{/if}
		{/if}
	{/if}

	<p class="source">
		{SOURCE} depuis votre navigateur ; ce site ne les stocke pas. Sans foi publique : seule la FAO fait foi.
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
	.attente {
		min-height: 92px;
		border-radius: 10px;
		background: var(--line);
		opacity: 0.6;
	}
	.barres.attente {
		min-height: 0;
	}
</style>
