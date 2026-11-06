<script lang="ts">
	/*
	 * Coquille de la carte, commune à `/` et à `/commune/<slug>` : elle garde la carte montée pendant la
	 * navigation. Rail des couches à gauche, volet posé sur la carte (celui d'une couche, ou le fil cantonal, ouvert à
	 * l'arrivée), recherche flottante en haut, et la fiche ouverte en colonne à droite : celle d'une commune, ou une
	 * fiche propre (`/grand-conseil`). Le volet sort en bulle de l'icône du rail qui l'ouvre, et recouvre le volet
	 * précédent (`registre/bulle`).
	 * Les pages du groupe ne portent que le <head>.
	 *
	 * Le volet ouvert et la vue du téléphone sont dans l'adresse (`volet=conseils`, `affichage=fil`), tenus par le
	 * registre : le précédent et le suivant du navigateur les rétablissent.
	 *
	 * Sur téléphone (requête `telephone`), une seule vue plein écran à la fois, choisie dans la barre Carte · Fil ·
	 * Couches · Fiche : la vue Fil rend le fil cantonal, la vue Couches empile les volets de toutes les couches, et ce
	 * qu'on ouvre depuis la carte ou le fil s'affiche d'abord en aperçu, en bas de la carte. L'arrivée sur une fiche
	 * (`/commune/<slug>`, `/grand-conseil`) se fait dans la vue Fiche, sauf si l'adresse en nomme une autre. Le grisage d'une couche n'y suit pas le volet
	 * ouvert : « Voir sur la carte », en tête de son volet, le montre sur la carte (`grisage-mobile`). Toucher la
	 * recherche de la vue Carte ouvre la Recherche plein écran, qui masque tout le reste et se referme sur la carte
	 * telle qu'on l'a laissée.
	 */
	import { tick, untrack } from 'svelte';
	// Essai (#165) : la carte dans le système Almanach, voir lib/almanach/carte.css.
	import '#lib/almanach/almanach.css';
	import '#lib/almanach/carte.css';
	import { fade, fly } from 'svelte/transition';
	import { bulleEntree, bulleSortie } from '#lib/registre/bulle.js';
	import { MediaQuery } from 'svelte/reactivity';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { navigating, page } from '$app/state';
	import Map, { CALQUE_REPERE } from '#lib/socle/Map.svelte';
	import Recherche from '#lib/socle/Recherche.svelte';
	import { COUCHES } from '#lib/registre/couches.js';
	import { resultatsCouches } from '#lib/registre/recherche.js';
	import { ancre } from '#lib/registre/recouvrement.js';
	import { creerRegistre, fournirRegistre, FIL, type VueCarte } from '#lib/registre/registre.svelte.js';
	import Fil from '#lib/fil/Fil.svelte';
	import { creerChargementFil } from '#lib/fil/chargement.svelte.js';
	import { sourcesCarte } from '#lib/registre/attribution.js';
	import Rail from '#lib/registre/Rail.svelte';
	import Volet from '#lib/registre/Volet.svelte';
	import FicheOuverte from '#lib/registre/FicheOuverte.svelte';
	import Apercu from '#lib/registre/Apercu.svelte';
	import Grisage from '#lib/registre/Grisage.svelte';
	import { grisageApres, type GrisageMobile } from '#lib/registre/grisage-mobile.js';
	import { couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import {
		TELEPHONE,
		decalageAuDessus,
		recherchePleine,
		texteApresRecherche,
		type FinRecherche
	} from '#lib/socle/telephone.js';
	import { attributionHtml, source } from '#lib/sources.js';
	import type { Resultat } from '#lib/types.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const registre = creerRegistre(COUCHES, () => data.communes);
	/** Entrées du fil cantonal, lues à sa première ouverture et gardées pendant la visite. */
	const fil = creerChargementFil(COUCHES);
	let carte: ReturnType<typeof Map> | undefined = $state();

	/* ---- Téléphone ---- */

	const telephone = new MediaQuery(TELEPHONE, false);
	/**
	 * Vue plein écran affichée sur téléphone, tenue par le registre : elle est dans l'adresse, et change avec ce qui
	 * s'ouvre (`affichageApres`).
	 */
	const affichage = $derived(registre.affichage);
	/** Mouvement réduit : les entrées de l'aperçu et de la colonne ne glissent pas, elles apparaissent en fondu court. */
	const mouvementReduit = new MediaQuery('(prefers-reduced-motion: reduce)', false);
	const entree = (node: Element, glisse: { x?: number; y?: number }) =>
		mouvementReduit.current ? fade(node, { duration: 120 }) : fly(node, { ...glisse, duration: 200 });

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
		voler: (lon, lat, zoom, parDefaut) => carte?.voler(lon, lat, zoom, decalage(), parDefaut),
		vueCanton: () => carte?.vueCanton(),
		cadrer: (emprise, anime, parDefaut) => carte?.cadrer(emprise, anime, parDefaut)
	};
	registre.brancherAdresse(
		() => (carte ? vueCarte : undefined),
		() => telephone.current
	);
	fournirRegistre(registre);

	// Une couche activée ou désactivée depuis une autre vue (fondu) n'est redessinée qu'au retour sur la carte.
	$effect(() => {
		if (affichage === 'carte') untrack(() => registre.map)?.triggerRepaint();
	});

	/** Le fil n'est monté qu'à son premier passage sur la vue Fil, qui le charge ; il reste monté ensuite. */
	let filVu = $state(false);
	$effect(() => {
		if (affichage === 'fil') filVu = true;
	});

	/** « Voir la fiche › » de l'aperçu : la vue Fiche, le focus sur le nom de la fiche. */
	async function voirFiche() {
		registre.affichage = 'fiche';
		await tick();
		document.getElementById('fiche-titre')?.focus();
	}

	/** Adresse cherchée ou position GPS, marquée sur la carte ; jamais écrite dans l'URL. */
	let repere: [number, number] | null = $state(null);

	const couverture = $derived(couvertureCourante(data.communes));
	/**
	 * Sur téléphone, la couche dont « Voir sur la carte » montre le grisage, jusqu'à la croix de sa pastille, au choix
	 * d'une autre couche ou à sa désactivation ; hors de l'adresse.
	 */
	let grisageMobile = $state<GrisageMobile>(null);
	$effect(() => {
		const actives = registre.actives;
		untrack(() => (grisageMobile = grisageApres(grisageMobile, { actives })));
	});
	/** Couches qui grisent au moins une commune : leur volet a « Voir sur la carte » sur téléphone. */
	const grisantes = $derived(COUCHES.filter((c) => couverture.grisees(c.id).length > 0).map((c) => c.id));
	const nomGrisage = $derived(COUCHES.find((c) => c.id === grisageMobile)?.nom ?? null);

	/** « Voir sur la carte » dans le volet de la couche : la vue Carte, avec son grisage (la couche s'active). */
	function voirCouverture(id: string) {
		if (!registre.active(id)) registre.activer(id, true);
		grisageMobile = grisageApres(grisageMobile, { voir: id });
		registre.affichage = 'carte';
	}

	/** Le grisage suit la couche dont le volet est ouvert sur bureau, et « Voir sur la carte » sur téléphone. */
	const grisees = $derived(couverture.grisees(telephone.current ? grisageMobile : registre.volet));

	// Un même texte (« © swisstopo », pour le fond, les adresses et les lacs) n'est cité qu'une fois.
	const attribution = $derived(
		sourcesCarte(COUCHES, registre.actives)
			.map(source)
			.filter((s, i, toutes) => toutes.findIndex((t) => t.attribution.texte === s.attribution.texte) === i)
			.map(attributionHtml)
	);

	const chercherCouches = (texte: string) => resultatsCouches(COUCHES, texte, data.communes);

	function choix(r: Resultat) {
		registre.oublierAvis();
		// Chercher un lieu déplace la zone du fil ; chercher un élément ou une fiche propre, non : c'est le registre
		// qui vole vers eux.
		if (r.type === 'adresse' || r.type === 'commune') registre.deplacementVoulu();
		if (r.type === 'adresse') {
			repere = [r.lon, r.lat];
			carte?.voler(r.lon, r.lat, r.categorie === 'Position' ? 15 : 16);
		} else if (r.type === 'commune') {
			// La fiche s'ouvre, et la carte cadre la commune.
			repere = null;
			registre.ouvrir({ commune: r.commune.slug });
		} else if (r.type === 'fiche') {
			repere = null;
			registre.ouvrir({ fiche: r.fiche });
		} else registre.ouvrir({ couche: r.couche, element: r.element });
	}

	/* ---- Recherche plein écran (téléphone) ---- */

	/**
	 * Ouverte, elle a poussé une entrée d'historique (même adresse) : le retour arrière du téléphone la retire et
	 * referme la Recherche, sans fermer l'aperçu ni quitter la page. On suit l'événement du navigateur plutôt que
	 * `page.state` : la carte qui finit un déplacement réécrit l'adresse, et SvelteKit abandonne alors la mise à jour.
	 */
	let ouverte = $state(false);
	const pleine = $derived(recherchePleine(telephone.current, affichage, ouverte));
	let texteRecherche = $state('');
	/** Texte du champ de la carte à l'ouverture, rendu par « Annuler » et le retour arrière. */
	let texteAvant = '';
	/** Ce qui referme la Recherche, sauf le retour arrière ; le résultat choisi attend qu'elle soit refermée. */
	let fin: { fin: Exclude<FinRecherche, 'retour'>; resultat?: Resultat } | null = null;

	function ouvrirRecherche() {
		if (ouverte || !recherchePleine(telephone.current, affichage, true)) return;
		// La Recherche s'ouvre vide, sur « Autour de moi » et la ligne d'aide ; « Annuler » rend le texte du champ.
		texteAvant = texteRecherche;
		texteRecherche = '';
		ouverte = true;
		goto(`${location.pathname}${location.search}`, { shallow: true, state: page.state });
	}

	$effect(() => {
		const retour = () => (ouverte = false);
		addEventListener('popstate', retour);
		return () => removeEventListener('popstate', retour);
	});

	/** « Annuler » ou un résultat choisi retirent l'entrée de la Recherche : elle se referme au retour. */
	function quitterRecherche(f: NonNullable<typeof fin>) {
		if (fin) return;
		fin = f;
		history.back();
	}

	let pleineAvant = false;
	$effect(() => {
		const p = pleine;
		untrack(() => {
			if (pleineAvant && !p) refermee();
			pleineAvant = p;
		});
	});

	/**
	 * La Recherche est refermée : rien n'a bougé dessous (aperçu, vue de la carte), le champ reprend son texte, et le
	 * résultat choisi s'ouvre comme depuis la vue Carte.
	 */
	function refermee() {
		const f = fin;
		fin = null;
		// Refermée sans retour (téléphone tourné au-delà de 760 px de large) : son entrée est retirée.
		if (ouverte) {
			ouverte = false;
			history.back();
		}
		texteRecherche = texteApresRecherche(f?.fin ?? 'retour', texteAvant, texteRecherche);
		// SvelteKit lance la navigation du retour quelques instants après lui : on la laisse partir.
		if (f?.resultat) setTimeout(() => (choisi = f.resultat!));
	}

	/**
	 * Résultat choisi dans la Recherche, ouvert une fois traité le retour qui l'a refermée. Quand l'entrée d'en
	 * dessous porte une autre adresse de page, SvelteKit y navigue, et une navigation lancée entre-temps serait annulée.
	 */
	let choisi = $state<Resultat | null>(null);
	$effect(() => {
		if (!choisi || navigating.to) return;
		const r = choisi;
		choisi = null;
		untrack(() => choix(r));
	});

	const choixRecherche = (r: Resultat) => (pleine ? quitterRecherche({ fin: 'choix', resultat: r }) : choix(r));

	/** Lien d'évitement : le clavier n'a pas à traverser le rail et la recherche pour atteindre la carte. */
	async function allerCarte(e: MouseEvent) {
		e.preventDefault();
		// Sur bureau, la carte est déjà là : la vue du téléphone n'entre pas dans l'adresse.
		if (telephone.current) registre.affichage = 'carte';
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

<div
	class="app"
	data-theme="almanach"
	class:avec-fiche={registre.commune ?? registre.propre}
	class:recherche-pleine={pleine}
	data-affichage={affichage}
>
	<!-- Le rail, dans son propre repère de page : sans boîte à lui (display: contents), la grille de .app reste la même. -->
	<aside class="cote-rail" aria-label="Couches de la carte">
		<Rail {registre} />
	</aside>

	<!-- Le contenu de la page, où mène « Aller au contenu » de l'en-tête : la carte, ses volets et la fiche ouverte. Le
		rail et la barre des vues, des commandes d'affichage, restent autour. « Aller à la carte », premier arrêt du
		contenu, passe la recherche et les volets pour mener au canevas. -->
	<main class="contenu" id="contenu" tabindex="-1">
		<h1 class="lecteur-seul">Vigie Vaud — carte du canton de Vaud</h1>
		<a class="evitement" href="#carte" onclick={allerCarte}>Aller à la carte</a>
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
				<Recherche
					communes={data.communes}
					{chercherCouches}
					bind:texte={texteRecherche}
					plein={pleine}
					onchoix={choixRecherche}
					onouvrir={ouvrirRecherche}
					onannuler={() => quitterRecherche({ fin: 'annuler' })}
				/>
				<!-- Élément introuvable (« Aucun dossier n° … »), près de la recherche qui permet d'en chercher un autre. -->
				<p class="avis" role="status">
					{#if registre.avis}
						{registre.avis}
						<button type="button" aria-label="Masquer ce message" onclick={registre.oublierAvis}>×</button>
					{/if}
				</p>
				<!-- Téléphone : le grisage montré par « Voir sur la carte », jusqu'à la croix. -->
				{#if telephone.current && nomGrisage}
					<p class="pastille-couverture">
						Couverture&nbsp;: {nomGrisage}
						<button
							type="button"
							aria-label="Ne plus griser les communes que {nomGrisage} ne couvre pas"
							onclick={() => (grisageMobile = grisageApres(grisageMobile, { effacer: true }))}
						>
							×
						</button>
					</p>
				{/if}
			</div>

			<!-- Un bloc par couche : le volet qui se ferme garde sa couche pendant qu'il disparaît. -->
			{#each COUCHES as c (c.id)}
				{#if registre.volet === c.id && !telephone.current}
					<!-- svelte-ignore a11y_no_static_element_interactions -->
					<div
						class="volet"
						in:bulleEntree={{ id: c.id }}
						out:bulleSortie={{ id: c.id, ouvert: () => registre.volet }}
						onkeydown={(e) => e.key === 'Escape' && fermerVolet()}
					>
						<Volet couche={c} {registre} onfermer={fermerVolet} />
					</div>
				{/if}
			{/each}

			<!-- Le fil cantonal, à la place des volets : ouvert à l'arrivée, sa colonne de fiche reste ouvrable à droite. -->
			{#if registre.volet === FIL && !telephone.current}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="volet"
					in:bulleEntree={{ id: FIL }}
					out:bulleSortie={{ id: FIL, ouvert: () => registre.volet }}
					onkeydown={(e) => e.key === 'Escape' && fermerVolet()}
				>
					<Fil {registre} chargement={fil} communes={data.communes} onfermer={fermerVolet} />
				</div>
			{/if}

			<p class="liens">
				<a href={resolve('/a-propos')}>À propos</a> ·
				<a href={resolve('/protection-des-donnees')}>Protection des données</a>
			</p>

			<!-- Téléphone : ce qui est ouvert s'affiche d'abord en aperçu, en bas de la carte. -->
			{#if telephone.current && (registre.commune ?? registre.propre)}
				<div class="apercu" bind:this={apercu} in:entree={{ y: 30 }}>
					<Apercu {registre} nom={registre.commune?.nom ?? registre.propre!.fiche.nom} onvoir={voirFiche} />
				</div>
			{/if}
		</div>

		<!-- Téléphone : la vue Fil, montée à son premier passage ; toucher une entrée ramène à la carte, pour l'aperçu. -->
		{#if telephone.current && filVu}
			<div class="vue-fil">
				<Fil {registre} chargement={fil} communes={data.communes} />
			</div>
		{/if}

		<!-- Téléphone : la vue Couches empile les volets de toutes les couches, dans l'ordre du registre. -->
		{#if telephone.current && affichage === 'couches'}
			<div class="couches">
				{#each COUCHES as c (c.id)}
					<Volet
						couche={c}
						{registre}
						onvoir={grisantes.includes(c.id) ? () => voirCouverture(c.id) : undefined}
					/>
				{/each}
			</div>
		{/if}

		{#if registre.commune ?? registre.propre}
			{@const ouverte = registre.commune ?? registre.propre!}
			<!-- Une seule colonne, pour une commune ou une fiche propre : changer de fiche remplace son contenu sans la refermer. -->
			<div class="colonne" in:entree={{ x: 40 }}>
				<FicheOuverte {registre} {ouverte} />
			</div>
		{/if}
	</main>

	<!-- Masquée sur bureau par la feuille de style : sur téléphone, elle est là dès le premier rendu. -->
	<nav class="barre-vues" aria-label="Affichage">
		<button type="button" aria-pressed={affichage === 'carte'} onclick={() => (registre.affichage = 'carte')}>
			Carte
		</button>
		<button type="button" aria-pressed={affichage === 'fil'} onclick={() => (registre.affichage = 'fil')}>Fil</button>
		<button type="button" aria-pressed={affichage === 'couches'} onclick={() => (registre.affichage = 'couches')}>
			Couches
		</button>
		<!-- « Fiche » reste inactif tant que rien n'est ouvert. -->
		<button
			type="button"
			aria-pressed={affichage === 'fiche'}
			disabled={!registre.fiche}
			onclick={() => (registre.affichage = 'fiche')}
		>
			Fiche
		</button>
	</nav>
</div>

{@render children()}

<style>
	.app {
		display: grid;
		grid-template-columns: calc(72px + env(safe-area-inset-left, 0px)) minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr);
		height: calc(100dvh - var(--header-h));
		position: relative;
	}
	/* Le contenu, à droite du rail : la carte, puis la fiche ouverte, qui prend une colonne à droite et la rétrécit. */
	.contenu {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr);
		min-width: 0;
		min-height: 0;
	}
	.app.avec-fiche .contenu {
		grid-template-columns: minmax(0, 1fr) min(420px, 40vw);
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
		/* Un filtre neutre donne à la recherche son propre calque. Sans lui, Chromium en rendu logiciel (sans
		   accélération graphique) laissait un trou de sa taille dans la carte, retourné en bas à gauche : le fond
		   de la page y paraissait en blanc, alors que la carte elle-même y était bien dessinée. */
		filter: opacity(1);
	}
	/* Pendant la saisie, les résultats passent devant l'aperçu (téléphone). */
	.recherche:focus-within {
		z-index: 5;
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
		flex: none;
		width: 32px;
		height: 32px;
		margin: -6px 0 -6px auto;
		border: 0;
		background: none;
		font-size: 18px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
	.avis button:hover {
		background: var(--color-paper-2, var(--bg));
		color: var(--text);
	}
	@media (pointer: coarse) {
		.avis button {
			width: 44px;
			height: 44px;
			margin-block: -10px;
		}
	}
	/*
	 * Le volet pend sous la recherche, à sa largeur : son filet de tête passe sous celui du champ (46 px de haut, filet
	 * de 2 px compris). Ni écart ni débord où la carte devrait se voir : un vieux navigateur Windows y laissait le fond
	 * de la page, en gris, au-dessus du fil.
	 */
	.volet {
		position: absolute;
		z-index: 3;
		top: 54px;
		left: 10px;
		bottom: 34px;
		width: min(360px, calc(100% - 70px));
		overflow-y: auto;
		border-radius: 10px;
		/* Le volet est à la hauteur de son contenu, sans dépasser le bas de la carte. */
		height: fit-content;
		max-height: calc(100% - 88px);
		/* Le volet descend au moins jusqu'à la dernière icône du rail (Hôtels de ville), pour que sa bulle sorte de
		   son icône et non d'en dessous ; le contenu, un volet blanc, remplit cette hauteur. */
		min-height: min(300px, calc(100% - 88px));
		display: flex;
		flex-direction: column;
	}
	.volet > :global(*) {
		flex: 1 0 auto;
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
	.liens a:hover {
		color: var(--text);
		text-decoration-thickness: 2px;
	}
	.apercu {
		position: absolute;
		z-index: 4;
		left: 8px;
		right: 8px;
		/* Laisse visibles les liens et le bouton des sources (attribution), en bas de la carte. */
		bottom: 34px;
	}
	.barre-vues,
	.vue-fil {
		display: none;
	}
	.pastille-couverture {
		display: flex;
		align-items: center;
		gap: 8px;
		width: fit-content;
		margin: 6px 0 0;
		padding: 4px 4px 4px 12px;
		border-radius: 999px;
		background: var(--surface);
		box-shadow: 0 2px 8px rgb(0 0 0 / 0.18);
		font-size: 14px;
		font-weight: 600;
	}
	.pastille-couverture button {
		width: 36px;
		height: 36px;
		border: 0;
		border-radius: 50%;
		background: none;
		font-size: 20px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}

	/*
	 * Téléphone (requête TELEPHONE de lib/socle/telephone.ts, la largeur seule) : une vue plein écran à la fois, et la
	 * barre en bas. Au-delà de 760 px (téléphone à l'horizontale, tablette), la mise en page reste celle du bureau.
	 */
	@media (max-width: 760px) {
		.app,
		.app.avec-fiche,
		.app.avec-fiche .contenu {
			grid-template-columns: minmax(0, 1fr);
		}
		.app {
			grid-template-rows: minmax(0, 1fr) auto;
		}
		.contenu {
			grid-area: 1 / 1;
		}
		.app > .cote-rail > :global(.rail) {
			display: none;
		}
		/* Les volets du bureau, rendus à la pré-génération, ne s'affichent pas avant que la requête ne les retire. */
		.zone-carte .volet {
			display: none;
		}
		.zone-carte,
		.colonne,
		.couches,
		.vue-fil {
			grid-area: 1 / 1;
		}
		.colonne,
		.couches,
		.vue-fil {
			z-index: 6;
		}
		.vue-fil {
			display: block;
			overflow-y: auto;
			/* Arrivé en bas du fil, le défilement ne passe pas à la page. */
			overscroll-behavior: contain;
			background: var(--bg);
		}
		.vue-fil :global(.fil) {
			border-radius: 0;
			box-shadow: none;
			min-height: 100%;
			box-sizing: border-box;
		}
		.colonne :global(.fiche) {
			border-left: 0;
		}
		/* visibility plutôt que display : la carte garde sa taille, et ce qui est caché sort de l'ordre de tabulation. */
		.app:not([data-affichage='carte']) .zone-carte,
		.app:not([data-affichage='fiche']) .colonne,
		.app:not([data-affichage='fil']) .vue-fil {
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
			overscroll-behavior: contain;
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
		/*
		 * Recherche plein écran : le champ à la place de l'en-tête, et les résultats sur tout l'écran. L'en-tête, la
		 * carte, l'aperçu, les liens, les sources et la barre des vues sont masqués, et sortent de l'ordre de tabulation.
		 */
		.recherche-pleine .recherche {
			position: fixed;
			inset: 0;
			z-index: 20;
			width: auto;
			border-radius: 0;
			box-shadow: none;
			visibility: visible;
		}
		.recherche-pleine .zone-carte,
		.recherche-pleine .barre-vues,
		.recherche-pleine .evitement,
		:global(header:has(~ .app.recherche-pleine)) {
			visibility: hidden;
		}
		.recherche-pleine .zone-carte :global(.maplibregl-control-container),
		.recherche-pleine .avis,
		.recherche-pleine .pastille-couverture {
			display: none;
		}
	}
	.cote-rail {
		display: contents;
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
	.evitement:hover {
		background: var(--surface-2, var(--bg));
		text-decoration-thickness: 2px;
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
