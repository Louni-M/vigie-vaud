<script lang="ts">
	/*
	 * Le fil cantonal, à la place des volets : il ne fait qu'afficher ce que calcule `calculerFil`. En tête, une ligne
	 * par couche en panne, les puces des types et la portée ; puis « Sans commune (n) », « À venir » et les jours.
	 * Une entrée s'ouvre par le registre, dans l'onglet de sa couche et la fiche de sa commune ; survolée, elle est
	 * surlignée sur la carte.
	 */
	import { onMount } from 'svelte';
	import type { GeoJSONSource, GeoJSONSourceSpecification } from 'maplibre-gl';
	import type { Registre } from '#lib/registre/registre.svelte.js';
	import type { Commune } from '#lib/types.js';
	import type { ChargementFil } from './chargement.svelte.js';
	import { calculerFil, jourDe, type LigneFil, type ReglagesFil } from './fil.js';

	let {
		registre,
		chargement,
		communes,
		onfermer,
		onouvert
	}: {
		registre: Registre;
		chargement: ChargementFil;
		communes: readonly Commune[];
		onfermer?: () => void;
		/** Une entrée vient d'être ouverte (téléphone : retour à la vue Carte, pour son aperçu). */
		onouvert?: () => void;
	} = $props();

	const aujourdhui = jourDe(new Date());

	// Première ouverture du fil : les couches sont lues une fois, activées ou non.
	onMount(() => {
		chargement.charger(aujourdhui);
		return () => surligner(null);
	});

	let reglages = $state<ReglagesFil>({ masques: [], portee: 'zone' });
	let sansCommuneOuvert = $state(true);

	const vue = $derived(
		calculerFil(chargement.sources, reglages, { aujourdhui, zone: registre.zoneFil, communes })
	);

	function basculer(cle: string) {
		const m = reglages.masques;
		reglages.masques = m.includes(cle) ? m.filter((x) => x !== cle) : [...m, cle];
	}

	const estOuverte = (l: LigneFil) => registre.ouvert?.couche === l.couche && registre.ouvert.element === l.element;

	function ouvrir(l: LigneFil) {
		registre.ouvrir({ couche: l.couche, element: l.element, position: l.position });
		onouvert?.();
	}

	/* ---- Jours : « Aujourd’hui », « Hier », « Mardi 7 oct. » ---- */

	const fmtJour = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'short' });
	const fmtCourt = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short' });
	const midi = (iso: string) => new Date(`${iso}T12:00:00`);
	function libelleJour(iso: string) {
		const n = Math.round((+midi(aujourdhui) - +midi(iso)) / 86_400_000);
		if (n === 0) return 'Aujourd’hui';
		if (n === 1) return 'Hier';
		const s = fmtJour.format(midi(iso));
		return s[0].toUpperCase() + s.slice(1);
	}

	/** « Motion · Grand Conseil → Morges, Lausanne », avec la date courte hors des jours (« · 20 oct. »). */
	function meta(l: LigneFil, date: boolean) {
		const qui = l.nommees.length ? `${l.qui} → ${l.nommees.join(', ')}` : l.qui;
		return [l.sorte, qui, ...(date ? [fmtCourt.format(midi(l.date))] : [])].join(' · ');
	}

	/* ---- Survol : l'entrée est surlignée sur la carte, à sa position ou à l'hôtel de ville de ses communes ---- */

	const CALQUE = 'fil-survol';
	const hotels = $derived(new Map(communes.map((c) => [c.slug, c.hotel])));

	function surligner(l: LigneFil | null) {
		const map = registre.map;
		if (!map) return;
		const points = !l ? [] : l.position ? [l.position] : l.communes.flatMap((c) => hotels.get(c) ?? []);
		const data: GeoJSONSourceSpecification['data'] = {
			type: 'FeatureCollection',
			features: points.map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }))
		};
		const source = map.getSource(CALQUE) as GeoJSONSource | undefined;
		if (source) return void source.setData(data);
		if (!l) return;
		map.addSource(CALQUE, { type: 'geojson', data });
		map.addLayer({
			id: CALQUE,
			type: 'circle',
			source: CALQUE,
			paint: {
				'circle-radius': 16,
				'circle-color': 'rgba(255, 200, 0, 0.25)',
				'circle-stroke-color': '#e0a800',
				'circle-stroke-width': 3
			}
		});
	}
</script>

{#snippet ligne(l: LigneFil, date = false)}
	<li class:ouvert={estOuverte(l)}>
		<button
			type="button"
			aria-current={estOuverte(l) ? 'true' : undefined}
			onclick={() => ouvrir(l)}
			onmouseenter={() => surligner(l)}
			onmouseleave={() => surligner(null)}
			onfocus={() => surligner(l)}
			onblur={() => surligner(null)}
		>
			<span class="signe" style:--c={l.couleur} title={l.nomType}>{l.signe}</span>
			<span class="texte">
				<span class="meta">{meta(l, date)}</span>
				<span class="titre">{l.titre}</span>
			</span>
			<span class="fleche" aria-hidden="true">›</span>
		</button>
	</li>
{/snippet}

<section class="fil" id="volet-fil" aria-labelledby="fil-titre">
	<header>
		<h2 id="fil-titre">Fil cantonal</h2>
		{#if onfermer}
			<button class="fermer" type="button" aria-label="Fermer le fil" onclick={onfermer}>×</button>
		{/if}
	</header>

	{#each vue.pannes as p (p.couche)}
		<p class="panne" role="alert">
			{p.nom} : source indisponible,
			<button type="button" onclick={() => chargement.reessayer(p.couche)}>réessayer</button>
		</p>
	{/each}

	<div class="puces" role="group" aria-label="Types">
		{#each vue.puces as p (p.cle)}
			<button type="button" aria-pressed={p.active} style:--c={p.couleur} onclick={() => basculer(p.cle)}>
				{p.signe}
				{p.nom}
			</button>
		{/each}
	</div>
	<div class="portee" role="radiogroup" aria-label="Portée">
		<label>
			<input type="radio" name="portee-fil" value="zone" bind:group={reglages.portee} /> Zone visible
		</label>
		<label>
			<input type="radio" name="portee-fil" value="canton" bind:group={reglages.portee} /> Tout le canton
		</label>
	</div>

	{#if vue.sansCommune.length}
		<div class="sans">
			<button
				type="button"
				class="tete-sans"
				aria-expanded={sansCommuneOuvert}
				onclick={() => (sansCommuneOuvert = !sansCommuneOuvert)}
			>
				<span aria-hidden="true">{sansCommuneOuvert ? '▾' : '▸'}</span> Sans commune ({vue.sansCommune.length})
				<span class="aide">Grand Conseil, sans commune nommée</span>
			</button>
			{#if sansCommuneOuvert}
				<ul>
					{#each vue.sansCommune as l (l.cle)}{@render ligne(l, true)}{/each}
				</ul>
			{/if}
		</div>
	{/if}

	<p class="compte" role="status">
		{vue.compteur}
		{reglages.portee === 'zone' ? 'dans la zone visible' : 'dans le canton'}
	</p>

	{#if vue.avenir.length}
		<h3>À venir</h3>
		<ul>
			{#each vue.avenir as l (l.cle)}{@render ligne(l, true)}{/each}
		</ul>
	{/if}
	{#each vue.jours as j (j.date)}
		<h3>{libelleJour(j.date)}</h3>
		<ul>
			{#each j.entrees as l (l.cle)}{@render ligne(l)}{/each}
		</ul>
	{/each}

	{#if vue.compteur === 0}
		{#if vue.chargement}
			<p class="vide">Chargement…</p>
		{:else if reglages.portee === 'zone'}
			<p class="vide">Rien de nouveau ici. Dézoomez, ou passez à « Tout le canton ».</p>
		{:else}
			<p class="vide">Rien de nouveau ces 14 derniers jours.</p>
		{/if}
	{/if}
</section>

<style>
	.fil {
		padding: 12px 12px 16px;
		background: var(--surface);
		border-radius: 10px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		font-size: 14px;
	}
	header {
		display: flex;
		align-items: center;
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: 16px;
	}
	.fermer {
		width: 32px;
		height: 32px;
		margin: -4px -6px -4px 0;
		border: 0;
		border-radius: 50%;
		background: none;
		font-size: 22px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
	.fermer:hover {
		background: var(--bg);
	}
	.panne {
		margin: 8px 0 0;
		color: var(--erreur);
	}
	.panne button {
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: inherit;
		text-decoration: underline;
		cursor: pointer;
	}
	.puces {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		margin: 10px 0 6px;
	}
	.puces button {
		padding: 4px 10px;
		border: 1px solid var(--c);
		border-radius: 999px;
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: var(--c);
		cursor: pointer;
	}
	.puces button[aria-pressed='true'] {
		background: var(--c);
		color: #fff;
	}
	.portee {
		display: flex;
		gap: 14px;
		margin-bottom: 8px;
		font-size: 13px;
	}
	.sans {
		margin-bottom: 8px;
		padding: 4px 6px;
		border: 1px dashed var(--line);
		border-radius: 8px;
		background: var(--bg);
	}
	.tete-sans {
		width: 100%;
		padding: 4px 2px;
		border: 0;
		background: none;
		font: inherit;
		font-weight: 600;
		text-align: left;
		cursor: pointer;
	}
	.aide {
		display: block;
		font-weight: 400;
		font-size: 12px;
		color: var(--muted);
	}
	.compte {
		margin: 6px 0 0;
		font-size: 13px;
		color: var(--muted);
	}
	h3 {
		margin: 12px 0 4px;
		font-size: 12px;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--muted);
	}
	ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		border-bottom: 1px solid var(--line);
	}
	li.ouvert {
		background: #fff6d6;
	}
	li > button {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		width: 100%;
		padding: 7px 2px;
		border: 0;
		background: none;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	li > button:hover {
		background: var(--bg);
	}
	li.ouvert > button:hover {
		background: #fdeeb5;
	}
	.signe {
		display: grid;
		flex: none;
		place-items: center;
		width: 22px;
		height: 22px;
		border-radius: 6px;
		background: var(--c);
		font-size: 12px;
		font-weight: 700;
		color: #fff;
	}
	.texte {
		display: grid;
		gap: 1px;
		min-width: 0;
	}
	.meta {
		font-size: 12px;
		color: var(--muted);
	}
	.titre {
		display: -webkit-box;
		overflow: hidden;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}
	.fleche {
		margin-left: auto;
		color: var(--muted);
	}
	.vide {
		font-size: 13px;
		color: var(--muted);
	}
</style>
