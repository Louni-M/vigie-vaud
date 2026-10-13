<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : onglet Permis de la fiche commune (contenu de l'ancienne page commune, allégé).
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import { getChiffresCommune, type ChiffresCommune } from '#lib/data.js';
	import { STATUTS } from '#lib/labels.js';
	import type { Commune, Dossier } from '#lib/types.js';
	import type { Proto } from '../proto.svelte.js';

	let { p, commune, onDossier = (d: Dossier) => p.ouvrirDossier(d) }: { p: Proto; commune: Commune; onDossier?: (d: Dossier) => void } = $props();

	const actifs = $derived(p.actifs.filter((d) => d.slug === commune.slug));
	const enquetes = $derived(actifs.filter((d) => d.statut === 'enquete'));
	const attente = $derived(actifs.filter((d) => d.statut === 'procedure'));

	let chiffres = $state<ChiffresCommune | null>(null);
	$effect(() => {
		const c = commune;
		chiffres = null;
		getChiffresCommune(fetch, c).then((r) => c === commune && (chiffres = r), () => {});
	});
	const annees = $derived(Object.entries(chiffres?.parAnnee ?? {}).sort().slice(-12));
	const max = $derived(Math.max(1, ...annees.map(([, n]) => n)));
</script>

<div class="onglet">
	<div class="chiffres">
		<div style:--c={STATUTS.enquete.couleur}><strong>{enquetes.length}</strong><span>À l’enquête</span></div>
		<div style:--c={STATUTS.procedure.couleur}><strong>{attente.length}</strong><span>Décision attendue</span></div>
		<div style:--c={STATUTS.delivre.couleur}><strong>{chiffres?.statuts.delivre ?? '…'}</strong><span>Délivrés</span></div>
	</div>

	<h3>À l’enquête en ce moment ({enquetes.length})</h3>
	{#if enquetes.length}
		<ul>
			{#each enquetes as d (d.id)}<li><DossierCarte {d} onclick={() => onDossier(d)} /></li>{/each}
		</ul>
	{:else}
		<p class="muted">Aucune demande à l’enquête actuellement.</p>
	{/if}

	{#if attente.length}
		<h3>Décision attendue ({attente.length})</h3>
		<ul>
			{#each attente.slice(0, 6) as d (d.id)}<li><DossierCarte {d} onclick={() => onDossier(d)} /></li>{/each}
		</ul>
		{#if attente.length > 6}<p class="muted">… et {attente.length - 6} autres</p>{/if}
	{/if}

	<h3>Demandes par année</h3>
	<div class="barres" aria-busy={!chiffres}>
		{#each annees as [a, n] (a)}
			<div class="barre" title="{n} en {a}"><span style:height="{(n / max) * 100}%"></span><small>{a.slice(2)}</small></div>
		{/each}
	</div>
	<button class="bouton secondaire" type="button" disabled>Historique complet (non branché)</button>
</div>

<style>
	.onglet {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	h3 {
		font-size: 15px;
		margin: 12px 0 2px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.chiffres {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
	}
	.chiffres div {
		background: var(--surface);
		border: 1px solid var(--line);
		border-top: 3px solid var(--c);
		border-radius: 8px;
		padding: 6px 8px;
		display: grid;
	}
	.chiffres strong {
		font-size: 18px;
	}
	.chiffres span {
		font-size: 12px;
		color: var(--muted);
	}
	.barres {
		display: flex;
		align-items: flex-end;
		gap: 4px;
		height: 80px;
	}
	.barre {
		flex: 1;
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
		gap: 2px;
	}
	.barre span {
		width: 100%;
		background: var(--accent);
		border-radius: 2px 2px 0 0;
		min-height: 2px;
	}
	.barre small {
		font-size: 10px;
		color: var(--muted);
	}
	.muted {
		color: var(--muted);
		font-size: 14px;
		margin: 0;
	}
</style>
