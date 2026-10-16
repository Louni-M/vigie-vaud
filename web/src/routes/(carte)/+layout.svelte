<script lang="ts">
	/*
	 * Coquille de la carte, commune à `/` et à `/commune/<slug>` : elle garde la carte montée pendant la
	 * navigation. Rail des couches à gauche, volet posé sur la carte, recherche flottante en haut, et la fiche
	 * commune en colonne à droite quand une commune est ouverte. Les pages du groupe ne portent que le <head>.
	 *
	 * Sur téléphone (requête `telephone`), une seule vue plein écran à la fois, choisie dans la barre Carte ·
	 * Couches · Fiche : la vue Couches empile les volets de toutes les couches, et ce qu'on ouvre depuis la carte
	 * s'affiche d'abord en aperçu, en bas de la carte. Aucun grisage sur téléphone en J0.
	 */
	import { tick, untrack } from 'svelte';
	import { fly } from 'svelte/transition';
	import { MediaQuery } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import Map, { CALQUE_REPERE } from '#lib/socle/Map.svelte';
	import Recherche from '#lib/socle/Recherche.svelte';
	import { COUCHES } from '#lib/registre/couches.js';
	import { resultatsCouches } from '#lib/registre/recherche.js';
	import { ancre } from '#lib/registre/recouvrement.js';
	import { creerRegistre, fournirRegistre, type VueCarte } from '#lib/registre/registre.svelte.js';
	import { sourcesCarte } from '#lib/registre/attribution.js';
	import Rail from '#lib/registre/Rail.svelte';
	import Volet from '#lib/registre/Volet.svelte';
	import FicheCommune from '#lib/registre/FicheCommune.svelte';
	import Apercu from '#lib/registre/Apercu.svelte';
	import Grisage from '#lib/registre/Grisage.svelte';
	import { couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import {
		TELEPHONE,
		affichageApres,
		decalageAuDessus,
		type Affichage,
		type Ouverture
	} from '#lib/socle/telephone.js';
	import { attributionHtml, source } from '#lib/sources.js';
	import type { Resultat } from '#lib/types.js';
	import type { LayoutProps } from './$types';
	// PROTOTYPE (ticket #45) : trois variantes du fil cantonal.
	import Variantes, { filChoisi } from '#lib/fil-prototype/Variantes.svelte';
	import FilA from '#lib/fil-prototype/FilA.svelte';
	import FilB from '#lib/fil-prototype/FilB.svelte';
	import FilC from '#lib/fil-prototype/FilC.svelte';
	// PROTOTYPE (ticket #51) : trois variantes de la couche Conseils ; le fil est fixé sur sa variante A.
	import VariantesConseils from '#lib/couches/conseils-prototype/Variantes.svelte';
	import FicheGrandConseil from '#lib/couches/conseils-prototype/FicheGrandConseil.svelte';
	import { proto, fermerGrandConseil } from '#lib/couches/conseils-prototype/proto.svelte.js';
	Object.assign(filChoisi, { variante: 'A' });

	let { data, children }: LayoutProps = $props();

	const registre = creerRegistre(COUCHES, () => data.communes);
	let carte: ReturnType<typeof Map> | undefined = $state();

	/* ---- Téléphone ---- */

	const telephone = new MediaQuery(TELEPHONE, false);
	/** Vue plein écran affichée sur téléphone ; n'entre pas dans l'adresse. */
	let affichage = $state<Affichage>('carte');
	const ouverture = $derived<Ouverture>({
		commune: registre.commune?.slug ?? null,
		element: registre.ouvert ? `${registre.ouvert.couche}:${registre.ouvert.element}` : null
	});
	let ouvertureAvant: Ouverture = { commune: null, element: null };
	$effect(() => {
		const apres = ouverture;
		untrack(() => {
			affichage = affichageApres(affichage, ouvertureAvant, apres);
			ouvertureAvant = apres;
		});
	});

	let zoneCarte: HTMLElement | undefined = $state();
	let recherche: HTMLElement | undefined = $state();
	let apercu: HTMLElement | undefined = $state();
	/** Place prise en bas de la carte par l'aperçu d'un dossier, tant qu'il n'est pas affiché. */
	const APERCU_DOSSIER = 170;

	/**
	 * Sur téléphone, la carte qui vole vers un élément le place au-dessus de son aperçu, au milieu de la bande
	 * libre entre la recherche et l'aperçu.
	 */
	function decalage() {
		if (!telephone.current || !zoneCarte) return 0;
		const haut = recherche ? recherche.offsetTop + recherche.offsetHeight : 0;
		const bas = apercu && registre.ouvert ? zoneCarte.clientHeight - apercu.offsetTop : APERCU_DOSSIER;
		return decalageAuDessus(haut, bas);
	}

	const vueCarte: VueCarte = {
		aller: (c, anime) => carte?.aller(c, anime),
		voler: (lon, lat, zoom) => carte?.voler(lon, lat, zoom, decalage()),
		vueCanton: () => carte?.vueCanton(),
		cadrer: (emprise, anime, parDefaut) => carte?.cadrer(emprise, anime, parDefaut)
	};
	registre.brancherAdresse(() => (carte ? vueCarte : undefined));
	fournirRegistre(registre);

	/** « Voir la fiche › » de l'aperçu : la vue Fiche, le focus sur le nom de la commune. */
	async function voirFiche() {
		affichage = 'fiche';
		await tick();
		document.getElementById('fiche-titre')?.focus();
	}

	/** Adresse cherchée ou position GPS, marquée sur la carte ; jamais écrite dans l'URL. */
	let repere: [number, number] | null = $state(null);

	/** Le grisage suit la couche dont le volet est ouvert, avec la mise en page du bureau seulement. */
	const grisees = $derived(
		telephone.current
			? proto.grisageMobile && registre.active('conseils')
				? couvertureCourante(data.communes).grisees('conseils')
				: []
			: couvertureCourante(data.communes).grisees(registre.volet)
	);

	// Un même texte (« © swisstopo », pour le fond, les adresses et les lacs) n'est cité qu'une fois.
	const attribution = $derived(
		sourcesCarte(COUCHES, registre.actives)
			.map(source)
			.filter((s, i, toutes) => toutes.findIndex((t) => t.attribution.texte === s.attribution.texte) === i)
			.map(attributionHtml)
	);

	const chercherCouches = (texte: string) => resultatsCouches(COUCHES, texte);

	function choix(r: Resultat) {
		registre.oublierAvis();
		if (r.type === 'adresse') {
			repere = [r.lon, r.lat];
			carte?.voler(r.lon, r.lat, r.categorie === 'Position' ? 15 : 16);
		} else if (r.type === 'commune') {
			// La fiche s'ouvre, et la carte cadre la commune.
			repere = null;
			registre.ouvrir({ commune: r.commune.slug });
		} else registre.ouvrir({ couche: r.couche, element: r.element });
	}

	/** Lien d'évitement : le clavier n'a pas à traverser le rail et la recherche pour atteindre la carte. */
	async function allerCarte(e: MouseEvent) {
		e.preventDefault();
		affichage = 'carte';
		await tick();
		document.querySelector<HTMLElement>('#carte .maplibregl-canvas')?.focus();
	}

	/* ---- PROTOTYPE (ticket #45) ---- */
	const variante = $derived(filChoisi.variante);
	// Variante A : le fil est ouvert à l'arrivée, à la place d'un volet.
	$effect(() => {
		if (variante === 'A') untrack(() => (registre.volet ??= 'fil'));
		else if (untrack(() => registre.volet) === 'fil') registre.volet = null;
	});
	const colonneB = $derived(variante === 'B' && !telephone.current);

	/* ---- PROTOTYPE (ticket #51) ---- */
	const gcOuvert = $derived(proto.variante === 'A' && proto.gc);
	// La fiche du Grand Conseil et la fiche commune se partagent la colonne : ouvrir l'une ferme l'autre.
	let avantGc = false;
	let avantCommune: string | null = null;
	$effect(() => {
		const gc = gcOuvert;
		const commune = registre.commune?.slug ?? null;
		untrack(() => {
			if (gc && !avantGc && commune) registre.fermerCommune();
			else if (commune && commune !== avantCommune && gc) fermerGrandConseil();
			if (gc && !avantGc && telephone.current) affichage = 'carte';
			avantGc = gc;
			avantCommune = commune;
		});
	});
	// Une vue demandée par la couche (marqueur du Grand Conseil, « Voir sur la carte ») : sur téléphone, la vue
	// plein écran ; sur bureau, le volet correspondant.
	$effect(() => {
		const v = proto.vue;
		if (!v) return;
		untrack(() => {
			proto.vue = null;
			if (telephone.current) affichage = v as Affichage;
			else if (v === 'fil') registre.volet = 'fil';
			else if (v === 'couches') registre.volet = 'conseils';
		});
	});
	async function voirGrandConseil() {
		affichage = 'fiche';
		await tick();
		document.getElementById('gc-titre')?.focus();
	}

	function fermerVolet() {
		const id = registre.volet;
		registre.volet = null;
		// Le focus revient à l'icône du rail qui avait ouvert le volet.
		tick().then(() => document.querySelector<HTMLElement>(`[data-couche="${id}"]`)?.focus());
	}
</script>

<VariantesConseils />

<div class="app" class:avec-fiche={registre.commune || colonneB || gcOuvert} data-affichage={affichage}>
	<a class="evitement" href="#carte" onclick={allerCarte}>Aller à la carte</a>

	<Rail {registre}>
		{#snippet avant()}
			{#if variante === 'A'}
				<button
					type="button"
					class="rail-fil"
					class:ouvert={registre.volet === 'fil'}
					aria-expanded={registre.volet === 'fil'}
					onclick={() => (registre.volet = registre.volet === 'fil' ? null : 'fil')}
				>
					<span class="icone-fil" aria-hidden="true">≡</span>Fil
				</button>
			{/if}
		{/snippet}
	</Rail>

	<div class="zone-carte" id="carte" bind:this={zoneCarte}>
		<Map
			bind:this={carte}
			{repere}
			{attribution}
			onpret={(m) => registre.carte(m, CALQUE_REPERE)}
			onvue={registre.deplacement}
		/>

		<!-- Calques de chaque couche, dans l'ordre du registre ; importés à la première activation. -->
		{#if registre.map}
			<!-- Sous toutes les couches : le gris voile le fond, pas les éléments. -->
			<Grisage map={registre.map} sous={ancre(COUCHES[0].id)} {grisees} />
			{#each COUCHES as c (c.id)}
				{#if registre.montee(c.id)}
					{#await registre.composant(c, 'Carte') then module}
						{#if module}<module.default ctx={registre.contexte(c)} />{/if}
					{/await}
				{/if}
			{/each}
		{/if}

		<div class="recherche" bind:this={recherche}>
			<Recherche communes={data.communes} {chercherCouches} onchoix={choix} />
			<!-- Élément introuvable (« Aucun dossier n° … »), près de la recherche qui permet d'en chercher un autre. -->
			<p class="avis" role="status">
				{#if registre.avis}
					{registre.avis}
					<button type="button" aria-label="Masquer ce message" onclick={registre.oublierAvis}>×</button>
				{/if}
			</p>
		</div>

		<!-- Un bloc par couche : le volet qui se ferme garde sa couche pendant qu'il disparaît. -->
		{#each COUCHES as c (c.id)}
			{#if registre.volet === c.id && !telephone.current}
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

		{#if variante === 'A' && registre.volet === 'fil' && !telephone.current}
			<div class="volet volet-fil" transition:fly={{ x: -20, duration: 160 }}>
				<FilA {registre} communes={data.communes} onfermer={() => (registre.volet = null)} />
			</div>
		{/if}
		{#if variante === 'B' && telephone.current && !registre.commune}
			<FilB {registre} communes={data.communes} tiroir />
		{/if}
		{#if variante === 'C' && !(telephone.current && registre.commune)}
			<FilC {registre} communes={data.communes} telephone={telephone.current} />
		{/if}

		<p class="liens">
			<a href={resolve('/a-propos')}>À propos</a> ·
			<a href={resolve('/protection-des-donnees')}>Protection des données</a>
		</p>

		<!-- PROTOTYPE (ticket #51) : grisage de la Couverture des Conseils sur téléphone (#44). -->
		{#if telephone.current && proto.grisageMobile && registre.active('conseils')}
			<p class="pastille-couverture">
				Couverture : Conseils
				<button type="button" aria-label="Retirer le grisage" onclick={() => (proto.grisageMobile = false)}>×</button>
			</p>
		{/if}
		{#if telephone.current && gcOuvert && !registre.commune}
			<div class="apercu" in:fly={{ y: 30, duration: 200 }}>
				<div class="apercu-gc">
					<button type="button" onclick={voirGrandConseil}><strong>Grand Conseil</strong> · <span>Voir la fiche ›</span></button>
					<button type="button" class="x" aria-label="Fermer" onclick={fermerGrandConseil}>×</button>
				</div>
			</div>
		{/if}

		<!-- Téléphone : ce qui est ouvert s'affiche d'abord en aperçu, en bas de la carte. -->
		{#if telephone.current && registre.commune}
			<div class="apercu" bind:this={apercu} in:fly={{ y: 30, duration: 200 }}>
				<Apercu {registre} commune={registre.commune} onvoir={voirFiche} />
			</div>
		{/if}
	</div>

	<!-- Téléphone : la vue Couches empile les volets de toutes les couches, dans l'ordre du registre. -->
	{#if telephone.current && affichage === 'couches'}
		<div class="couches">
			{#each COUCHES as c (c.id)}
				<Volet couche={c} {registre} />
			{/each}
		</div>
	{/if}

	{#if telephone.current && variante === 'A' && affichage === ('fil' as Affichage)}
		<div class="couches">
			<FilA {registre} communes={data.communes} onouvert={() => (affichage = 'carte')} />
		</div>
	{/if}

	{#if colonneB}
		<div class="colonne"><FilB {registre} communes={data.communes} /></div>
	{:else if gcOuvert}
		<div class="colonne" in:fly={{ x: 40, duration: 200 }}>
			<FicheGrandConseil communes={data.communes} telephone={telephone.current} onfermer={() => (affichage = 'carte')} />
		</div>
	{:else if registre.commune}
		<!-- Une seule colonne : changer de commune remplace son contenu sans la refermer. -->
		<div class="colonne" in:fly={{ x: 40, duration: 200 }}>
			<FicheCommune {registre} commune={registre.commune} />
		</div>
	{/if}

	<!-- Masquée sur bureau par la feuille de style : sur téléphone, elle est là dès le premier rendu. -->
	<nav class="barre-vues" aria-label="Affichage">
		<button type="button" aria-pressed={affichage === 'carte'} onclick={() => (affichage = 'carte')}>Carte</button>
		{#if variante === 'A'}
			<button type="button" aria-pressed={affichage === ('fil' as Affichage)} onclick={() => (affichage = 'fil' as Affichage)}>Fil</button>
		{/if}
		<button type="button" aria-pressed={affichage === 'couches'} onclick={() => (affichage = 'couches')}>
			Couches
		</button>
		<!-- « Fiche » reste inactif tant que rien n'est ouvert. -->
		<button
			type="button"
			aria-pressed={affichage === 'fiche'}
			disabled={!registre.commune && !gcOuvert}
			onclick={() => (affichage = 'fiche')}
		>
			Fiche
		</button>
	</nav>
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
	/* La fiche ouverte prend une colonne à droite : la carte se rétrécit. */
	.app.avec-fiche {
		grid-template-columns: 72px minmax(0, 1fr) min(420px, 40vw);
	}
	.zone-carte {
		position: relative;
		overflow: hidden;
	}
	.colonne {
		min-width: 0;
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
	.avis:empty {
		display: none;
	}
	.avis {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 6px 0 0;
		padding: 8px 6px 8px 12px;
		border-radius: 10px;
		background: var(--surface);
		font-size: 14px;
		color: var(--erreur);
	}
	.avis button {
		margin-left: auto;
		border: 0;
		background: none;
		font-size: 18px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
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
	/* PROTOTYPE (ticket #45) */
	.volet-fil {
		width: min(380px, calc(100% - 20px));
	}
	.rail-fil {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 8px 2px 10px;
		margin-bottom: 6px;
		border: 0;
		border-bottom: 1px solid var(--line);
		border-radius: 8px 8px 0 0;
		background: none;
		font: inherit;
		font-size: 11px;
		font-weight: 600;
		cursor: pointer;
	}
	.rail-fil.ouvert {
		background: var(--bg);
	}
	.icone-fil {
		width: 30px;
		height: 30px;
		border-radius: 8px;
		display: grid;
		place-items: center;
		background: #111;
		color: #fff;
		font-size: 18px;
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
	.apercu {
		position: absolute;
		z-index: 4;
		left: 8px;
		right: 8px;
		/* Laisse visibles les liens et le bouton des sources (attribution), en bas de la carte. */
		bottom: 34px;
	}
	.barre-vues {
		display: none;
	}
	/* PROTOTYPE (ticket #51) */
	.pastille-couverture {
		position: absolute;
		z-index: 4;
		top: 64px;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 4px;
		margin: 0;
		padding: 4px 4px 4px 12px;
		border-radius: 999px;
		background: #0b7285;
		color: #fff;
		font-size: 14px;
		font-weight: 600;
		box-shadow: 0 2px 8px rgb(0 0 0 / 0.25);
	}
	.pastille-couverture button {
		width: 30px;
		height: 30px;
		border: 0;
		border-radius: 50%;
		background: rgb(255 255 255 / 0.2);
		color: #fff;
		font-size: 18px;
		cursor: pointer;
	}
	.apercu-gc {
		display: flex;
		border-radius: 10px;
		background: var(--surface);
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
	}
	.apercu-gc button {
		min-height: 52px;
		padding: 12px 14px;
		border: 0;
		background: none;
		font: inherit;
		font-size: 15px;
		text-align: left;
		color: var(--muted);
		cursor: pointer;
	}
	.apercu-gc button:first-child {
		flex: 1;
	}
	.apercu-gc strong {
		font-size: 17px;
		color: #0b7285;
	}
	.apercu-gc span {
		color: var(--accent);
		font-weight: 600;
	}
	.apercu-gc .x {
		font-size: 24px;
	}

	/*
	 * Téléphone en portrait (requête TELEPHONE de lib/socle/telephone.ts) : une vue plein écran à la fois, et la
	 * barre en bas. À l'horizontale et sur tablette, la mise en page reste celle du bureau.
	 */
	@media (max-width: 760px) and (min-height: 521px) {
		.app,
		.app.avec-fiche {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: minmax(0, 1fr) auto;
		}
		.app > :global(.rail) {
			display: none;
		}
		.zone-carte,
		.colonne,
		.couches {
			grid-area: 1 / 1;
		}
		.colonne,
		.couches {
			z-index: 6;
		}
		.colonne :global(.fiche) {
			border-left: 0;
		}
		/* visibility plutôt que display : la carte garde sa taille, et ce qui est caché sort de l'ordre de tabulation. */
		.app:not([data-affichage='carte']) .zone-carte,
		.app:not([data-affichage='fiche']) .colonne {
			visibility: hidden;
		}
		/* MapLibre force « visibility: visible » sur l'attribution dépliée. */
		.app:not([data-affichage='carte']) .zone-carte :global(.maplibregl-control-container) {
			display: none;
		}
		.couches {
			display: flex;
			flex-direction: column;
			gap: 12px;
			padding: 12px;
			overflow-y: auto;
			background: var(--bg);
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
			font-size: 15px;
			font-weight: 600;
			cursor: pointer;
		}
		.barre-vues button[aria-pressed='true'] {
			background: var(--accent);
			color: #fff;
		}
		.barre-vues button:disabled {
			opacity: 0.4;
			cursor: default;
		}
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
