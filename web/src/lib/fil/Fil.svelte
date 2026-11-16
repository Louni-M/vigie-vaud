<script lang="ts">
	/*
	 * Le fil cantonal, à la place des volets : il ne fait qu'afficher ce que calcule `calculerFil`. En tête, une ligne
	 * par couche en panne, les puces des types et la portée ; puis « Sans commune (n) », « À venir » et les jours.
	 * Une entrée est un lien vers son élément sur la carte (`lienElement`) : un clic simple l'ouvre par le registre,
	 * dans l'onglet de sa couche et la fiche de sa commune (sur téléphone, en aperçu sur la carte) ; Cmd, Ctrl ou le
	 * bouton du milieu l'ouvrent dans un autre onglet. Survolée, elle est surlignée sur la carte.
	 */
	import { onMount } from 'svelte';
	import type { GeoJSONSource, GeoJSONSourceSpecification } from 'maplibre-gl';
	import { typographier } from '#lib/almanach/typographie.js';
	import { clicSimple, lienElement } from '#lib/registre/liens.js';
	import type { Registre } from '#lib/registre/registre.svelte.js';
	import type { Commune } from '#lib/types.js';
	import type { ChargementFil } from './chargement.svelte.js';
	import { calculerFil, jourDe, type LigneFil, type ReglagesFil } from './fil.js';

	let {
		registre,
		chargement,
		communes,
		onfermer
	}: {
		registre: Registre;
		chargement: ChargementFil;
		communes: readonly Commune[];
		onfermer?: () => void;
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

	/** Clic simple : le registre ouvre l'entrée sur place ; avec une touche ou un autre bouton, le navigateur suit le lien. */
	function ouvrir(e: MouseEvent, l: LigneFil) {
		if (!clicSimple(e)) return;
		e.preventDefault();
		registre.ouvrir({ couche: l.couche, element: l.element, position: l.position });
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

	/*
	 * La méta : « Motion · Grand Conseil → Morges, Lausanne », avec la date courte hors des jours (« · 20 oct. »).
	 * La flèche n'est que vue ; le lecteur d'écran entend « Grand Conseil, communes nommées : Morges, Lausanne ».
	 */
	const avantFleche = (l: LigneFil) => typographier(`${l.sorte} · ${l.qui}`);
	const apresFleche = (l: LigneFil, date: boolean) =>
		typographier(l.nommees.join(', ')) + (date ? ` · ${fmtCourt.format(midi(l.date))}` : '');

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
		<a
			href={lienElement(l.couche, l.element)}
			aria-current={estOuverte(l) ? 'true' : undefined}
			onclick={(e) => ouvrir(e, l)}
			onmouseenter={() => surligner(l)}
			onmouseleave={() => surligner(null)}
			onfocus={() => surligner(l)}
			onblur={() => surligner(null)}
		>
			<!-- Le signe se lit par le nom de son type, avant la ligne. -->
			<span class="signe" style:--c={l.couleur} title={l.nomType} aria-hidden="true">{l.signe}</span>
			<span class="lecteur-seul">{l.nomType}&nbsp;:</span>
			<span class="texte">
				<span class="meta"
					>{avantFleche(l)}{#if l.nommees.length}<span aria-hidden="true">&nbsp;→ </span><span
							class="lecteur-seul">, communes nommées&nbsp;: </span
						>{/if}{apresFleche(l, date)}</span
				>
				<span class="titre">{typographier(l.titre)}</span>
			</span>
			<span class="fleche" aria-hidden="true">›</span>
		</a>
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
			{p.nom}&nbsp;: source indisponible,
			<button type="button" onclick={() => chargement.reessayer(p.couche)}>réessayer</button>
		</p>
	{/each}

	<div class="puces" role="group" aria-label="Types">
		{#each vue.puces as p (p.cle)}
			<button type="button" aria-pressed={p.active} style:--c={p.couleur} onclick={() => basculer(p.cle)}>
				<span aria-hidden="true">{p.signe}</span>
				{p.nom}
			</button>
		{/each}
	</div>
	<fieldset class="portee">
		<legend class="lecteur-seul">Portée</legend>
		<label>
			<input type="radio" name="portee-fil" value="zone" bind:group={reglages.portee} /> Zone visible
		</label>
		<label>
			<input type="radio" name="portee-fil" value="canton" bind:group={reglages.portee} /> Tout le canton
		</label>
	</fieldset>

	{#if vue.aideSansCommune !== null}
		<div class="sans">
			<button
				type="button"
				class="tete-sans"
				aria-expanded={sansCommuneOuvert}
				onclick={() => (sansCommuneOuvert = !sansCommuneOuvert)}
			>
				<span aria-hidden="true">{sansCommuneOuvert ? '▾' : '▸'}</span> Sans commune ({vue.sansCommune.length})
				<span class="aide">{vue.aideSansCommune}</span>
			</button>
			{#if sansCommuneOuvert && vue.sansCommune.length}
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
			<p class="vide">Rien de nouveau ici. Dézoomez, ou passez à «&nbsp;Tout le canton&nbsp;».</p>
		{:else}
			<p class="vide">Rien de nouveau ces 14 derniers jours.</p>
		{/if}
	{/if}
</section>

<style>
	/* Le fil : la feuille posée sur la carte, un filet d'encre en tête, rien d'autre. */
	.fil {
		padding: var(--space-md) var(--space-md) var(--space-lg);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		font-size: 14px;
	}
	header {
		display: flex;
		align-items: center;
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: var(--text-lg);
		font-weight: 600;
		letter-spacing: var(--tracking-display);
		color: var(--color-ink);
	}
	.fermer {
		width: 32px;
		height: 32px;
		margin: -4px -6px -4px 0;
		border: 0;
		background: none;
		font-size: 22px;
		line-height: 1;
		color: var(--color-muted);
		cursor: pointer;
	}
	.fermer:hover {
		background: var(--color-paper);
		color: var(--color-ink);
	}
	.panne {
		margin: 8px 0 0;
		color: var(--color-erreur);
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
	/* Les types du fil : une puce à angle droit ; choisie, elle prend un lavis de sa couleur et son filet, plutôt qu'un
	   aplat qui mettrait quatre couleurs vives en tête du volet. */
	.puces button {
		padding: 4px 10px;
		border: 1px solid var(--color-rule);
		border-radius: var(--radius-pill);
		background: var(--color-sheet);
		font: inherit;
		font-size: 13px;
		color: var(--color-muted);
		cursor: pointer;
	}
	.puces button[aria-pressed='true'] {
		border-color: var(--c);
		background: color-mix(in oklch, var(--c) 12%, var(--color-sheet));
		color: var(--color-ink);
		font-weight: 500;
	}
	/* Au survol, la puce prend un lavis de sa couleur ; choisie, elle fonce son lavis et se cerne de sa couleur. */
	.puces button:not([aria-pressed='true']):hover {
		background: color-mix(in oklch, var(--c) 8%, var(--color-sheet));
	}
	.puces button[aria-pressed='true']:hover {
		background: color-mix(in oklch, var(--c) 24%, var(--color-sheet));
		box-shadow: 0 0 0 1px var(--c);
	}
	.portee {
		display: flex;
		gap: 14px;
		/* Le cadre du <fieldset> n'est pas montré : la portée reste une ligne de réglage. */
		min-width: 0;
		margin: 0 0 8px;
		padding: 0;
		border: 0;
		font-size: 13px;
	}
	.sans {
		margin-bottom: 8px;
		padding: 4px 6px;
		border-top: var(--rule-hair) solid var(--color-rule);
		background: var(--color-paper);
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
	.tete-sans:hover {
		background: var(--color-paper-2);
	}
	.aide {
		display: block;
		font-weight: 400;
		font-size: 12px;
		color: var(--color-muted);
	}
	.compte {
		margin: 6px 0 0;
		font-size: 13px;
		color: var(--color-muted);
	}
	/* Le fil cantonal : intertitres en casse de phrase, lignes réglées, l'entrée ouverte sur un lavis orange. */
	h3 {
		margin: var(--space-md) 0 4px;
		padding-bottom: var(--space-2xs);
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
		font-size: var(--text-xs);
		font-weight: 600;
		color: var(--color-ink);
	}
	ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		border-bottom: 1px solid var(--color-rule);
	}
	li.ouvert {
		background: var(--color-accent-wash);
		box-shadow: inset var(--rule-bar) 0 0 var(--color-accent);
	}
	li > a {
		display: flex;
		align-items: flex-start;
		gap: 8px;
		width: 100%;
		padding: 7px var(--space-xs);
		color: inherit;
		text-decoration: none;
		text-align: left;
		/*
		 * Quatorze jours d'entrées : celles hors de l'écran ne sont ni mises en page ni dessinées. Sur le lien et non
		 * sur le `li`, dont le confinement couperait l'anneau du focus.
		 */
		content-visibility: auto;
		contain-intrinsic-size: auto 64px;
	}
	li > a:hover {
		background: var(--color-paper);
	}
	/* L'entrée ouverte garde son lavis orange au survol : son titre s'y souligne d'orange. */
	li.ouvert > a:hover {
		background: none;
	}
	li.ouvert > a:hover .titre {
		text-decoration: underline var(--rule-bar) var(--color-accent);
		text-underline-offset: 0.18em;
	}
	.signe {
		display: grid;
		flex: none;
		place-items: center;
		width: 22px;
		height: 22px;
		border-radius: var(--radius-pill);
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
		color: var(--color-muted);
	}
	.titre {
		font-family: var(--font-body);
		font-size: 0.9375rem;
		line-height: 1.35;
		color: var(--color-ink);
		display: -webkit-box;
		overflow: hidden;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
	}
	.fleche {
		margin-left: auto;
		color: var(--color-muted);
	}
	.vide {
		font-size: 13px;
		color: var(--color-muted);
	}
</style>
