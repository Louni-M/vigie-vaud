<script lang="ts">
	/*
	 * Coquille de la carte, commune à `/` et (bientôt) à `/commune/<slug>` : elle garde la carte montée pendant
	 * la navigation. Rail des couches à gauche, volet posé sur la carte, recherche flottante en haut ; la fiche
	 * commune viendra en colonne à droite. Les pages du groupe ne portent que le <head>.
	 */
	import { onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import { resolve } from '$app/paths';
	import Map, { CALQUE_REPERE } from '#lib/socle/Map.svelte';
	import Recherche from '#lib/socle/Recherche.svelte';
	import { getCommunes } from '#lib/socle/communes.js';
	import { COUCHES } from '#lib/registre/couches.js';
	import { creerRegistre } from '#lib/registre/registre.svelte.js';
	import { sourcesCarte } from '#lib/registre/attribution.js';
	import Rail from '#lib/registre/Rail.svelte';
	import Volet from '#lib/registre/Volet.svelte';
	import { attributionHtml, source } from '#lib/sources.js';
	import type { Commune, Resultat } from '#lib/types.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	const registre = creerRegistre(COUCHES);
	let carte: ReturnType<typeof Map> | undefined = $state();
	registre.brancherAdresse(() => carte);

	let communes: Commune[] = $state([]);
	onMount(() => {
		getCommunes(fetch).then(
			(c) => (communes = c),
			() => {}
		);
	});

	/** Adresse cherchée ou position GPS, marquée sur la carte ; jamais écrite dans l'URL. */
	let repere: [number, number] | null = $state(null);

	const attribution = $derived(sourcesCarte(COUCHES, registre.actives).map((id) => attributionHtml(source(id))));

	const chercherCouches = (texte: string) =>
		COUCHES.flatMap((c) =>
			(c.chercher?.(texte) ?? []).map((r) => ({
				type: 'element' as const,
				genre: c.nom,
				label: r.libelle,
				couche: r.couche,
				element: r.element
			}))
		);

	function choix(r: Resultat) {
		if (r.type === 'adresse') {
			repere = [r.lon, r.lat];
			carte?.voler(r.lon, r.lat, r.genre === 'Position' ? 15 : 16);
		} else if (r.type === 'commune') {
			repere = null;
			carte?.cadrer(r.commune.bbox);
		} else registre.ouvrir({ couche: r.couche, element: r.element });
	}

	/** Lien d'évitement : le clavier n'a pas à traverser le rail et la recherche pour atteindre la carte. */
	async function allerCarte(e: MouseEvent) {
		e.preventDefault();
		await tick();
		document.querySelector<HTMLElement>('#carte .maplibregl-canvas')?.focus();
	}

	function fermerVolet() {
		const id = registre.volet;
		registre.volet = null;
		// Le focus revient à l'icône du rail qui avait ouvert le volet.
		tick().then(() => document.querySelector<HTMLElement>(`[data-couche="${id}"]`)?.focus());
	}
</script>

<div class="app">
	<a class="evitement" href="#carte" onclick={allerCarte}>Aller à la carte</a>

	<Rail {registre} />

	<div class="zone-carte" id="carte">
		<Map
			bind:this={carte}
			{repere}
			{attribution}
			onpret={(m) => registre.carte(m, CALQUE_REPERE)}
			onvue={registre.deplacement}
		/>

		<!-- Calques de chaque couche, dans l'ordre du registre ; importés à la première activation. -->
		{#if registre.map}
			{#each COUCHES as c (c.id)}
				{#if registre.montee(c.id)}
					{#await registre.composant(c, 'Carte') then module}
						{#if module}<module.default ctx={registre.contexte(c)} />{/if}
					{/await}
				{/if}
			{/each}
		{/if}

		<div class="recherche">
			<Recherche {communes} {chercherCouches} onchoix={choix} />
		</div>

		<!-- Un bloc par couche : le volet qui se ferme garde sa couche pendant qu'il disparaît. -->
		{#each COUCHES as c (c.id)}
			{#if registre.volet === c.id}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="volet"
					transition:fly={{ x: -20, duration: 160 }}
					onkeydown={(e) => e.key === 'Escape' && fermerVolet()}
				>
					<Volet couche={c} {registre} onfermer={fermerVolet} />
				</div>
			{/if}
		{/each}

		<p class="liens">
			<a href={resolve('/a-propos')}>À propos</a> ·
			<a href={resolve('/infos-legales')}>Informations légales</a>
		</p>
	</div>
</div>

{@render children()}

<style>
	.app {
		display: grid;
		grid-template-columns: 72px minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr);
		height: calc(100dvh - var(--header-h));
		position: relative;
	}
	.zone-carte {
		position: relative;
		overflow: hidden;
	}
	.recherche {
		position: absolute;
		z-index: 4;
		top: 10px;
		left: 10px;
		width: min(360px, calc(100% - 70px));
		border-radius: 10px;
		box-shadow: 0 2px 10px rgb(0 0 0 / 0.18);
	}
	.volet {
		position: absolute;
		z-index: 3;
		top: 66px;
		left: 10px;
		bottom: 34px;
		width: min(360px, calc(100% - 20px));
		overflow-y: auto;
		border-radius: 10px;
		/* Le volet est à la hauteur de son contenu, sans dépasser le bas de la carte. */
		height: fit-content;
		max-height: calc(100% - 100px);
	}
	.liens {
		position: absolute;
		z-index: 2;
		left: 10px;
		bottom: 8px;
		margin: 0;
		padding: 2px 8px;
		border-radius: 6px;
		background: rgb(255 255 255 / 0.85);
		font-size: 12px;
		color: var(--muted);
	}
	.evitement {
		position: absolute;
		z-index: 30;
		left: 8px;
		top: 8px;
		padding: 10px 14px;
		border-radius: 8px;
		background: var(--surface);
		font-weight: 600;
		box-shadow: 0 2px 8px rgb(0 0 0 / 0.2);
	}
	/* Visible seulement au clavier, quand il reçoit le focus. */
	.evitement:not(:focus) {
		width: 1px;
		height: 1px;
		padding: 0;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
