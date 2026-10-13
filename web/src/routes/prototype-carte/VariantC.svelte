<script lang="ts">
	/*
	 * PROTOTYPE jetable (ticket #7), variante C : « rail des couches, dossier dans l'onglet ».
	 * Bureau : un rail d'icônes à gauche, une icône par couche ; un clic ouvre son volet (interrupteur, badge,
	 * légende, réglages). La fiche commune est une colonne à droite qui n'existe que si une fiche est ouverte ;
	 * un dossier s'ouvre DANS l'onglet Permis (fil « Permis › n° … »), les onglets restent visibles.
	 * Ouvrir un dossier sur la carte ouvre aussi la fiche de sa commune. Badge : sous le nom de chaque onglet.
	 * Mobile : barre d'onglets en bas (Carte · Couches · Fiche) et aperçu sur la carte, comme Chantiers Vaud.
	 */
	import { untrack } from 'svelte';
	import { fly, slide } from 'svelte/transition';
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
	import { libelleBadge, type Proto } from './proto.svelte.js';

	let { p }: { p: Proto } = $props();
	const mobile = new MediaQuery('(max-width: 760px)', false);

	let volet: null | 'permis' | 'hdv' = $state(null);
	let vue: 'carte' | 'couches' | 'fiche' = $state('carte');
	const ouvert = $derived(!!(p.commune || p.gc));

	// Un dossier ouvert depuis la carte emmène sa commune avec lui.
	$effect(() => {
		const d = p.dossier;
		untrack(() => {
			if (!d) return;
			const c = p.communeDe(d);
			if (c && p.commune?.slug !== c.slug) p.commune = c;
			p.onglet = 'permis';
		});
	});
	$effect(() => {
		if (!ouvert) untrack(() => vue === 'fiche' && (vue = 'carte'));
	});
</script>

<div class="app" class:avec-fiche={ouvert} class:mobile={mobile.current} data-vue={vue}>
	{#if !mobile.current}
		<nav class="rail" aria-label="Couches">
			<button type="button" class:actif={volet === 'permis'} onclick={() => (volet = volet === 'permis' ? null : 'permis')}>
				<span class="icone" class:off={!p.permis} style:--c={STATUTS.enquete.couleur}>P</span>Permis
			</button>
			<button type="button" class:actif={volet === 'hdv'} onclick={() => (volet = volet === 'hdv' ? null : 'hdv')}>
				<span class="icone" style:--c="#1f3a5f">⌂</span>Hôtels de ville
			</button>
		</nav>
	{/if}

	<div class="zone-carte">
		<ProtoCarte {p} />
		<div class="recherche"><Chercher {p} /></div>

		{#if volet && !mobile.current}
			<div class="volet" transition:fly={{ x: -20, duration: 160 }}>
				{@render contenuVolet(volet)}
			</div>
		{/if}

		{#if mobile.current && (p.commune || p.gc)}
			<button class="apercu" type="button" onclick={() => (vue = 'fiche')} in:fly={{ y: 30, duration: 200 }}>
				<strong>{p.dossier ? `Dossier n° ${p.dossier.id}` : p.gc ? 'Grand Conseil' : p.commune?.nom}</strong>
				<span>{p.dossier ? p.commune?.nom : p.gc ? 'Parlement vaudois' : `${p.actifs.filter((d) => d.slug === p.commune?.slug && d.statut === 'enquete').length} à l’enquête`} · Voir la fiche ›</span>
			</button>
		{/if}
	</div>

	{#if mobile.current && vue === 'couches'}
		<div class="plein">
			{@render contenuVolet('permis')}
			<hr />
			{@render contenuVolet('hdv')}
		</div>
	{/if}

	{#if ouvert}
		<aside class="fiche" in:fly={{ x: 40, duration: 200 }}>
			<div class="entete">
				<h2>{p.gc ? 'Grand Conseil' : p.commune?.nom}</h2>
				<button class="fermer" type="button" onclick={() => p.toutFermer()} aria-label="Fermer">×</button>
			</div>
			{#if p.gc}
				<div class="corps"><GrandConseil /></div>
			{:else if p.commune}
				<div class="onglets" role="tablist">
					{#each p.onglets as o (o.id)}
						<button type="button" role="tab" aria-selected={p.onglet === o.id} onclick={() => (p.onglet = o.id)}>
							{o.nom}<small>{libelleBadge(p.sources[o.id], p.maintenant)}</small>
						</button>
					{/each}
				</div>
				<div class="corps">
					{#if p.onglet === 'permis'}
						{#if p.dossier}
							{#key p.dossier.id}
								<div in:fly={{ x: 20, duration: 160 }}>
									<p class="fil">
										<button class="lien" type="button" onclick={() => p.fermer()}>Permis</button> › n° {p.dossier.id}
									</p>
									<Dossier {p} d={p.dossier} />
								</div>
							{/key}
						{:else}
							<OngletPermis {p} commune={p.commune} />
						{/if}
					{:else}
						<OngletFutur onglet={p.onglet} nom={p.onglets.find((o) => o.id === p.onglet)?.nom ?? ''} />
					{/if}
				</div>
			{/if}
		</aside>
	{/if}

	{#if mobile.current}
		<div class="barre-vues" role="group" aria-label="Affichage">
			<button type="button" aria-pressed={vue === 'carte'} onclick={() => (vue = 'carte')}>Carte</button>
			<button type="button" aria-pressed={vue === 'couches'} onclick={() => (vue = 'couches')}>Couches</button>
			<button type="button" aria-pressed={vue === 'fiche'} disabled={!ouvert} onclick={() => (vue = 'fiche')}>Fiche</button>
		</div>
	{/if}
</div>

{#snippet contenuVolet(id: 'permis' | 'hdv')}
	{#if id === 'permis'}
		<div class="volet-tete">
			<h3>Permis de construire</h3>
			<label class="interrupteur"><input type="checkbox" bind:checked={p.permis} /> affichée</label>
		</div>
		<Badge {p} source="permis" />
		<p class="attrib">Géodonnées État de Vaud (CAMAC), lues en direct.</p>
		{#if p.permis}<div transition:slide={{ duration: 150 }}><Reglages {p} /></div>{/if}
	{:else}
		<div class="volet-tete">
			<h3>Hôtels de ville</h3>
			<span class="perm">🔒 permanente</span>
		</div>
		<Badge {p} source="hdv" />
		<p class="attrib">Un marqueur par commune ; il ouvre sa fiche. Limites © swisstopo.</p>
	{/if}
{/snippet}

<style>
	.app {
		display: grid;
		grid-template-columns: 72px 1fr 0;
		height: calc(100dvh - var(--header-h));
		transition: grid-template-columns 0.22s ease;
	}
	.app.avec-fiche {
		grid-template-columns: 72px 1fr 420px;
	}
	.rail {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 8px 4px;
		background: var(--surface);
		border-right: 1px solid var(--line);
	}
	.rail button {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 8px 2px;
		border: 0;
		border-radius: 8px;
		background: none;
		font: inherit;
		font-size: 11px;
		color: var(--text);
		cursor: pointer;
		text-align: center;
	}
	.rail button.actif {
		background: #e8edf5;
	}
	.icone {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: 50%;
		background: var(--c);
		color: #fff;
		font-weight: 700;
		font-size: 15px;
	}
	.icone.off {
		background: var(--surface);
		color: var(--c);
		box-shadow: inset 0 0 0 2px var(--c);
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
		width: min(340px, calc(100% - 20px));
		box-shadow: 0 2px 10px rgb(0 0 0 / 0.18);
		border-radius: 8px;
	}
	.volet {
		position: absolute;
		z-index: 5;
		top: 58px;
		left: 10px;
		width: 300px;
		padding: 12px 14px;
		background: var(--surface);
		border-radius: 10px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.volet-tete {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.volet-tete h3 {
		margin: 0;
		font-size: 15px;
	}
	.interrupteur,
	.perm {
		font-size: 13px;
		display: flex;
		gap: 4px;
		align-items: center;
		color: var(--muted);
	}
	.attrib {
		margin: 0;
		font-size: 12px;
		color: var(--muted);
	}
	.fiche {
		display: flex;
		flex-direction: column;
		min-width: 0;
		overflow: hidden;
		background: var(--bg);
		border-left: 1px solid var(--line);
	}
	.entete {
		display: flex;
		align-items: center;
		padding: 12px 14px 4px;
	}
	.entete h2 {
		flex: 1;
		margin: 0;
		font-size: 22px;
	}
	.fermer {
		width: 34px;
		height: 34px;
		border: 0;
		border-radius: 50%;
		background: var(--surface);
		font-size: 22px;
		color: var(--muted);
		cursor: pointer;
	}
	.onglets {
		display: flex;
		padding: 0 10px;
		border-bottom: 1px solid var(--line);
		overflow-x: auto;
	}
	.onglets button {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		padding: 8px 10px 6px;
		border: 0;
		border-bottom: 3px solid transparent;
		background: none;
		font: inherit;
		font-size: 14px;
		font-weight: 600;
		color: var(--muted);
		cursor: pointer;
		white-space: nowrap;
	}
	.onglets button small {
		font-weight: 400;
		font-size: 10.5px;
	}
	.onglets button[aria-selected='true'] {
		color: var(--text);
		border-bottom-color: var(--enquete);
	}
	.corps {
		flex: 1;
		overflow-y: auto;
		padding: 12px 14px 80px;
	}
	.fil {
		margin: 0 0 8px;
		font-size: 14px;
		color: var(--muted);
	}
	.lien {
		border: 0;
		background: none;
		color: var(--accent);
		font: inherit;
		font-weight: 600;
		cursor: pointer;
		padding: 0;
	}

	/* Mobile : une vue à la fois, barre en bas. */
	.app.mobile {
		grid-template-columns: 1fr;
		grid-template-rows: minmax(0, 1fr) auto;
	}
	.mobile .zone-carte,
	.mobile .plein,
	.mobile .fiche {
		grid-area: 1 / 1;
	}
	.mobile .fiche {
		border-left: 0;
		z-index: 6;
	}
	.mobile:not([data-vue='fiche']) .fiche {
		visibility: hidden;
	}
	.plein {
		z-index: 6;
		background: var(--bg);
		padding: 14px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		overflow-y: auto;
	}
	.plein hr {
		width: 100%;
		border: 0;
		border-top: 1px solid var(--line);
	}
	.apercu {
		position: absolute;
		z-index: 4;
		left: 8px;
		right: 8px;
		bottom: 30px;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		padding: 12px 14px;
		border: 0;
		border-radius: 12px;
		background: var(--surface);
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.apercu strong {
		font-size: 17px;
	}
	.apercu span {
		font-size: 13px;
		color: var(--accent);
	}
	.barre-vues {
		grid-area: 2 / 1;
		display: flex;
		gap: 6px;
		padding: 6px 12px calc(6px + env(safe-area-inset-bottom));
		background: var(--surface);
		border-top: 1px solid var(--line);
	}
	.barre-vues button {
		flex: 1;
		min-height: 44px;
		border: 1px solid var(--accent);
		border-radius: 8px;
		background: var(--surface);
		color: var(--accent);
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}
	.barre-vues button[aria-pressed='true'] {
		background: var(--accent);
		color: #fff;
	}
	.barre-vues button:disabled {
		opacity: 0.4;
	}
</style>
