<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import { MediaQuery } from 'svelte/reactivity';
	import { resolve } from '$app/paths';
	import { afterNavigate, goto } from '$app/navigation';
	import { page } from '$app/state';
	import Map from '#lib/components/Map.svelte';
	import Recherche from '#lib/components/Recherche.svelte';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import DossierFiche from '#lib/components/DossierFiche.svelte';
	import { getActive, getCommuneDossiers, getCommunes, getDossier } from '#lib/data.js';
	import { NATURES, STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import { dateLongue } from '#lib/dates.js';
	import { ecrireEtat, lireEtat, STATUTS_EN_COURS, type EtatCarte, type Tri } from '#lib/etat.js';
	import type { Centre, Commune, Dossier, Resultat, Statut } from '#lib/types.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	const ANNEE_COURANTE = new Date().getFullYear();
	const DEPUIS_DEFAUT = ANNEE_COURANTE - 2;
	const LISTE_MAX = 150;
	/** Au-delà (communes visibles cumulées), l'historique serait trop lourd à charger pour la liste. */
	const HISTO_MAX_DOSSIERS = 12_000;

	/** Téléphone en portrait : carte et liste occupent tour à tour tout l'écran. Même requête que dans le CSS. */
	const telephone = new MediaQuery('(max-width: 760px) and (min-height: 521px)', false);

	let actifs: Dossier[] = $state([]);
	let communes: Commune[] = $state([]);
	let carte: ReturnType<typeof Map> | undefined = $state();
	let vue: [number, number, number, number] | null = $state(null);
	let centre: Centre | null = $state(null);

	let historique = $state(false);
	let aerien = $state(false);
	let nature = $state('');
	let tri: Tri = $state('recent');
	let anneeMin = $state(DEPUIS_DEFAUT);
	let statutsActifs: Statut[] = $state([...STATUTS_EN_COURS]);
	let statutsHisto: Statut[] = $state([...STATUTS_ORDRE]);
	/** N° du dossier ouvert, connu avant que sa fiche soit chargée. */
	let ouvert: number | null = $state(null);
	let selection: Dossier | null = $state(null);
	/** Adresse cherchée ou position GPS, marquée sur la carte ; jamais écrite dans l'URL. */
	let repere: [number, number] | null = $state(null);
	/** Vue de la carte avant l'ouverture d'une fiche, rétablie au retour à la liste. */
	let vueAvant: Centre | null = null;
	let mode: 'carte' | 'liste' = $state('carte');
	let reglagesOuverts = $state(false);
	let erreur = $state('');
	let echecChargement = $state(false);
	let localisation = $state(false);
	let detail: HTMLDivElement | undefined = $state();
	let compte: HTMLParagraphElement | undefined = $state();

	const statutsProposes = $derived<Statut[]>(historique ? STATUTS_ORDRE : STATUTS_EN_COURS);
	const statuts = $derived(historique ? statutsHisto : statutsActifs);
	const filtresActifs = $derived(
		Number(statuts.length !== statutsProposes.length) + Number(!!nature) + Number(aerien) + Number(tri !== 'recent')
	);

	/* Historique dans la liste : dossiers des communes visibles (data/communes/tout/<slug>.json). */
	let histoCommunes: Record<string, Dossier[]> = $state.raw({});
	let histoEchec = $state(false);
	const communesVisibles = $derived.by(() => {
		if (!vue || !historique) return [];
		const [w, s, e, n] = vue;
		return communes.filter(({ bbox: [cw, cs, ce, cn] }) => cw <= e && ce >= w && cs <= n && cn >= s);
	});
	const histoTropLarge = $derived(communesVisibles.reduce((t, c) => t + c.total, 0) > HISTO_MAX_DOSSIERS);
	const histoChargement = $derived(
		!histoTropLarge && !histoEchec && communesVisibles.some((c) => !(c.slug in histoCommunes))
	);
	$effect(() => {
		if (histoTropLarge) return;
		const charges = untrack(() => histoCommunes);
		for (const c of communesVisibles.filter((c) => !(c.slug in charges))) {
			getCommuneDossiers(fetch, c.slug).then(
				(ds) => (histoCommunes = { ...histoCommunes, [c.slug]: ds }),
				() => (histoEchec = true)
			);
		}
	});

	const idsActifs = $derived(new Set(actifs.map((d) => d.id)));
	const annee = (d: Dossier) => Number(d.debut?.slice(0, 4) ?? 0);
	/** Publication (début d'enquête) la plus récente d'abord. */
	const parPublication = (a: Dossier, b: Dossier) => (b.debut ?? '').localeCompare(a.debut ?? '') || b.id - a.id;
	/** Enquêtes en cours d'abord, la plus proche de sa fin en tête ; ensuite par publication. */
	const parFin = (a: Dossier, b: Dossier) =>
		Number(b.statut === 'enquete') - Number(a.statut === 'enquete') ||
		(a.statut === 'enquete' ? (a.fin ?? '').localeCompare(b.fin ?? '') : 0) ||
		parPublication(a, b);

	const visibles = $derived.by(() => {
		if (!vue) return [];
		const [w, s, e, n] = vue;
		const garde = (d: Dossier) =>
			d.lon >= w && d.lon <= e && d.lat >= s && d.lat <= n &&
			statuts.includes(d.statut) && (!nature || d.nature === nature);
		const liste = actifs.filter(garde);
		// Comme sur la carte : l'historique est filtré par année, pas les dossiers en cours.
		if (historique && !histoTropLarge)
			for (const c of communesVisibles)
				for (const d of histoCommunes[c.slug] ?? [])
					if (!idsActifs.has(d.id) && annee(d) >= anneeMin && garde(d)) liste.push(d);
		return liste.sort(tri === 'fin' ? parFin : parPublication);
	});

	async function charger() {
		echecChargement = false;
		try {
			[actifs, communes] = await Promise.all([getActive(fetch), getCommunes(fetch)]);
		} catch {
			echecChargement = true;
		}
	}
	onMount(charger);

	/* ---- État dans l'URL : lu côté navigateur seulement (pages pré-générées sans paramètres). ---- */

	/** Requête déjà reflétée par l'état ; `null` tant que l'URL de départ n'a pas été lue. */
	let synchro: string | null = null;
	/** La prochaine écriture crée une entrée d'historique (ouverture d'une fiche) au lieu de remplacer. */
	let nouvelleEntree = false;

	const requete = $derived(
		ecrireEtat(
			{ d: ouvert, vue: centre, statuts, nature, historique, depuis: anneeMin, aerien, tri },
			statutsProposes,
			DEPUIS_DEFAUT
		)
	);

	afterNavigate(() => {
		if (synchro !== null) return;
		synchro = location.search;
		appliquer(lireEtat(new URLSearchParams(location.search)), true);
	});

	// État → URL. Les déplacements de carte et les filtres remplacent l'entrée courante.
	$effect(() => {
		const q = requete;
		untrack(() => {
			const push = nouvelleEntree;
			nouvelleEntree = false;
			if (synchro === null || q === location.search) return;
			synchro = q;
			goto(`${location.pathname}${q}`, {
				shallow: true,
				replace: !push,
				state: push ? { fiche: true } : page.state
			});
		});
	});

	// URL → état : boutons précédent et suivant du navigateur, lien « Carte » de l'en-tête.
	$effect(() => {
		const url = page.shallow?.url ?? page.url;
		const q = url.search;
		untrack(() => {
			if (synchro === null || q === synchro) return;
			synchro = q;
			appliquer(lireEtat(url.searchParams));
		});
	});

	async function appliquer(e: EtatCarte, initial = false) {
		historique = e.historique;
		aerien = e.aerien;
		nature = e.nature;
		tri = e.tri;
		anneeMin = Math.min(Math.max(e.depuis ?? DEPUIS_DEFAUT, 1999), ANNEE_COURANTE);
		if (e.historique) statutsHisto = e.statuts ?? [...STATUTS_ORDRE];
		else statutsActifs = e.statuts?.filter((s) => STATUTS_EN_COURS.includes(s)) ?? [...STATUTS_EN_COURS];
		if (e.vue) {
			centre = e.vue;
			carte?.aller(e.vue, !initial);
		}

		if (e.d == null) {
			if (ouvert != null) fermer();
		} else if (e.d !== ouvert) {
			ouvert = e.d;
			const d = await ouvrir(e.d);
			if (d && !e.vue) carte?.aller({ lon: d.lon, lat: d.lat, zoom: 16 }, !initial);
		}

		if (initial && e.commune && !e.vue && e.d == null) {
			const c = (await getCommunes(fetch).catch(() => [])).find((c) => c.slug === e.commune);
			if (c) carte?.cadrer(c.bbox, false);
		}
	}

	/* ---- Fiche ---- */

	/** Ouvre la fiche d'un dossier ; `nouvelle` : action de l'utilisateur, le bouton retour la refermera. */
	async function ouvrir(cible: number | Dossier, nouvelle = false): Promise<Dossier | undefined> {
		erreur = '';
		const id = typeof cible === 'number' ? cible : cible.id;
		const d =
			typeof cible === 'number'
				? (actifs.find((x) => x.id === id) ?? (await getDossier(fetch, id)))
				: cible;
		if (!d) {
			if (ouvert === id) ouvert = null;
			selection = null;
			erreur = `Aucun dossier n° ${id} dans les données (n° CAMAC à 5 ou 6 chiffres).`;
			return;
		}
		if (nouvelle && ouvert == null) {
			nouvelleEntree = true;
			vueAvant = centre;
		}
		ouvert = d.id;
		selection = d;
		await tick();
		// Sur téléphone en mode carte, un aperçu s'affiche sur la carte : le focus ne bouge pas.
		if (!telephone.current || mode === 'liste') {
			detail?.focus({ preventScroll: true });
			detail?.scrollIntoView({ block: telephone.current ? 'start' : 'nearest' });
		}
		return d;
	}

	/** Ferme la fiche ; le focus revient sur la carte du dossier quitté dans la liste, ou sur le compteur. */
	async function fermer() {
		const id = ouvert;
		ouvert = null;
		selection = null;
		await tick();
		if (telephone.current && mode === 'carte') return;
		const carteListe = document.querySelector<HTMLElement>(`.liste li[data-id="${id}"] .carte`);
		(carteListe ?? compte)?.focus({ preventScroll: true });
		(carteListe ?? compte)?.scrollIntoView({ block: 'nearest' });
	}

	/** « Retour à la liste » : revient à l'entrée d'historique d'avant la fiche, qui garde la vue d'alors. */
	function retour() {
		if (page.state.fiche) {
			history.back();
			return;
		}
		// Fiche ouverte depuis un lien : pas d'entrée précédente, on élargit la vue autour du dossier.
		const avant = vueAvant ?? (centre && { ...centre, zoom: Math.min(centre.zoom, 14) });
		fermer();
		if (avant) carte?.aller(avant);
	}

	function depuisListe(d: Dossier) {
		ouvrir(d, true);
		carte?.voler(d.lon, d.lat, 15);
	}

	function basculerStatut(s: Statut) {
		const liste = historique ? statutsHisto : statutsActifs;
		const suivante = liste.includes(s) ? liste.filter((x) => x !== s) : [...liste, s];
		if (historique) statutsHisto = suivante;
		else statutsActifs = suivante;
	}

	function choix(r: Resultat) {
		erreur = '';
		if (r.type === 'adresse') {
			repere = [r.lon, r.lat];
			carte?.voler(r.lon, r.lat, 16);
		} else if (r.type === 'commune') {
			repere = null;
			carte?.cadrer(r.commune.bbox);
		} else ouvrir(r.id, true).then((d) => d && carte?.voler(d.lon, d.lat, 16));
	}

	function autourDeMoi() {
		erreur = '';
		if (!navigator.geolocation) {
			erreur = 'La géolocalisation n’est pas disponible dans ce navigateur. Cherchez plutôt une adresse.';
			return;
		}
		localisation = true;
		navigator.geolocation.getCurrentPosition(
			(p) => {
				localisation = false;
				repere = [p.coords.longitude, p.coords.latitude];
				carte?.voler(p.coords.longitude, p.coords.latitude, 15);
			},
			(e) => {
				localisation = false;
				erreur =
					e.code === e.PERMISSION_DENIED
						? 'Position refusée : autorisez la localisation pour ce site, ou cherchez une adresse.'
						: 'Position indisponible pour le moment. Cherchez plutôt une adresse.';
			},
			{ timeout: 15_000, maximumAge: 60_000 }
		);
	}

	/** Lien d'évitement : le clavier n'a pas à traverser la liste (jusqu'à 150 dossiers) pour atteindre la carte. */
	async function allerCarte(e: MouseEvent) {
		e.preventDefault();
		mode = 'carte';
		await tick();
		document.querySelector<HTMLElement>('#carte .maplibregl-canvas')?.focus();
	}

	async function voirFiche() {
		mode = 'liste';
		await tick();
		detail?.focus({ preventScroll: true });
		detail?.scrollIntoView({ block: 'start' });
	}
</script>

<svelte:head>
	<title>Chantiers Vaud – carte des mises à l’enquête du canton de Vaud</title>
	<meta
		name="description"
		content="Toutes les demandes de permis de construire du canton de Vaud sur une carte : enquêtes publiques en cours, dates de consultation des dossiers, historique depuis 1999."
	/>
	<!-- Sans paramètres : la mesure d'audience (GoatCounter suit ce lien) ne reçoit pas le centre de la carte. -->
	<link rel="canonical" href={resolve('/')} />
</svelte:head>

<div class="app" class:mode-liste={mode === 'liste'}>
	<a class="evitement" href="#carte" onclick={allerCarte}>Aller à la carte</a>

	<section class="panneau" aria-label="Recherche et liste des dossiers">
		<div class="commandes">
			<Recherche {communes} onchoix={choix} />

			<div class="outils">
				<button class="bouton secondaire petit" type="button" onclick={autourDeMoi} disabled={localisation}>
					<span aria-hidden="true">◎</span> {localisation ? 'Localisation…' : 'Autour de moi'}
				</button>
				<button
					class="bouton secondaire petit reglages-bouton"
					type="button"
					aria-expanded={reglagesOuverts}
					aria-controls="reglages"
					onclick={() => (reglagesOuverts = !reglagesOuverts)}
				>
					Filtres{filtresActifs ? ` (${filtresActifs})` : ''}
					<span aria-hidden="true">{reglagesOuverts ? '▴' : '▾'}</span>
				</button>
				<label class="bascule"><input type="checkbox" bind:checked={historique} /> Historique</label>
			</div>

			<div class="reglages" id="reglages" class:ouverts={reglagesOuverts}>
				<div class="filtres">
					{#each statutsProposes as s (s)}
						<button
							type="button"
							class="puce"
							class:off={!statuts.includes(s)}
							aria-pressed={statuts.includes(s)}
							style:--c={STATUTS[s].couleur}
							onclick={() => basculerStatut(s)}
						>
							<span></span>{STATUTS[s].court}
						</button>
					{/each}
				</div>

				<div class="ligne">
					<select bind:value={nature} aria-label="Nature des travaux">
						<option value="">Toutes natures</option>
						{#each Object.entries(NATURES) as [k, v] (k)}
							<option value={k}>{v}</option>
						{/each}
					</select>
					<select bind:value={tri} aria-label="Ordre de la liste">
						<option value="recent">Publication récente d’abord</option>
						<option value="fin">Fin d’enquête la plus proche</option>
					</select>
					<label class="bascule"><input type="checkbox" bind:checked={aerien} /> Vue aérienne</label>
				</div>
				{#if historique}
					<label class="annee">
						<span>Historique depuis <strong>{anneeMin}</strong></span>
						<input type="range" min="1999" max={ANNEE_COURANTE} bind:value={anneeMin} />
					</label>
				{/if}
			</div>

			<p class="erreur" role="status">{erreur}</p>
		</div>

		<div class="resultats">
			{#if selection}
				<div class="detail" bind:this={detail} tabindex="-1" aria-label="Fiche du dossier n° {selection.id}">
					<div class="detail-haut">
						<button class="retour" type="button" onclick={retour}>← Retour à la liste</button>
						<button class="retour telephone" type="button" onclick={() => (mode = 'carte')}>Voir sur la carte</button>
					</div>
					<DossierFiche d={selection} lienFiche />
				</div>
			{:else}
				<p class="compte" bind:this={compte} tabindex="-1">
					{#if echecChargement}
						<span class="erreur">Les données n’ont pas pu être chargées.</span>
						<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
					{:else if !actifs.length}
						Chargement…
					{:else if historique && !histoTropLarge}
						<strong>{visibles.length}</strong> dossier{visibles.length > 1 ? 's' : ''} dans la zone affichée,
						historique depuis {anneeMin} compris
						{#if histoChargement}<span class="muted"> · chargement de l’historique…</span>{/if}
						{#if histoEchec}<span class="erreur"> · l’historique n’a pas pu être chargé</span>{/if}
					{:else}
						<strong>{visibles.length}</strong> dossier{visibles.length > 1 ? 's' : ''} en cours dans la zone affichée
						{#if historique}<span class="muted"> · zoomez sur la carte pour ajouter l’historique à la liste</span>{/if}
					{/if}
				</p>
				{#if actifs.length && !visibles.length && !histoChargement}
					<p class="muted vide">
						{#if !statuts.length}
							Aucun statut n’est sélectionné : activez-en au moins un pour afficher la liste.
						{:else if historique && histoTropLarge}
							Aucun dossier en cours ne correspond à ces filtres ici. Zoomez pour lister aussi l’historique.
						{:else}
							Aucun dossier ne correspond à ces filtres dans la zone affichée. Dézoomez la carte ou
							choisissez « Toutes natures ».
						{/if}
					</p>
				{/if}
				<ul class="liste">
					{#each visibles.slice(0, LISTE_MAX) as d (d.id)}
						<li data-id={d.id}>
							<DossierCarte {d} onclick={() => depuisListe(d)} />
						</li>
					{/each}
				</ul>
				{#if visibles.length > LISTE_MAX}
					<p class="muted">… et {visibles.length - LISTE_MAX} autres : zoomez pour affiner.</p>
				{/if}
			{/if}

			<footer class="source">
				{data.meta.source}. Données mises à jour le {dateLongue(data.meta.mise_a_jour)}, sans foi
				publique : seule la <a href="https://www.vd.ch/territoire-et-construction/permis-de-construire/faq/avis-denquete/publication-fao" target="_blank" rel="noopener">FAO</a> fait foi.
				Fond de carte © swisstopo. <a href={resolve('/infos-legales')}>Informations légales</a> ·
				<a href={resolve('/a-propos')}>À propos</a>
			</footer>
		</div>
	</section>

	<div class="zone-carte" id="carte">
		<Map
			bind:this={carte}
			dossiers={actifs}
			{historique}
			{statuts}
			{nature}
			{anneeMin}
			{aerien}
			{repere}
			selection={selection?.id ?? null}
			point={selection ? [selection.lon, selection.lat] : null}
			onselect={(id) => ouvrir(id, true)}
			onview={(b, c) => {
				vue = b;
				centre = c;
			}}
		/>
		<div class="legende">
			{#each statutsProposes as s (s)}
				<span><i style:background={STATUTS[s].couleur}></i>{STATUTS[s].court}</span>
			{/each}
		</div>
		{#if selection}
			<div class="apercu">
				<DossierCarte d={selection} onclick={voirFiche} />
				<button class="fermer" type="button" aria-label="Fermer l’aperçu du dossier" onclick={retour}>×</button>
			</div>
		{/if}
	</div>

	<div class="bascule-vue" role="group" aria-label="Affichage">
		<button type="button" aria-pressed={mode === 'carte'} onclick={() => (mode = 'carte')}>Carte</button>
		<button type="button" aria-pressed={mode === 'liste'} onclick={() => (mode = 'liste')}>
			{selection ? 'Fiche' : `Liste (${visibles.length})`}
		</button>
	</div>
</div>

<style>
	.app {
		display: grid;
		/* Sur tablette (≈ 768 px), le panneau rétrécit pour laisser de la place à la carte. */
		grid-template-columns: clamp(320px, 42vw, 400px) 1fr;
		grid-template-rows: minmax(0, 1fr);
		height: calc(100dvh - var(--header-h));
		position: relative;
	}
	.panneau {
		overflow-y: auto;
		padding: 14px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		background: var(--bg);
		border-right: 1px solid var(--line);
	}
	.commandes,
	.resultats,
	.reglages {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.resultats {
		flex: 1;
	}
	.zone-carte {
		position: relative;
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
	.outils,
	.ligne,
	.filtres {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
	}
	.petit {
		padding: 6px 10px;
		font-size: 13px;
	}
	.petit:disabled {
		cursor: progress;
		opacity: 0.7;
	}
	.bascule {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13.5px;
		cursor: pointer;
	}
	.bascule input {
		width: 18px;
		height: 18px;
		margin: 0;
		accent-color: var(--accent);
	}
	.puce {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: 999px;
		border: 1px solid var(--c);
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
		cursor: pointer;
	}
	.puce span {
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: var(--c);
	}
	.puce.off {
		border-color: var(--line);
		color: var(--muted);
	}
	.puce.off span {
		background: transparent;
		box-shadow: inset 0 0 0 1.5px var(--c);
	}
	select {
		padding: 7px 8px;
		border-radius: 8px;
		border: 1px solid var(--line);
		background: var(--surface);
		font: inherit;
		font-size: 14px;
		color: inherit;
		max-width: 100%;
	}
	.annee {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		min-width: 0;
	}
	.annee span {
		white-space: nowrap;
	}
	.annee input {
		flex: 1;
		min-width: 80px;
		accent-color: var(--accent);
	}
	.compte {
		margin: 4px 0 0;
		font-size: 14px;
	}
	.compte .bouton {
		margin-left: 6px;
	}
	.compte:focus {
		outline: none;
	}
	.vide {
		margin: 0;
		font-size: 14px;
		line-height: 1.45;
	}
	.liste {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.detail {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 12px;
		padding: 14px;
	}
	.detail:focus {
		outline: none;
	}
	.detail:focus-visible {
		outline: 3px solid var(--focus);
	}
	.detail-haut {
		display: flex;
		justify-content: space-between;
		margin: -10px -6px 0;
	}
	.retour {
		min-height: 44px;
		border: 0;
		background: none;
		color: var(--accent);
		font: inherit;
		font-size: 14px;
		padding: 0 6px;
		cursor: pointer;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
		margin: 0;
		font-size: 14px;
	}
	/* Région annoncée par les lecteurs d'écran : vide, elle ne doit pas créer d'espace. */
	.erreur:empty {
		position: absolute;
	}
	.source {
		margin-top: auto;
		padding-top: 12px;
	}
	/* En haut à gauche : en bas, l'attribution la recouvrirait sur une carte étroite. */
	.legende {
		position: absolute;
		left: 10px;
		top: 10px;
		display: flex;
		flex-wrap: wrap;
		gap: 4px 10px;
		max-width: calc(100% - 80px);
		padding: 6px 10px;
		background: rgb(255 255 255 / 0.92);
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
	/* Éléments propres au téléphone en portrait. */
	.reglages-bouton,
	.telephone,
	.apercu,
	.bascule-vue {
		display: none;
	}

	/* Zones tactiles d'au moins 44 px sur écran tactile. */
	@media (pointer: coarse), (max-width: 760px) {
		.petit,
		.puce,
		.bascule,
		select {
			min-height: 44px;
		}
	}

	/*
	 * Téléphone en portrait : la carte ou la liste occupe l'écran, une barre en bas bascule de l'une à l'autre.
	 * À l'horizontale (hauteur ≤ 520 px) et sur tablette, panneau et carte restent côte à côte.
	 */
	@media (max-width: 760px) and (min-height: 521px) {
		.app {
			grid-template-columns: 1fr;
			grid-template-rows: auto minmax(0, 1fr) auto;
		}
		.panneau {
			display: contents;
		}
		.commandes {
			grid-area: 1 / 1;
			/* Au-dessus de la carte : la liste de résultats de recherche déborde dessus. */
			position: relative;
			z-index: 3;
			padding: 10px 12px;
			background: var(--bg);
			border-bottom: 1px solid var(--line);
		}
		.resultats {
			grid-area: 2 / 1;
			overflow-y: auto;
			padding: 12px 12px 16px;
			background: var(--bg);
		}
		.zone-carte {
			grid-area: 2 / 1;
		}
		/* visibility plutôt que display : la carte garde sa taille, et le contenu caché sort de l'ordre de tabulation. */
		.app:not(.mode-liste) .resultats,
		.app.mode-liste .zone-carte {
			visibility: hidden;
		}
		/* MapLibre force « visibility: visible » sur l'attribution dépliée. */
		.app.mode-liste .zone-carte :global(.maplibregl-control-container) {
			display: none;
		}
		.reglages:not(.ouverts) {
			display: none;
		}
		.reglages-bouton {
			display: inline-flex;
		}
		.telephone {
			display: block;
		}
		.apercu {
			display: block;
			position: absolute;
			z-index: 2;
			left: 8px;
			right: 8px;
			/* Laisse visible le bouton des sources (attribution) en bas à droite. */
			bottom: 34px;
			box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
			border-radius: 10px;
		}
		.apercu :global(.carte) {
			padding-right: 48px;
		}
		.fermer {
			position: absolute;
			top: 0;
			right: 0;
			width: 44px;
			height: 44px;
			border: 0;
			background: none;
			font-size: 24px;
			line-height: 1;
			color: var(--muted);
			cursor: pointer;
		}
		.bascule-vue {
			grid-area: 3 / 1;
			display: flex;
			gap: 6px;
			padding: 6px 12px calc(6px + env(safe-area-inset-bottom));
			background: var(--surface);
			border-top: 1px solid var(--line);
		}
		.bascule-vue button {
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
		.bascule-vue button[aria-pressed='true'] {
			background: var(--accent);
			color: #fff;
		}
	}
</style>
