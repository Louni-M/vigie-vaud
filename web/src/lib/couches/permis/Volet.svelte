<script lang="ts">
	/*
	 * Volet de la couche Permis : puces de statut (qui servent de légende), nature, tri, historique et curseur
	 * d'années, puis le compteur et la liste des dossiers de la zone visible, masqués quand la couche est
	 * désactivée. Le registre a déjà rendu l'interrupteur et l'attribution au-dessus.
	 */
	import { resolve } from '$app/paths';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import { ErreurApi } from '#lib/api.js';
	import { NATURES, STATUTS } from '#lib/labels.js';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Dossier, PointHisto, Statut } from '#lib/types.js';
	import { permis, visibles as dossiersVisibles, type Parametres } from './donnees.svelte.js';
	import { ANNEE_MIN, statutsProposes } from './index.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	const ANNEE_COURANTE = new Date().getFullYear();
	/** Dossiers listés au plus : au-delà, on invite à zoomer. */
	const LISTE_MAX = 150;

	const p = $derived(ctx.parametres);
	const proposes = $derived(statutsProposes(p.historique));
	const actifs = $derived(permis.actifs);
	const visibles = $derived(ctx.active ? dossiersVisibles(ctx.zone, p, permis) : []);

	/* ---- Chargement des dossiers en cours, et son échec ---- */

	let echec = $state('');
	const messageErreur = (e: unknown) =>
		e instanceof ErreurApi && e.hors_ligne
			? 'Vous semblez hors ligne : les dossiers sont lus en direct sur le service du canton.'
			: e instanceof ErreurApi
				? `${e.message} Les dossiers sont lus en direct sur ogc.vd.ch : réessayez dans un instant.`
				: 'Les données n’ont pas pu être chargées.';
	function charger() {
		echec = '';
		permis.chargerActifs().catch((e) => (echec = messageErreur(e)));
	}
	$effect(() => {
		if (ctx.active) charger();
	});

	/* ---- Fiches complètes des dossiers d'historique en tête de liste, chargées quand la carte s'arrête ---- */

	let fichesHisto: Record<number, Dossier> = $state.raw({});
	/** Fiche complète d'un élément de la liste, ou `undefined` tant qu'elle n'est pas chargée. */
	const fiche = (d: Dossier | PointHisto): Dossier | undefined => ('slug' in d ? d : fichesHisto[d.id]);

	$effect(() => {
		const manquants = visibles
			.slice(0, LISTE_MAX)
			.filter((d) => !fiche(d))
			.map((d) => d.id);
		if (!manquants.length) return;
		const ctrl = new AbortController();
		const t = setTimeout(
			() =>
				permis.fiches(manquants, ctrl.signal).then(
					(ds) => (fichesHisto = { ...fichesHisto, ...Object.fromEntries(ds.map((d) => [d.id, d])) }),
					() => {}
				),
			200
		);
		return () => {
			clearTimeout(t);
			ctrl.abort();
		};
	});

	/* ---- Réglages ---- */

	function basculerStatut(s: Statut) {
		ctx.regler({ statuts: p.statuts.includes(s) ? p.statuts.filter((x) => x !== s) : [...p.statuts, s] });
	}

	/** Les statuts proposés changent avec l'historique : on repart de ceux par défaut. */
	function basculerHistorique(historique: boolean) {
		ctx.regler({ historique, statuts: [...statutsProposes(historique)] });
	}

	/** Le curseur suit la main ; l'adresse et le chargement suivent la valeur (le chargement attend qu'il s'arrête). */
	function depuis(e: Event) {
		ctx.regler({ depuis: Number((e.currentTarget as HTMLInputElement).value) });
	}

	/** Un clic sur un dossier de la liste fait voler la carte vers lui ; l'ouvrir viendra avec l'onglet Permis. */
	function vers(d: Dossier) {
		ctx.map.flyTo({ center: [d.lon, d.lat], zoom: Math.max(ctx.map.getZoom(), 16), curve: 1.6, speed: 0.9 });
	}
</script>

<div class="reglages">
	<div class="puces" role="group" aria-label="Statuts affichés (légende de la carte)">
		{#each proposes as s (s)}
			<button
				type="button"
				class="puce"
				class:off={!p.statuts.includes(s)}
				aria-pressed={p.statuts.includes(s)}
				style:--c={STATUTS[s].couleur}
				onclick={() => basculerStatut(s)}
			>
				<span></span>{STATUTS[s].court}
			</button>
		{/each}
	</div>

	<div class="ligne">
		<select value={p.nature} onchange={(e) => ctx.regler({ nature: e.currentTarget.value })} aria-label="Nature des travaux">
			<option value="">Toutes natures</option>
			{#each Object.entries(NATURES) as [k, v] (k)}
				<option value={k}>{v}</option>
			{/each}
		</select>
		<select
			value={p.tri}
			onchange={(e) => ctx.regler({ tri: e.currentTarget.value === 'fin' ? 'fin' : 'recent' })}
			aria-label="Ordre de la liste"
		>
			<option value="recent">Publication récente d’abord</option>
			<option value="fin">Fin d’enquête la plus proche</option>
		</select>
	</div>

	<label class="bascule">
		<input type="checkbox" checked={p.historique} onchange={(e) => basculerHistorique(e.currentTarget.checked)} />
		Historique
	</label>
	{#if p.historique}
		<label class="annee">
			<span>Depuis <strong>{p.depuis}</strong></span>
			<input type="range" min={ANNEE_MIN} max={ANNEE_COURANTE} value={p.depuis} oninput={depuis} />
		</label>
	{/if}
</div>

{#if ctx.active}
	<div class="zone">
		<p class="compte" tabindex="-1">
			{#if echec}
				<span class="erreur">{echec}</span>
				<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
			{:else if !actifs.length}
				Chargement des dossiers en cours auprès du canton…
			{:else if p.historique}
				<strong>{visibles.length}</strong> dossier{visibles.length > 1 ? 's' : ''} dans la zone affichée,
				historique depuis {p.depuis} compris
				{#if permis.histoChargement}<span class="muted"> · chargement de l’historique…</span>{/if}
				{#if permis.histoEchec}
					<span class="erreur"> · historique partiel : une partie n’a pas pu être chargée</span>
					<button class="bouton secondaire petit" type="button" onclick={() => permis.chargerHisto(p.depuis)}>Réessayer</button>
				{/if}
			{:else}
				<strong>{visibles.length}</strong> dossier{visibles.length > 1 ? 's' : ''} en cours dans la zone affichée
			{/if}
		</p>
		{#if actifs.length && !visibles.length && !permis.histoChargement}
			<p class="muted vide">
				{#if !p.statuts.length}
					Aucun statut n’est sélectionné : activez-en au moins un pour afficher la liste.
				{:else}
					Aucun dossier ne correspond à ces filtres dans la zone affichée. Dézoomez la carte ou choisissez
					« Toutes natures ».
				{/if}
			</p>
		{/if}
		<ul class="liste">
			{#each visibles.slice(0, LISTE_MAX) as d (d.id)}
				{@const f = fiche(d)}
				<li data-id={d.id}>
					{#if f}
						<DossierCarte d={f} onclick={() => vers(f)} />
					{:else}
						<div class="carte-attente" aria-busy="true">
							<span class="barre-s" style:width="45%"></span>
							<span class="barre-s" style:width="90%"></span>
							<span class="barre-s" style:width="30%"></span>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
		{#if visibles.length > LISTE_MAX}
			<p class="muted">… et {visibles.length - LISTE_MAX} autres : zoomez pour affiner.</p>
		{/if}
	</div>
{/if}

<p class="source">
	Dossiers consultés en direct depuis votre navigateur ; ce site ne les stocke pas. Sans foi publique : seule la
	<a href="https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao" target="_blank" rel="noopener">FAO</a>
	fait foi. <a href={resolve('/infos-legales')}>L’enquête publique : ce que prévoit la loi</a>
</p>

<style>
	.reglages,
	.zone {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.puces,
	.ligne {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.puce {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: 999px;
		border: 1px solid var(--c);
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
		cursor: pointer;
	}
	.puce span {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--c);
	}
	.puce.off {
		border-color: var(--line);
		color: var(--muted);
	}
	.puce.off span {
		background: transparent;
		box-shadow: inset 0 0 0 1.5px var(--c);
	}
	select {
		padding: 7px 8px;
		border-radius: 8px;
		border: 1px solid var(--line);
		background: var(--surface);
		font: inherit;
		font-size: 13.5px;
		color: inherit;
		max-width: 100%;
	}
	.bascule {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13.5px;
		cursor: pointer;
	}
	.bascule input {
		width: 18px;
		height: 18px;
		margin: 0;
		accent-color: var(--accent);
	}
	.annee {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		min-width: 0;
	}
	.annee span {
		white-space: nowrap;
	}
	.annee input {
		flex: 1;
		min-width: 80px;
		accent-color: var(--accent);
	}
	.zone {
		margin-top: 4px;
		padding-top: 10px;
		border-top: 1px solid var(--line);
	}
	.compte {
		margin: 0;
		font-size: 14px;
	}
	.compte .bouton {
		margin-left: 6px;
	}
	.compte:focus {
		outline: none;
	}
	.petit {
		padding: 6px 10px;
		font-size: 13px;
	}
	.vide {
		margin: 0;
		font-size: 14px;
		line-height: 1.45;
	}
	.liste {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.carte-attente {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: var(--surface);
		min-height: 92px;
	}
	.barre-s {
		display: block;
		height: 12px;
		border-radius: 6px;
		background: linear-gradient(90deg, var(--line) 0%, var(--bg) 50%, var(--line) 100%);
		background-size: 200% 100%;
		animation: reflet 1.2s ease-in-out infinite;
	}
	@keyframes reflet {
		from {
			background-position: 100% 0;
		}
		to {
			background-position: -100% 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.barre-s {
			animation: none;
		}
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin: 4px 0 0;
	}
	@media (pointer: coarse) {
		.petit,
		.puce,
		.bascule,
		select {
			min-height: 44px;
		}
	}
</style>
