<script lang="ts">
	/*
	 * PROTOTYPE (ticket #45), variante C « Bandeau sur la carte » : le fil est un bandeau en bas de la carte, des
	 * cartes qui défilent de gauche à droite, la plus récente à gauche. Il suit toujours la zone visible (pas de
	 * choix de portée : dézoomer, c'est voir le canton). Les éléments sans commune sont regroupés dans une première
	 * carte « Tout le canton » qui déplie leur liste au-dessus du bandeau. Types en boutons-icônes cumulables ;
	 * « Agrandir » fait du bandeau une grille sur la moitié de la carte. Sur téléphone, le même bandeau, au-dessus
	 * de la barre, masqué quand un aperçu est affiché.
	 */
	import { onMount } from 'svelte';
	import { permis } from '#lib/couches/permis/donnees.svelte.js';
	import type { Registre } from '#lib/registre/registre.svelte.js';
	import type { Commune } from '#lib/types.js';
	import { Filtre, TYPES, dansZone, jour, sansRattachement, surligner, toutes, typeDe, type Entree } from './entrees.svelte.js';
	import Deplie from './Deplie.svelte';

	let { registre, communes, telephone = false }: { registre: Registre; communes: readonly Commune[]; telephone?: boolean } = $props();

	onMount(() => {
		permis.chargerActifs().catch(() => {});
		return () => surligner(registre.map, null);
	});

	const filtre = new Filtre();
	const tout = $derived(toutes(communes).filter((e) => filtre.types.includes(e.type)));
	const sans = $derived(tout.filter(sansRattachement));
	const avec = $derived(tout.filter((e) => !sansRattachement(e) && dansZone(e, registre.zone)));
	let canton = $state(false);
	let grand = $state(false);
	let deplie = $state<string | null>(null);
	const ouvertCle = $derived(registre.ouvert ? `${registre.ouvert.couche === 'permis' ? 'd' : 'o'}:${registre.ouvert.element}` : null);
</script>

{#snippet carte(e: Entree)}
	{@const t = typeDe(e.type)}
	<li>
		<button
			type="button"
			class="carte"
			class:ouvert={ouvertCle === e.cle}
			style:--c={t.couleur}
			onclick={() => e.cible && registre.ouvrir(e.cible)}
			onmouseenter={() => surligner(registre.map, e)}
			onmouseleave={() => surligner(registre.map, null)}
		>
			<span class="haut"><span class="type">{t.signe} {e.sorte}</span><span class="date">{e.avenir ? 'à venir · ' : ''}{jour(e.date)}</span></span>
			<span class="titre">{e.titre}</span>
			<span class="qui">{e.communes.length ? e.communes.map((c) => c.nom).join(', ') : e.qui}{#if e.conseil} · {e.conseil.conseil === null ? 'Grand Conseil' : 'Conseil communal'}{/if}</span>
		</button>
	</li>
{/snippet}

<section class="bandeau" class:grand class:telephone aria-label="Fil cantonal">
	{#if canton}
		<div class="canton-liste">
			<header><strong>Tout le canton · sans commune</strong><button type="button" aria-label="Fermer" onclick={() => (canton = false)}>×</button></header>
			<ul>
				{#each sans as e (e.cle)}
					{@const t = typeDe(e.type)}
					<li>
						<button type="button" class="ligne" onclick={() => (deplie = deplie === e.cle ? null : e.cle)}>
							<span style:color={t.couleur}>{t.signe}</span> {e.sorte} · {jour(e.date)} — {e.titre}
						</button>
						{#if deplie === e.cle}<Deplie {e} />{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}
	<div class="barre-c">
		<strong>Fil cantonal</strong>
		<span class="compte">{avec.length} dans la zone</span>
		<span class="types">
			{#each TYPES as t (t.id)}
				<button type="button" title={t.nom} aria-label={t.nom} aria-pressed={filtre.types.includes(t.id)} style:--c={t.couleur} onclick={() => filtre.basculer(t.id)}>{t.signe}</button>
			{/each}
		</span>
		{#if !telephone}<button type="button" class="agrandir" onclick={() => (grand = !grand)}>{grand ? 'Réduire ▼' : 'Agrandir ▲'}</button>{/if}
	</div>
	<ul class="cartes">
		{#if sans.length}
			<li>
				<button type="button" class="carte canton-carte" aria-expanded={canton} onclick={() => (canton = !canton)}>
					<span class="haut"><span class="type">Tout le canton</span></span>
					<span class="titre">{sans.length} nouveautés sans commune</span>
					<span class="qui">Grand Conseil · {canton ? 'masquer' : 'voir la liste'}</span>
				</button>
			</li>
		{/if}
		{#each avec as e (e.cle)}{@render carte(e)}{/each}
		{#if !avec.length}<li class="vide">Rien de nouveau dans cette zone. Dézoomez pour voir plus loin.</li>{/if}
	</ul>
</section>

<style>
	.bandeau { position: absolute; z-index: 3; left: 10px; right: 10px; bottom: 30px; display: flex; flex-direction: column; gap: 6px; pointer-events: none; }
	.bandeau > * { pointer-events: auto; }
	.barre-c { align-self: flex-start; display: flex; gap: 10px; align-items: center; background: var(--surface); border-radius: 999px; padding: 4px 6px 4px 14px; box-shadow: 0 1px 6px rgb(0 0 0 / 0.18); font-size: 13px; }
	.compte { color: var(--muted); }
	.types { display: flex; gap: 3px; }
	.types button { width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--c); background: var(--surface); color: var(--c); font-weight: 700; cursor: pointer; }
	.types button[aria-pressed='true'] { background: var(--c); color: #fff; }
	.agrandir { border: 0; background: var(--bg); border-radius: 999px; padding: 4px 10px; font: inherit; font-size: 12px; cursor: pointer; }
	.cartes { list-style: none; margin: 0; padding: 2px 2px 6px; display: flex; gap: 8px; overflow-x: auto; scroll-snap-type: x mandatory; }
	.cartes > li { flex: none; scroll-snap-align: start; }
	.grand .cartes { flex-wrap: wrap; overflow-y: auto; max-height: 45vh; background: rgb(255 255 255 / 0.6); border-radius: 10px; padding: 8px; }
	.carte { width: 230px; height: 104px; display: flex; flex-direction: column; gap: 3px; text-align: left; border: 0; border-top: 4px solid var(--c, #444); border-radius: 10px; background: var(--surface); box-shadow: 0 1px 6px rgb(0 0 0 / 0.18); padding: 8px 10px; font: inherit; cursor: pointer; overflow: hidden; }
	.carte:hover, .carte.ouvert { outline: 2px solid #e0a800; }
	.canton-carte { --c: #555; background: #f3f3f3; }
	.haut { display: flex; font-size: 11px; }
	.type { color: var(--c); font-weight: 700; }
	.date { margin-left: auto; color: var(--muted); }
	.titre { font-size: 13px; font-weight: 600; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
	.qui { margin-top: auto; font-size: 11px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.vide { align-self: center; background: var(--surface); padding: 8px 12px; border-radius: 8px; font-size: 13px; color: var(--muted); }
	.canton-liste { max-width: 520px; max-height: 40vh; overflow-y: auto; background: var(--surface); border-radius: 10px; box-shadow: 0 2px 10px rgb(0 0 0 / 0.2); padding: 8px 12px; }
	.canton-liste header { display: flex; align-items: center; font-size: 14px; }
	.canton-liste header button { margin-left: auto; border: 0; background: none; font-size: 20px; cursor: pointer; }
	.canton-liste ul { list-style: none; padding: 0; margin: 4px 0 0; }
	.ligne { border: 0; background: none; text-align: left; font: inherit; font-size: 13px; padding: 5px 0; cursor: pointer; width: 100%; border-bottom: 1px solid var(--line); }
	.telephone { left: 0; right: 0; bottom: 8px; }
	.telephone .barre-c { margin-left: 8px; }
	.telephone .cartes { padding-left: 8px; padding-right: 8px; }
	.telephone .carte { width: 78vw; }
</style>
