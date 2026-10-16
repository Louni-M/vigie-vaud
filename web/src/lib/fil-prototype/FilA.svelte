<script lang="ts">
	/*
	 * PROTOTYPE (ticket #45), variante A « Fil au rail » : le fil est une entrée du rail, au-dessus des couches,
	 * et s'ouvre dans le même emplacement que leurs volets. Entrées compactes groupées par jour ; filtre par type
	 * en puces cumulables ; « Zone visible / Tout le canton ». Les éléments sans commune ont leur propre section,
	 * repliable, en tête : ils ne dépendent pas de la zone. Un clic ouvre l'élément dans la fiche de sa commune
	 * (le fil reste ouvert) ; un élément sans commune se déplie sur place.
	 */
	import { onMount } from 'svelte';
	import { permis } from '#lib/couches/permis/donnees.svelte.js';
	import type { Registre } from '#lib/registre/registre.svelte.js';
	import type { Commune } from '#lib/types.js';
	import { Filtre, TYPES, court, dansZone, parJour, sansRattachement, surligner, toutes, typeDe, type Entree } from './entrees.svelte.js';
	import Deplie from './Deplie.svelte';
	// PROTOTYPE (ticket #51)
	import { charger } from '#lib/couches/conseils-prototype/donnees.svelte.js';
	import { ouvrirGrandConseil, proto } from '#lib/couches/conseils-prototype/proto.svelte.js';

	let {
		registre,
		communes,
		onfermer,
		onouvert
	}: { registre: Registre; communes: readonly Commune[]; onfermer?: () => void; onouvert?: () => void } = $props();

	onMount(() => {
		permis.chargerActifs().catch(() => {});
		charger(communes);
		return () => surligner(registre.map, null);
	});

	const filtre = new Filtre();
	const tout = $derived(toutes(communes).filter((e) => filtre.types.includes(e.type) && (!proto.filQui || e.qui === proto.filQui)));
	const sans = $derived(tout.filter(sansRattachement));
	const avec = $derived(tout.filter((e) => !sansRattachement(e) && (!filtre.zone || dansZone(e, registre.zone))));
	let sansOuvert = $state(true);
	let deplie = $state<string | null>(null);

	const ouvertCle = $derived(registre.ouvert ? `${registre.ouvert.couche === 'permis' ? 'd' : 'o'}:${registre.ouvert.element}` : null);

	function clic(e: Entree) {
		if (e.cible) {
			registre.ouvrir(e.cible);
			onouvert?.();
		} else if (proto.variante === 'A' && e.conseil?.conseil === null) {
			// Variante A : un élément du Grand Conseil sans commune s'ouvre dans la fiche du Grand Conseil.
			ouvrirGrandConseil(e.conseil.id);
			onouvert?.();
		} else deplie = deplie === e.cle ? null : e.cle;
	}
</script>

{#snippet ligne(e: Entree)}
	{@const t = typeDe(e.type)}
	<li class:ouvert={ouvertCle === e.cle}>
		<button
			type="button"
			onclick={() => clic(e)}
			onmouseenter={() => surligner(registre.map, e)}
			onmouseleave={() => surligner(registre.map, null)}
			aria-expanded={e.cible ? undefined : deplie === e.cle}
		>
			<span class="signe" style:--c={t.couleur}>{t.signe}</span>
			<span class="texte">
				<span class="meta">{e.sorte} · {e.qui}{#if e.conseil?.conseil === null && e.communes.length} → {e.communes.map((c) => c.nom).join(', ')}{/if}</span>
				<span class="titre">{e.titre}</span>
			</span>
			{#if e.cible}<span class="fleche" aria-hidden="true">›</span>{:else}<span class="fleche" aria-hidden="true">{deplie === e.cle ? '▾' : '▸'}</span>{/if}
		</button>
		{#if deplie === e.cle}<Deplie {e} />{/if}
	</li>
{/snippet}

<section class="fil" aria-labelledby="fil-a-titre">
	<header>
		<h2 id="fil-a-titre">Fil cantonal</h2>
		{#if onfermer}<button class="fermer" type="button" aria-label="Fermer le fil" onclick={onfermer}>×</button>{/if}
	</header>

	<div class="puces" role="group" aria-label="Types">
		{#each TYPES as t (t.id)}
			<button type="button" aria-pressed={filtre.types.includes(t.id)} style:--c={t.couleur} onclick={() => filtre.basculer(t.id)}>
				{t.signe} {t.nom}
			</button>
		{/each}
	</div>
	{#if proto.filQui}
		<p class="qui">Seulement : <strong>{proto.filQui}</strong> <button type="button" aria-label="Retirer ce filtre" onclick={() => (proto.filQui = null)}>×</button></p>
	{/if}
	<div class="portee" role="radiogroup" aria-label="Portée">
		<label><input type="radio" name="portee-a" checked={filtre.zone} onchange={() => (filtre.zone = true)} /> Zone visible</label>
		<label><input type="radio" name="portee-a" checked={!filtre.zone} onchange={() => (filtre.zone = false)} /> Tout le canton</label>
	</div>

	{#if sans.length}
		<div class="sans">
			<button type="button" class="tete-sans" aria-expanded={sansOuvert} onclick={() => (sansOuvert = !sansOuvert)}>
				{sansOuvert ? '▾' : '▸'} Sans commune ({sans.length})
				<span class="aide">dans le fil seulement, quelle que soit la zone</span>
			</button>
			{#if sansOuvert}<ul>{#each sans as e (e.cle)}{@render ligne(e)}{/each}</ul>{/if}
		</div>
	{/if}

	<p class="compte">{avec.length} {filtre.zone ? 'dans la zone visible' : 'dans le canton'}</p>
	{#each parJour(avec) as g (g.jour)}
		<h3>{g.jour}</h3>
		<ul>{#each g.entrees as e (e.cle)}{@render ligne(e)}{/each}</ul>
	{:else}
		<p class="vide">Rien de nouveau ici. Dézoomez, ou passez à « Tout le canton ».</p>
	{/each}
	<p class="note">Dossiers : mis à l’enquête ces 14 derniers jours (réels). Objets et séances : OpenParlData, 30 derniers jours. {court.format(new Date())}</p>
</section>

<style>
	.fil { background: var(--surface); padding: 12px 12px 16px; border-radius: 10px; box-shadow: 0 2px 10px rgb(0 0 0 / 0.18); }
	header { display: flex; align-items: center; }
	h2 { margin: 0; font-size: 18px; }
	.fermer { margin-left: auto; border: 0; background: none; font-size: 22px; cursor: pointer; color: var(--muted); }
	.puces { display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0 6px; }
	.puces button { border: 1px solid var(--c); color: var(--c); background: var(--surface); border-radius: 999px; padding: 4px 10px; font: inherit; font-size: 13px; cursor: pointer; }
	.puces button[aria-pressed='true'] { background: var(--c); color: #fff; }
	.qui { display: flex; align-items: center; gap: 6px; margin: 0 0 6px; padding: 4px 8px; border-radius: 6px; background: #e3f2f4; font-size: 13px; }
	.qui button { margin-left: auto; border: 0; background: none; font-size: 16px; cursor: pointer; color: var(--muted); }
	.portee { display: flex; gap: 14px; font-size: 13px; margin-bottom: 8px; }
	.sans { border: 1px dashed var(--line); border-radius: 8px; padding: 4px 6px; margin-bottom: 8px; background: var(--bg); }
	.tete-sans { border: 0; background: none; font: inherit; font-weight: 600; font-size: 14px; cursor: pointer; padding: 4px 2px; text-align: left; width: 100%; }
	.aide { display: block; font-weight: 400; font-size: 12px; color: var(--muted); }
	.compte { font-size: 13px; color: var(--muted); margin: 6px 0 0; }
	h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 12px 0 4px; }
	ul { list-style: none; margin: 0; padding: 0; }
	li { border-bottom: 1px solid var(--line); }
	li.ouvert { background: #fff6d6; }
	li > button { display: flex; gap: 8px; align-items: flex-start; width: 100%; text-align: left; border: 0; background: none; padding: 7px 2px; font: inherit; cursor: pointer; }
	li > button:hover { background: var(--bg); }
	.signe { flex: none; width: 22px; height: 22px; border-radius: 6px; background: var(--c); color: #fff; display: grid; place-items: center; font-size: 12px; font-weight: 700; }
	.texte { display: grid; gap: 1px; min-width: 0; }
	.meta { font-size: 12px; color: var(--muted); }
	.titre { font-size: 14px; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
	.fleche { margin-left: auto; color: var(--muted); }
	.vide, .note { font-size: 13px; color: var(--muted); }
	.note { margin-top: 14px; font-size: 11px; }
</style>
