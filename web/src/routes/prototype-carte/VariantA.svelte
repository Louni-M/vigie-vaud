<script lang="ts">
	/*
	 * PROTOTYPE jetable (ticket #7), variante A : « colonne unique ».
	 * Bureau : une colonne à gauche (recherche, couches avec réglages dépliés sous l'interrupteur, puis la fiche).
	 * Une fiche remplace l'autre (pas d'empilement) : « ← Pully » ramène à la fiche commune.
	 * Mobile : la colonne entière devient un tiroir en bas, à trois hauteurs.
	 */
	import { untrack } from 'svelte';
	import { fly } from 'svelte/transition';
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

	let reglages = $state(false);
	let hauteur: 'bas' | 'mi' | 'haut' = $state('bas');
	const ouvert = $derived(!!(p.commune || p.dossier || p.gc));
	const cle = $derived(`${p.commune?.slug}-${p.dossier?.id}-${p.gc}`);
	// Le tiroir monte quand une fiche s'ouvre, redescend quand tout est fermé.
	$effect(() => {
		const o = ouvert;
		untrack(() => (hauteur = o ? (hauteur === 'haut' ? 'haut' : 'mi') : 'bas'));
	});
	const HAUTEURS = { bas: 150, mi: 0.55, haut: 0.9 };
	let fenetre = $state(800);
	const px = $derived(hauteur === 'bas' ? HAUTEURS.bas : Math.round(fenetre * HAUTEURS[hauteur]));
	const marge = $derived(mobile.current ? { top: 0, right: 0, left: 0, bottom: px } : { top: 0, right: 0, left: 0, bottom: 0 });
	const cycle = () => (hauteur = hauteur === 'bas' ? 'mi' : hauteur === 'mi' ? 'haut' : 'bas');
</script>

<svelte:window bind:innerHeight={fenetre} />

<div class="app">
	<aside class="colonne" style:--h="{px}px" class:tiroir={mobile.current}>
		{#if mobile.current}
			<button class="poignee" type="button" onclick={cycle} aria-label="Agrandir ou réduire le panneau"><span></span></button>
		{/if}
		<div class="haut">
			<Chercher {p} />
			<section class="couches" class:compactes={ouvert && !reglages}>
				<h2>Couches</h2>
				<div class="couche">
					<label class="ligne">
						<input type="checkbox" bind:checked={p.permis} />
						<span class="nom">Permis de construire</span>
						<button class="lien" type="button" onclick={(e) => { e.preventDefault(); reglages = !reglages; }} aria-expanded={reglages}>
							Réglages {reglages ? '▴' : '▾'}
						</button>
					</label>
					{#if !ouvert || reglages}
						<div class="sous" transition:fly={{ y: -6, duration: 150 }}>
							<Badge {p} source="permis" />
							<span class="legende">
								{#each p.statuts as s (s)}<span><i style:background={STATUTS[s].couleur}></i>{STATUTS[s].court}</span>{/each}
							</span>
						</div>
					{/if}
					{#if reglages}<div class="reglages" transition:fly={{ y: -6, duration: 150 }}><Reglages {p} /></div>{/if}
				</div>
				<div class="couche">
					<div class="ligne">
						<span class="cadenas" title="Couche permanente">🔒</span>
						<span class="nom">Hôtels de ville</span>
						{#if !ouvert}<Badge {p} source="hdv" />{/if}
					</div>
				</div>
			</section>
		</div>

		<div class="fiche-zone">
			{#key cle}
				<div class="fiche" in:fly={{ x: 24, duration: 200 }}>
					{#if p.dossier}
						<div class="entete">
							<button class="lien retour" type="button" onclick={() => p.retour()}>← {p.commune?.nom ?? 'Retour'}</button>
							<Badge {p} source="permis" />
							<button class="fermer" type="button" onclick={() => p.toutFermer()} aria-label="Fermer">×</button>
						</div>
						<Dossier {p} d={p.dossier} />
					{:else if p.gc}
						<div class="entete">
							<h2>Grand Conseil</h2>
							<button class="fermer" type="button" onclick={() => p.toutFermer()} aria-label="Fermer">×</button>
						</div>
						<GrandConseil />
					{:else if p.commune}
						<div class="entete">
							<h2>{p.commune.nom}</h2>
							<button class="fermer" type="button" onclick={() => p.toutFermer()} aria-label="Fermer">×</button>
						</div>
						{#if p.onglets.length > 1}
							<div class="onglets" role="tablist">
								{#each p.onglets as o (o.id)}
									<button type="button" role="tab" aria-selected={p.onglet === o.id} onclick={() => (p.onglet = o.id)}>{o.nom}</button>
								{/each}
							</div>
						{:else}
							<h3 class="seul">Permis de construire</h3>
						{/if}
						<p class="badge-onglet"><Badge {p} source={p.onglet} /></p>
						{#if p.onglet === 'permis'}<OngletPermis {p} commune={p.commune} />
						{:else}<OngletFutur onglet={p.onglet} nom={p.onglets.find((o) => o.id === p.onglet)?.nom ?? ''} />{/if}
					{:else}
						<p class="aide">Cliquez sur un hôtel de ville (point bleu foncé) pour ouvrir la fiche de la commune, ou sur un dossier pour sa fiche.</p>
					{/if}
				</div>
			{/key}
		</div>
	</aside>

	<div class="zone-carte"><ProtoCarte {p} {marge} /></div>
</div>

<style>
	.app {
		display: grid;
		grid-template-columns: 390px 1fr;
		height: calc(100dvh - var(--header-h));
	}
	.colonne {
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		background: var(--bg);
		border-right: 1px solid var(--line);
		padding: 12px 14px 80px;
		gap: 12px;
	}
	.zone-carte {
		position: relative;
	}
	.haut {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 18px;
	}
	.couches h2 {
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--muted);
		margin-bottom: 4px;
	}
	.couche {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 10px;
		padding: 8px 10px;
		margin-bottom: 6px;
	}
	.compactes .couche {
		padding: 4px 10px;
	}
	.ligne {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 14px;
	}
	.nom {
		font-weight: 600;
		flex: 1;
	}
	.sous {
		display: flex;
		flex-wrap: wrap;
		gap: 6px 10px;
		align-items: center;
		margin: 6px 0 0 26px;
	}
	.reglages {
		margin: 8px 0 2px 26px;
	}
	.legende {
		display: inline-flex;
		gap: 8px;
		font-size: 11.5px;
		color: var(--muted);
	}
	.legende span {
		display: inline-flex;
		align-items: center;
		gap: 4px;
	}
	.legende i {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.cadenas {
		width: 18px;
		text-align: center;
		font-size: 12px;
	}
	.lien {
		border: 0;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: 13px;
		cursor: pointer;
		padding: 4px;
	}
	.fiche-zone {
		border-top: 1px solid var(--line);
		padding-top: 12px;
	}
	.entete {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}
	.entete h2 {
		flex: 1;
		font-size: 22px;
	}
	.retour {
		font-size: 15px;
		font-weight: 600;
		padding-left: 0;
	}
	.entete .retour + :global(.badge) {
		margin-left: auto;
	}
	.fermer {
		width: 36px;
		height: 36px;
		border: 0;
		border-radius: 50%;
		background: var(--surface);
		font-size: 22px;
		color: var(--muted);
		cursor: pointer;
	}
	.onglets {
		display: flex;
		gap: 2px;
		border-bottom: 1px solid var(--line);
	}
	.onglets button {
		border: 0;
		background: none;
		padding: 8px 12px;
		font: inherit;
		font-size: 14px;
		color: var(--muted);
		cursor: pointer;
		border-bottom: 3px solid transparent;
	}
	.onglets button[aria-selected='true'] {
		color: var(--text);
		font-weight: 600;
		border-bottom-color: var(--enquete);
	}
	.seul {
		margin: 0;
		font-size: 13px;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: var(--muted);
	}
	.badge-onglet {
		margin: 8px 0;
	}
	.aide {
		color: var(--muted);
		font-size: 14px;
		line-height: 1.5;
	}

	/* Mobile : carte plein écran, la colonne devient un tiroir. */
	@media (max-width: 760px) {
		.app {
			display: block;
			position: relative;
		}
		.zone-carte {
			position: absolute;
			inset: 0;
		}
		.colonne.tiroir {
			position: absolute;
			z-index: 5;
			left: 0;
			right: 0;
			bottom: 0;
			height: var(--h);
			border-right: 0;
			border-radius: 16px 16px 0 0;
			box-shadow: 0 -4px 20px rgb(0 0 0 / 0.2);
			padding-top: 0;
			transition: height 0.25s ease;
		}
		.poignee {
			position: sticky;
			top: 0;
			z-index: 1;
			flex: none;
			height: 24px;
			margin: 0 -14px;
			border: 0;
			background: var(--bg);
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
	}
</style>
