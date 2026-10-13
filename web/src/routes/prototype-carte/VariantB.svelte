<script lang="ts">
	/*
	 * PROTOTYPE jetable (ticket #7), variante B : « carte pleine, fiches empilées ».
	 * Bureau : la carte occupe tout ; recherche et menu « Couches » flottent en haut à gauche, les réglages
	 * s'ouvrent dans le menu (second volet) ; les fiches sont des cartes à droite, le dossier s'empile sur la commune.
	 * Badges : tous ceux de la fiche, dans son en-tête. Mobile : feuilles en bas, empilées elles aussi.
	 */
	import { fly, fade } from 'svelte/transition';
	import { MediaQuery } from 'svelte/reactivity';
	import { STATUTS } from '#lib/labels.js';
	import ProtoCarte from './ProtoCarte.svelte';
	import Badge from './parts/Badge.svelte';
	import Reglages from './parts/Reglages.svelte';
	import OngletPermis from './parts/OngletPermis.svelte';
	import OngletFutur from './parts/OngletFutur.svelte';
	import Dossier from './parts/Dossier.svelte';
	import GrandConseil from './parts/GrandConseil.svelte';
	import Chercher from './parts/Chercher.svelte';
	import type { Proto } from './proto.svelte.js';

	let { p }: { p: Proto } = $props();
	const mobile = new MediaQuery('(max-width: 760px)', false);

	let menu: false | 'couches' | 'reglages' = $state(false);
	let pleine = $state(false);
	const base = $derived(p.commune || p.gc);
	const ouvert = $derived(!!(base || p.dossier));
	let fenetre = $state(800);
	const feuille = $derived(pleine ? Math.round(fenetre * 0.88) : Math.round(fenetre * 0.5));
	const marge = $derived(
		mobile.current
			? { top: 60, right: 0, left: 0, bottom: ouvert ? feuille : 0 }
			: { top: 0, right: ouvert ? 436 : 0, left: 0, bottom: 0 }
	);
</script>

<svelte:window bind:innerHeight={fenetre} />

<div class="app" class:mobile={mobile.current}>
	<ProtoCarte {p} {marge} />

	<div class="flottant">
		<div class="barre-haut">
			<Chercher {p} />
			<button class="bouton secondaire couches-btn" type="button" aria-expanded={!!menu} onclick={() => (menu = menu ? false : 'couches')}>
				☰ Couches
			</button>
		</div>
		{#if menu}
			<div class="menu" transition:fly={{ y: -8, duration: 150 }}>
				{#if menu === 'couches'}
					<div class="couche">
						<label><input type="checkbox" bind:checked={p.permis} /> <strong>Permis de construire</strong></label>
						<button class="lien" type="button" onclick={() => (menu = 'reglages')}>Réglages ›</button>
					</div>
					<div class="couche">
						<span><span class="cadenas">🔒</span> <strong>Hôtels de ville</strong> <small>toujours affichée</small></span>
					</div>
				{:else}
					<button class="lien" type="button" onclick={() => (menu = 'couches')}>‹ Couches</button>
					<h3>Permis de construire</h3>
					<Reglages {p} />
				{/if}
			</div>
		{/if}
	</div>

	{#if p.permis && !(mobile.current && ouvert)}
		<div class="legende" transition:fade={{ duration: 150 }}>
			{#each p.statuts as s (s)}<span><i style:background={STATUTS[s].couleur}></i>{STATUTS[s].court}</span>{/each}
			<Badge {p} source="permis" />
		</div>
	{/if}

	<div class="pile" style:--f="{feuille}px">
		{#if base}
			{#key `${p.commune?.slug}-${p.gc}`}
				<section class="carte-fiche" class:dessous={!!p.dossier} in:fly={{ x: mobile.current ? 0 : 40, y: mobile.current ? 40 : 0, duration: 220 }}>
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
					<header onclick={() => p.dossier && p.fermer()}>
						{#if mobile.current}<button class="poignee" type="button" onclick={() => (pleine = !pleine)} aria-label="Agrandir"><span></span></button>{/if}
						<div class="titre">
							<h2>{p.gc ? 'Grand Conseil' : p.commune?.nom}</h2>
							<button class="fermer" type="button" onclick={(e) => { e.stopPropagation(); p.toutFermer(); }} aria-label="Fermer">×</button>
						</div>
						{#if p.commune}
							<div class="badges">
								{#each p.onglets as o (o.id)}<Badge {p} source={o.id} />{/each}
							</div>
						{/if}
					</header>
					{#if !p.dossier}
						<div class="corps">
							{#if p.gc}<GrandConseil />
							{:else if p.commune}
								<div class="onglets" role="tablist">
									{#each p.onglets as o (o.id)}
										<button type="button" role="tab" aria-selected={p.onglet === o.id} onclick={() => (p.onglet = o.id)}>{o.nom}</button>
									{/each}
								</div>
								{#if p.onglet === 'permis'}<OngletPermis {p} commune={p.commune} />
								{:else}<OngletFutur onglet={p.onglet} nom={p.onglets.find((o) => o.id === p.onglet)?.nom ?? ''} />{/if}
							{/if}
						</div>
					{/if}
				</section>
			{/key}
		{/if}
		{#if p.dossier}
			{#key p.dossier.id}
				<section class="carte-fiche dessus" class:seule={!base} in:fly={{ x: mobile.current ? 0 : 40, y: mobile.current ? 60 : 0, duration: 220 }}>
					<header>
						{#if mobile.current}<button class="poignee" type="button" onclick={() => (pleine = !pleine)} aria-label="Agrandir"><span></span></button>{/if}
						<div class="titre">
							<span class="fil">{p.commune ? `${p.commune.nom} › ` : ''}Dossier n° {p.dossier.id}</span>
							<button class="fermer" type="button" onclick={() => p.fermer()} aria-label="Fermer le dossier">×</button>
						</div>
						<div class="badges"><Badge {p} source="permis" /></div>
					</header>
					<div class="corps"><Dossier {p} d={p.dossier} /></div>
				</section>
			{/key}
		{/if}
	</div>
</div>

<style>
	.app {
		position: relative;
		height: calc(100dvh - var(--header-h));
		overflow: hidden;
	}
	.flottant {
		position: absolute;
		z-index: 6;
		top: 12px;
		left: 12px;
		width: 380px;
		max-width: calc(100% - 24px);
	}
	.barre-haut {
		display: flex;
		gap: 6px;
		box-shadow: 0 2px 10px rgb(0 0 0 / 0.18);
		border-radius: 8px;
	}
	.couches-btn {
		white-space: nowrap;
		min-height: 0;
	}
	.menu {
		margin-top: 6px;
		background: var(--surface);
		border-radius: 10px;
		padding: 10px 12px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		display: flex;
		flex-direction: column;
		gap: 8px;
		font-size: 14px;
	}
	.menu h3 {
		margin: 0;
		font-size: 15px;
	}
	.couche {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 4px 0;
	}
	.couche small {
		color: var(--muted);
	}
	.cadenas {
		font-size: 12px;
	}
	.lien {
		border: 0;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: 13px;
		cursor: pointer;
		padding: 4px 0;
		text-align: left;
	}
	.legende {
		position: absolute;
		z-index: 4;
		left: 12px;
		bottom: 28px;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px 10px;
		padding: 6px 10px;
		background: rgb(255 255 255 / 0.94);
		border-radius: 8px;
		font-size: 12px;
		box-shadow: 0 1px 4px rgb(0 0 0 / 0.15);
	}
	.legende span {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.legende i {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}
	.pile {
		position: absolute;
		z-index: 5;
		top: 12px;
		right: 12px;
		bottom: 12px;
		width: 420px;
		pointer-events: none;
	}
	.carte-fiche {
		position: absolute;
		inset: 0 0 auto 0;
		max-height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-radius: 14px;
		box-shadow: 0 6px 24px rgb(0 0 0 / 0.22);
		pointer-events: auto;
		transition: transform 0.22s ease, opacity 0.22s ease;
	}
	/* La fiche commune reste visible derrière le dossier : on n'en voit plus que l'en-tête. */
	.carte-fiche.dessous {
		transform: translate(-14px, 0) scale(0.97);
		opacity: 0.85;
		cursor: pointer;
	}
	.carte-fiche.dessus {
		top: 74px;
		bottom: 0;
	}
	.carte-fiche.dessus.seule {
		top: 0;
	}
	header {
		padding: 12px 14px 8px;
		border-bottom: 1px solid var(--line);
	}
	.titre {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.titre h2 {
		flex: 1;
		margin: 0;
		font-size: 22px;
	}
	.fil {
		flex: 1;
		font-weight: 600;
		color: var(--muted);
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin-top: 6px;
	}
	.corps {
		overflow-y: auto;
		padding: 10px 14px 16px;
	}
	.fermer {
		width: 34px;
		height: 34px;
		border: 0;
		border-radius: 50%;
		background: var(--bg);
		font-size: 22px;
		color: var(--muted);
		cursor: pointer;
	}
	.onglets {
		display: flex;
		gap: 6px;
		margin-bottom: 10px;
	}
	.onglets button {
		border: 1px solid var(--line);
		background: var(--surface);
		border-radius: 999px;
		padding: 5px 12px;
		font: inherit;
		font-size: 13.5px;
		cursor: pointer;
	}
	.onglets button[aria-selected='true'] {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	/* Mobile : feuilles en bas, empilées ; le dossier recouvre la commune dont l'en-tête dépasse. */
	.mobile .flottant {
		top: 8px;
		left: 8px;
		right: 8px;
		width: auto;
	}
	.mobile .pile {
		inset: auto 0 0 0;
		width: auto;
		height: var(--f);
		transition: height 0.25s ease;
	}
	.mobile .carte-fiche {
		inset: 0;
		border-radius: 16px 16px 0 0;
	}
	.mobile .carte-fiche.dessous {
		transform: translateY(-40px) scale(0.96);
	}
	.mobile .carte-fiche.dessus {
		top: 0;
	}
	.poignee {
		display: block;
		width: 100%;
		height: 18px;
		margin-top: -6px;
		border: 0;
		background: none;
		cursor: pointer;
	}
	.poignee span {
		display: block;
		width: 40px;
		height: 5px;
		margin: auto;
		border-radius: 3px;
		background: #b8bfcc;
	}
</style>
