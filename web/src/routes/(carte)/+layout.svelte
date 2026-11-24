<script lang="ts">
	/*
	 * Coquille de la carte, commune à `/` et à `/commune/<slug>` : elle garde la carte montée pendant la
	 * navigation. Le panneau posé sur la carte montre le sommaire à l'arrivée, ou la rubrique qu'on y a ouverte ; la
	 * recherche flotte au-dessus, et la fiche ouverte prend une colonne à droite : celle d'une commune, ou une fiche
	 * propre (`/grand-conseil`). La carte dessine la rubrique ouverte, ou l'onglet de la fiche commune ouverte, en plus
	 * des hôtels de ville et du marqueur du Grand Conseil (`registre/dessin`) ; le grisage suit la même couche.
	 * Les pages du groupe ne portent que le <head>.
	 *
	 * La rubrique ouverte et la vue du téléphone sont dans l'adresse (`volet=routes`, `affichage=carte`), tenues par le
	 * registre : le précédent et le suivant du navigateur les rétablissent.
	 *
	 * Sur téléphone (requête `telephone`), une seule vue plein écran à la fois, choisie dans la barre du bas : le
	 * panneau, la carte ou la fiche ; ce qu'on ouvre depuis la carte ou une liste s'affiche d'abord en aperçu, en bas de
	 * la carte. L'arrivée sur une fiche (`/commune/<slug>`, `/grand-conseil`) se fait dans la vue Fiche, sauf si
	 * l'adresse en nomme une autre. Toucher la recherche de la vue Carte ouvre la Recherche plein écran, qui masque tout
	 * le reste et se referme sur la carte telle qu'on l'a laissée.
	 */
	import { tick, untrack } from 'svelte';
	import '#lib/almanach/almanach.css';
	import { fade, fly } from 'svelte/transition';
	import { MediaQuery } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import { navigating } from '$app/state';
	import Map, { CALQUE_REPERE } from '#lib/socle/Map.svelte';
	import Recherche from '#lib/socle/Recherche.svelte';
	import { COUCHES } from '#lib/registre/couches.js';
	import { resultatsCouches } from '#lib/registre/recherche.js';
	import { ancre } from '#lib/registre/recouvrement.js';
	import { creerRegistre, fournirRegistre, SOMMAIRE, type VueCarte } from '#lib/registre/registre.svelte.js';
	import { navigateurSvelteKit } from '#lib/registre/navigateur.js';
	import { sourcesCarte } from '#lib/registre/attribution.js';
	import { clicSimple } from '#lib/registre/liens.js';
	import { rubriquesDuSommaire } from '#lib/registre/rubriques.js';
	import Sommaire from '#lib/registre/Sommaire.svelte';
	import Volet from '#lib/registre/Volet.svelte';
	import FicheOuverte from '#lib/registre/FicheOuverte.svelte';
	import Apercu from '#lib/registre/Apercu.svelte';
	import Grisage from '#lib/registre/Grisage.svelte';
	import { couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import {
		TELEPHONE,
		decalageAuDessus,
		recherchePleine,
		texteApresRecherche,
		type FinRecherche
	} from '#lib/socle/telephone.js';
	import { suivreSaisie } from '#lib/socle/saisie.js';
	import { attributionHtml, source } from '#lib/sources.js';
	import type { Resultat } from '#lib/types.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const registre = creerRegistre(COUCHES, () => data.communes, navigateurSvelteKit());
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
	let composantRecherche: ReturnType<typeof Recherche> | undefined = $state();
	let apercu: HTMLElement | undefined = $state();
	let colonne: HTMLElement | undefined = $state();
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

	// Une couche dessinée ou remplacée depuis une autre vue (fondu) n'est redessinée qu'au retour sur la carte.
	$effect(() => {
		if (affichage === 'carte') untrack(() => registre.map)?.triggerRepaint();
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
	/** Le grisage suit la couche dessinée : la rubrique ouverte, ou l'onglet de la fiche commune ouverte. */
	const grisees = $derived(couverture.grisees(registre.dessinee));

	// Un même texte (« © swisstopo », pour le fond, les adresses et les lacs) n'est cité qu'une fois.
	const attribution = $derived(
		sourcesCarte(COUCHES, registre.dessinee)
			.map(source)
			.filter((s, i, toutes) => toutes.findIndex((t) => t.attribution.texte === s.attribution.texte) === i)
			.map(attributionHtml)
	);

	const chercherCouches = (texte: string) => resultatsCouches(COUCHES, texte, data.communes);

	function choix(r: Resultat) {
		registre.oublierAvis();
		// Chercher un lieu déplace la zone du fil ; chercher un élément ou une fiche propre, non : c'est le registre
		// qui vole vers eux. Un élément cherché s'ouvre dans sa rubrique.
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
		} else registre.ouvrir({ couche: r.couche, element: r.element }, { rubrique: true });
	}

	/* ---- Recherche plein écran (téléphone) ---- */

	/**
	 * Ouverte, elle a son entrée d'historique, tenue par le registre (`registre.recherche`) : le retour arrière du
	 * téléphone la retire et referme la Recherche, sans fermer l'aperçu ni quitter la page.
	 */
	const pleine = $derived(recherchePleine(telephone.current, affichage, registre.recherche));
	let texteRecherche = $state('');
	/** Texte du champ de la carte à l'ouverture, rendu par « Annuler » et le retour arrière. */
	let texteAvant = '';
	/** Ce qui referme la Recherche, sauf le retour arrière ; le résultat choisi attend qu'elle soit refermée. */
	let fin: { fin: Exclude<FinRecherche, 'retour'>; resultat?: Resultat } | null = null;

	function ouvrirRecherche() {
		if (registre.recherche || !recherchePleine(telephone.current, affichage, true)) return;
		// La Recherche s'ouvre vide, sur « Autour de moi » et la ligne d'aide ; « Annuler » rend le texte du champ.
		texteAvant = texteRecherche;
		texteRecherche = '';
		registre.ouvrirRecherche();
	}

	/** « Annuler » ou un résultat choisi retirent l'entrée de la Recherche : elle se referme au retour. */
	function quitterRecherche(f: NonNullable<typeof fin>) {
		if (fin) return;
		fin = f;
		registre.fermerRecherche();
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
		registre.fermerRecherche();
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

	/* ---- Focus à la fermeture de la fiche ---- */

	// Doigt, pointeur ou clavier : rendre le focus au champ de recherche ouvrirait le clavier de l'écran après un toucher.
	$effect(() => suivreSaisie());

	/** Dernier élément à avoir reçu le focus hors de la fiche ouverte et de son aperçu. */
	let dernierFocus: HTMLElement | null = null;
	$effect(() => {
		const noter = (e: FocusEvent) => {
			const el = e.target;
			if (el instanceof HTMLElement && !colonne?.contains(el) && !apercu?.contains(el)) dernierFocus = el;
		};
		document.addEventListener('focusin', noter);
		return () => document.removeEventListener('focusin', noter);
	});

	/**
	 * Ce qui avait le focus quand la fiche ouverte s'est ouverte : le champ de recherche, la carte, une ligne d'une liste.
	 * Il le retrouve quand la fiche se ferme, par sa croix, celle de son aperçu ou le précédent : la croix disparaît
	 * avec elle, et le focus tomberait sur la page.
	 */
	let ouvreur: HTMLElement | null = null;
	let ficheAvant: string | null = null;
	$effect(() => {
		const f = registre.fiche;
		const cle = f && ('commune' in f ? `commune:${f.commune}` : `fiche:${f.fiche}`);
		untrack(() => {
			if (cle !== null && cle !== ficheAvant) ouvreur = dernierFocus;
			else if (cle === null && ficheAvant !== null) rendreFocusApresFiche();
			ficheAvant = cle;
		});
	});

	const visible = (el: HTMLElement) =>
		el.isConnected &&
		!(el as HTMLButtonElement).disabled &&
		(typeof el.checkVisibility !== 'function' || el.checkVisibility({ checkVisibilityCSS: true }));

	/**
	 * La fiche est fermée : le focus revient à ce qui l'avait ouverte, s'il est encore là. Sinon, ou quand c'est le
	 * champ de recherche après un toucher, il va au contenu de la page (`#contenu`), d'où le clavier repart.
	 */
	async function rendreFocusApresFiche() {
		const o = ouvreur;
		ouvreur = null;
		await tick();
		// Le focus est ailleurs que dans la fiche fermée (logo, lien « Carte ») : il y reste.
		if (document.activeElement && document.activeElement !== document.body) return;
		if (o && recherche?.contains(o)) {
			if (composantRecherche?.rendreFocus()) return;
		} else if (o && visible(o)) return o.focus();
		document.getElementById('contenu')?.focus();
	}

	/** Lien d'évitement : le clavier n'a pas à traverser la recherche et le panneau pour atteindre la carte. */
	async function allerCarte(e: MouseEvent) {
		e.preventDefault();
		// Sur bureau, la carte est déjà là : la vue du téléphone n'entre pas dans l'adresse.
		if (telephone.current) registre.affichage = 'carte';
		await tick();
		document.querySelector<HTMLElement>('#carte .maplibregl-canvas')?.focus();
	}

	/* ---- Panneau : le sommaire ou une rubrique ---- */

	/** La rubrique que montre le panneau, et la couche qui la déclare ; `null` : le sommaire. */
	const ouverte = $derived(
		rubriquesDuSommaire(COUCHES).find(({ rubrique: r }) => !r.fiche && r.id === registre.panneau) ?? null
	);

	/** Une ligne du sommaire ouvre sa rubrique : le focus va sur son titre. */
	async function ouvrirRubrique(id: string) {
		registre.panneau = id;
		await tick();
		document.getElementById(`volet-${id}-titre`)?.focus();
	}

	/** Le lien de retour ou Échap ramènent au sommaire : le focus revient sur la ligne de la rubrique quittée. */
	async function retourSommaire() {
		const id = registre.panneau;
		registre.panneau = SOMMAIRE;
		await tick();
		document.querySelector<HTMLElement>(`.sommaire [data-rubrique="${id}"]`)?.focus();
	}

	function retour(e: MouseEvent) {
		if (!clicSimple(e)) return;
		e.preventDefault();
		retourSommaire();
	}
</script>

<div
	class="app"
	class:avec-fiche={registre.commune ?? registre.propre}
	class:recherche-pleine={pleine}
	data-affichage={affichage}
>
	<!-- Le contenu de la page, où mène « Aller au contenu » de l'en-tête : la carte, son panneau et la fiche ouverte. La
		barre des vues, des commandes d'affichage, reste autour. « Aller à la carte », premier arrêt du contenu, passe la
		recherche et le panneau pour mener au canevas. -->
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

			<!-- Calques de chaque couche, dans l'ordre du registre ; importés la première fois qu'elle est dessinée. -->
			{#if registre.map}
				<!-- Sous toutes les couches : le gris voile le fond, pas les éléments. -->
				<Grisage map={registre.map} sous={ancre(COUCHES[0].id)} {grisees} />
				<!-- La carte d'une couche n'a pas de balisage : seuls s'y lisent les messages des couches dont le code n'a pas pu être chargé. -->
				<div class="echecs-couches" aria-live="polite">
					{#each COUCHES as c (c.id)}
						{#if registre.montee(c.id)}
							{#await registre.composant(c, 'Carte') then module}
								{#if module}<module.default ctx={registre.contexte(c)} />{/if}
							{:catch}
								<p>La couche «&nbsp;{c.nom}&nbsp;» n’a pas pu s’afficher sur la carte. Rechargez la page.</p>
							{/await}
						{/if}
					{/each}
				</div>
			{/if}

			<div class="recherche" bind:this={recherche}>
				<Recherche
					bind:this={composantRecherche}
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
			</div>

			<!-- Le panneau, posé sur la carte : le sommaire, ou la rubrique qu'on y a ouverte. -->
			{#if !telephone.current}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div class="volet" onkeydown={(e) => e.key === 'Escape' && ouverte && retourSommaire()}>
					{@render panneau()}
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

		<!-- Téléphone : la vue du panneau, le sommaire ou la rubrique ouverte, l'une ou l'autre. -->
		{#if telephone.current && affichage === 'panneau'}
			<div class="vue-panneau">
				{@render panneau()}
			</div>
		{/if}

		{#if registre.commune ?? registre.propre}
			{@const fiche = registre.commune ?? registre.propre!}
			<!-- Une seule colonne, pour une commune ou une fiche propre : changer de fiche remplace son contenu sans la refermer. -->
			<div class="colonne" bind:this={colonne} in:entree={{ x: 40 }}>
				<FicheOuverte {registre} ouverte={fiche} />
			</div>
		{/if}
	</main>

	<!-- Masquée sur bureau par la feuille de style : sur téléphone, elle est là dès le premier rendu. -->
	<nav class="barre-vues" aria-label="Affichage">
		<button type="button" aria-pressed={affichage === 'panneau'} onclick={() => (registre.affichage = 'panneau')}>
			Sujets
		</button>
		<button type="button" aria-pressed={affichage === 'carte'} onclick={() => (registre.affichage = 'carte')}>
			Carte
		</button>
		<!-- « Détail » n'apparaît que quand une fiche est ouverte : il n'aurait rien à montrer. -->
		{#if registre.fiche}
			<button type="button" aria-pressed={affichage === 'fiche'} onclick={() => (registre.affichage = 'fiche')}>
				Détail
			</button>
		{/if}
	</nav>
</div>

{#snippet panneau()}
	{#if ouverte}
		<Volet rubrique={ouverte.rubrique} couche={ouverte.couche} {registre} onretour={retour} />
	{:else}
		<Sommaire {registre} communes={data.communes} onouvrir={ouvrirRubrique} />
	{/if}
{/snippet}

{@render children()}

<style>
	.app {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr);
		height: calc(100dvh - var(--size-header));
		position: relative;
		color: var(--color-ink-2);
		font-family: var(--font-display);
	}
	/* Sur la carte, l'anneau de focus et le soulignement orange des liens passent avant ce que les composants et
	   MapLibre en disent : le titre de la fiche, les boutons de zoom, le fil d'Ariane gardent les leurs. */
	.app :global(:focus-visible) {
		outline: var(--rule-bar) solid var(--color-focus);
		outline-offset: var(--space-3xs);
	}
	.app :global(a) {
		text-decoration-color: var(--color-accent);
		text-underline-offset: 0.18em;
	}
	/* Le contenu : la carte, puis la fiche ouverte, qui prend une colonne à droite et la rétrécit. */
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
		/* Un filtre neutre donne à la recherche son propre calque. Sans lui, Chromium en rendu logiciel (sans
		   accélération graphique) laissait un trou de sa taille dans la carte, retourné en bas à gauche : le fond
		   de la page y paraissait en blanc, alors que la carte elle-même y était bien dessinée. */
		filter: opacity(1);
	}
	/* Pendant la saisie, les résultats passent devant l'aperçu (téléphone). */
	.recherche:focus-within {
		z-index: 5;
	}
	/* Couches qui n'ont pas pu s'afficher : en bas de la carte, l'une sous l'autre, sans gêner les clics sur la carte. */
	.echecs-couches {
		position: absolute;
		z-index: 3;
		left: 10px;
		right: 10px;
		bottom: 40px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
		pointer-events: none;
	}
	.echecs-couches p {
		margin: 0;
		max-width: 360px;
		padding: 8px 12px;
		border-radius: 10px;
		background: var(--color-sheet);
		box-shadow: 0 2px 10px rgb(0 0 0 / 0.18);
		font-size: 14px;
		color: var(--color-erreur);
		pointer-events: auto;
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
		background: var(--color-sheet);
		font-size: 14px;
		color: var(--color-erreur);
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
		color: var(--color-muted);
		cursor: pointer;
	}
	.avis button:hover {
		background: var(--color-paper-2);
		color: var(--color-ink);
	}
	@media (pointer: coarse) {
		.avis button {
			width: 44px;
			height: 44px;
			margin-block: -10px;
		}
	}
	/*
	 * Sur la carte, un volet flotte sur l'image : la feuille claire et son filet d'encre en tête suffisent à l'en
	 * détacher, sans ombre ni coins arrondis.
	 *
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
		/* Le volet est à la hauteur de son contenu, sans dépasser le bas de la carte. */
		height: fit-content;
		max-height: calc(100% - 88px);
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
		background: oklch(99% 0.003 255 / 0.9);
		font-size: 12px;
		color: var(--color-muted);
	}
	.liens a:hover {
		color: var(--color-ink);
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
	.vue-panneau {
		display: none;
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
		/* Le panneau du bureau, rendu à la pré-génération, ne s'affiche pas avant que la requête ne le retire. */
		.zone-carte .volet {
			display: none;
		}
		.zone-carte,
		.colonne,
		.vue-panneau {
			grid-area: 1 / 1;
		}
		.colonne,
		.vue-panneau {
			z-index: 6;
		}
		/* Le panneau laisse en tête la place de la recherche, qui reste au-dessus de lui. */
		.vue-panneau {
			display: block;
			padding-top: 62px;
			overflow-y: auto;
			/* Arrivé en bas de la liste, le défilement ne passe pas à la page. */
			overscroll-behavior: contain;
			background: var(--color-paper);
		}
		.vue-panneau > :global(*) {
			min-height: 100%;
			box-sizing: border-box;
		}
		/* visibility plutôt que display : la carte garde sa taille, et ce qui est caché sort de l'ordre de tabulation. */
		.app:not([data-affichage='carte']) .zone-carte,
		.app:not([data-affichage='fiche']) .colonne,
		.app:not([data-affichage='panneau']) .vue-panneau {
			visibility: hidden;
		}
		/* La recherche, posée sur la carte, reste en tête du panneau. */
		.app[data-affichage='panneau'] .recherche {
			z-index: 7;
			visibility: visible;
		}
		/* MapLibre force « visibility: visible » sur l'attribution dépliée. */
		.app:not([data-affichage='carte']) .zone-carte :global(.maplibregl-control-container) {
			display: none;
		}
		.barre-vues {
			grid-area: 2 / 1;
			display: flex;
			gap: 6px;
			padding: 6px 12px calc(6px + env(safe-area-inset-bottom));
			background: var(--color-sheet);
			border-top: var(--rule-bar) solid var(--color-rule-2);
		}
		/* La barre des vues, à angle droit, la vue courante en encre. */
		.barre-vues button {
			flex: 1;
			min-height: 44px;
			border: 1px solid var(--color-rule-2);
			border-radius: var(--radius-pill);
			background: var(--color-sheet);
			color: var(--color-ink);
			font: inherit;
			font-size: 15px;
			font-weight: 600;
			cursor: pointer;
		}
		.barre-vues button[aria-pressed='true'] {
			background: var(--color-ink);
			color: var(--color-accent-ink);
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
			visibility: visible;
		}
		.recherche-pleine .zone-carte,
		.recherche-pleine .barre-vues,
		.recherche-pleine .evitement,
		:global(header:has(~ .app.recherche-pleine)),
		:global(.evitement-contenu:has(~ .app.recherche-pleine)) {
			visibility: hidden;
		}
		.recherche-pleine .zone-carte :global(.maplibregl-control-container),
		.recherche-pleine .avis {
			display: none;
		}
	}
	.evitement {
		position: absolute;
		z-index: 30;
		left: 8px;
		top: 8px;
		padding: 10px 14px;
		background: var(--color-sheet);
		font-weight: 600;
	}
	.evitement:hover {
		background: var(--color-paper-2);
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
