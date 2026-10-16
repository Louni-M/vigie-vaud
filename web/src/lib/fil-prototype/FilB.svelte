<script lang="ts">
	/*
	 * PROTOTYPE (ticket #45), variante B « Colonne Fil | Fiche » : sur bureau, la colonne de droite est toujours là ;
	 * elle montre le fil cantonal tant qu'aucune fiche n'est ouverte, puis deux onglets « Fil cantonal » et la fiche
	 * de la commune. Entrées en cartes détaillées ; filtre par type à choix unique ; « Limiter à la zone visible »
	 * en case à cocher. Les éléments sans commune sont mêlés au fil avec l'étiquette « Tout le canton ». Un objet du
	 * Grand Conseil propose chaque commune citée. Sur téléphone, le fil est un tiroir à trois hauteurs sur la carte.
	 */
	import { onMount, untrack } from 'svelte';
	import { permis } from '#lib/couches/permis/donnees.svelte.js';
	import FicheCommune from '#lib/registre/FicheCommune.svelte';
	import type { Registre } from '#lib/registre/registre.svelte.js';
	import type { Commune } from '#lib/types.js';
	import { Filtre, TYPES, dansZone, jour, sansRattachement, surligner, toutes, typeDe, type Entree, type TypeEntree } from './entrees.svelte.js';
	import Deplie from './Deplie.svelte';

	let {
		registre,
		communes,
		tiroir = false,
		onouvert
	}: { registre: Registre; communes: readonly Commune[]; tiroir?: boolean; onouvert?: () => void } = $props();

	onMount(() => {
		permis.chargerActifs().catch(() => {});
		return () => surligner(registre.map, null);
	});

	const filtre = new Filtre();
	let type = $state<TypeEntree | 'tout'>('tout');
	$effect(() => {
		filtre.types = type === 'tout' ? TYPES.map((t) => t.id) : [type];
	});
	/** Zone figée par un clic dans le fil : la carte vole vers l'élément sans vider la liste qu'on parcourait. */
	let figee = $state.raw<typeof registre.zone>(null);
	const zone = $derived(figee ?? registre.zone);
	const visibles = $derived(
		toutes(communes).filter(
			(e) => filtre.types.includes(e.type) && (sansRattachement(e) || !filtre.zone || dansZone(e, zone))
		)
	);

	/* Onglets de la colonne : une fiche qui s'ouvre prend la main ; « Fil cantonal » la garde ouverte derrière. */
	let vue = $state<'fil' | 'fiche'>('fil');
	let communeAvant: string | null = null;
	$effect(() => {
		const s = registre.commune?.slug ?? null;
		const o = registre.ouvert ? `${registre.ouvert.couche}:${registre.ouvert.element}` : null;
		untrack(() => {
			if (s && (s !== communeAvant || o)) vue = 'fiche';
			if (!s) vue = 'fil';
			communeAvant = s;
		});
	});

	let detail = $state<Entree | null>(null);
	/** Tiroir sur téléphone : replié (une ligne), à mi-hauteur, ou plein. */
	let hauteur = $state<'replie' | 'moitie' | 'plein'>('replie');

	function clic(e: Entree) {
		if (e.cible) {
			figee ??= registre.zone;
			registre.ouvrir(e.cible);
			if (tiroir) hauteur = 'replie';
			onouvert?.();
		} else detail = e;
	}
</script>

{#snippet carte(e: Entree)}
	{@const t = typeDe(e.type)}
	<li>
		<article
			class="carte"
			style:--c={t.couleur}
			onmouseenter={() => surligner(registre.map, e)}
			onmouseleave={() => surligner(registre.map, null)}
		>
			<p class="haut">
				<span class="type">{e.sorte}</span>
				{#if !e.cible}<span class="canton">Tout le canton</span>{/if}
				<span class="date">{e.avenir ? 'à venir · ' : ''}{jour(e.date)}</span>
			</p>
			<button type="button" class="titre" onclick={() => clic(e)}>{e.titre}</button>
			<p class="qui">
				{e.qui}{#if e.conseil?.auteurs.length} · {e.conseil.auteurs[0].nom}{/if}{#if e.conseil?.statut} · {e.conseil.statut}{/if}
			</p>
			{#if e.conseil?.conseil === null && e.communes.length}
				<p class="cites">
					Cité :
					{#each e.communes as c (c.slug)}
						<button type="button" onclick={() => { figee ??= registre.zone; registre.ouvrir({ couche: 'conseils', element: e.conseil!.id, position: c.hotel }); onouvert?.(); }}>{c.nom}</button>
					{/each}
				</p>
			{/if}
		</article>
	</li>
{/snippet}

{#snippet fil()}
	{#if detail}
		<button type="button" class="retour" onclick={() => (detail = null)}>← Fil cantonal</button>
		<p class="type-detail">{detail.sorte} · {detail.qui} · <span class="canton">Tout le canton</span></p>
		<h3>{detail.titre}</h3>
		<Deplie e={detail} />
	{:else}
		<div class="filtres">
			<select bind:value={type} aria-label="Type">
				<option value="tout">Tout</option>
				{#each TYPES as t (t.id)}<option value={t.id}>{t.nom}</option>{/each}
			</select>
			<label><input type="checkbox" bind:checked={filtre.zone} /> Limiter à la zone visible</label>
		</div>
		<p class="compte">{visibles.length} nouveautés{filtre.zone ? ' dans la zone, et celles de tout le canton' : ''}</p>
		{#if figee && filtre.zone}
			<p class="figee">Liste de la zone où vous étiez. <button type="button" onclick={() => (figee = null)}>↻ Suivre la carte</button></p>
		{/if}
		<ul>{#each visibles as e (e.cle)}{@render carte(e)}{/each}</ul>
		<p class="note">Dossiers mis à l’enquête ces 14 derniers jours (réels). Objets et séances fictifs.</p>
	{/if}
{/snippet}

{#if tiroir}
	<section class="tiroir {hauteur}" aria-label="Fil cantonal">
		<button
			type="button"
			class="poignee"
			onclick={() => (hauteur = hauteur === 'replie' ? 'moitie' : hauteur === 'moitie' ? 'plein' : 'replie')}
		>
			<span class="barre" aria-hidden="true"></span>
			Fil cantonal · {visibles.length} nouveautés {hauteur === 'plein' ? '▼' : '▲'}
		</button>
		{#if hauteur !== 'replie'}<div class="defile">{@render fil()}</div>{/if}
	</section>
{:else}
	<section class="colonne-b">
		<div class="onglets-b" role="tablist">
			<button type="button" role="tab" aria-selected={vue === 'fil'} onclick={() => (vue = 'fil')}>Fil cantonal</button>
			<button type="button" role="tab" aria-selected={vue === 'fiche'} disabled={!registre.commune} onclick={() => (vue = 'fiche')}>
				{registre.commune ? registre.commune.nom : 'Fiche commune'}
			</button>
		</div>
		<div class="corps-b">
			{#if vue === 'fiche' && registre.commune}
				<FicheCommune {registre} commune={registre.commune} />
			{:else}
				<div class="fil-b">{@render fil()}</div>
			{/if}
		</div>
	</section>
{/if}

<style>
	.colonne-b { display: grid; grid-template-rows: auto minmax(0, 1fr); height: 100%; border-left: 1px solid var(--line); background: var(--surface); }
	.onglets-b { display: flex; border-bottom: 1px solid var(--line); }
	.onglets-b button { flex: 1; padding: 10px; border: 0; border-bottom: 3px solid transparent; background: none; font: inherit; font-weight: 600; cursor: pointer; }
	.onglets-b button[aria-selected='true'] { border-bottom-color: var(--accent); color: var(--accent); }
	.onglets-b button:disabled { opacity: 0.4; cursor: default; }
	.corps-b { min-height: 0; overflow: hidden; }
	.corps-b :global(.fiche) { border-left: 0; height: 100%; }
	.fil-b { height: 100%; overflow-y: auto; padding: 10px 14px 20px; }
	.filtres { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; font-size: 13px; }
	select { font: inherit; padding: 4px 6px; }
	.compte { font-size: 12px; color: var(--muted); margin: 8px 0; }
	ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
	.carte { border: 1px solid var(--line); border-left: 4px solid var(--c); border-radius: 8px; padding: 8px 10px; background: var(--surface); }
	.carte:hover { box-shadow: 0 1px 6px rgb(0 0 0 / 0.12); }
	.haut { display: flex; gap: 6px; align-items: center; margin: 0; font-size: 12px; }
	.type { color: var(--c); font-weight: 700; }
	.date { margin-left: auto; color: var(--muted); }
	.canton { font-size: 11px; padding: 1px 6px; border-radius: 999px; background: #eee; color: #444; }
	.titre { display: block; text-align: left; border: 0; background: none; padding: 3px 0; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
	.titre:hover { text-decoration: underline; }
	.qui { margin: 0; font-size: 12px; color: var(--muted); }
	.cites { margin: 4px 0 0; font-size: 12px; display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
	.cites button { border: 1px solid var(--line); border-radius: 999px; background: var(--bg); font: inherit; font-size: 12px; padding: 1px 8px; cursor: pointer; }
	.retour { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; padding: 4px 0; }
	.type-detail { font-size: 13px; color: var(--muted); }
	.figee { font-size: 12px; background: #fff6d6; border-radius: 6px; padding: 4px 8px; margin: 0 0 8px; }
	.figee button { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; cursor: pointer; }
	.note { font-size: 11px; color: var(--muted); margin-top: 14px; }
	.tiroir { position: absolute; z-index: 5; left: 0; right: 0; bottom: 0; background: var(--surface); border-radius: 14px 14px 0 0; box-shadow: 0 -2px 12px rgb(0 0 0 / 0.2); display: flex; flex-direction: column; transition: height 0.2s; }
	.tiroir.replie { height: 52px; }
	.tiroir.moitie { height: 50%; }
	.tiroir.plein { height: calc(100% - 60px); }
	.poignee { border: 0; background: none; font: inherit; font-weight: 600; padding: 6px 12px 10px; cursor: pointer; display: grid; justify-items: center; gap: 6px; }
	.barre { width: 40px; height: 4px; border-radius: 2px; background: var(--line); }
	.defile { overflow-y: auto; padding: 0 12px 16px; min-height: 0; }
</style>
