<script lang="ts">
	import { untrack } from 'svelte';
	import { normaliser } from '#lib/labels.js';
	import type { Commune, Resultat } from '#lib/types.js';
	import { typographier } from '#lib/almanach/typographie.js';
	import { ancienEtActuelle, avecAdresses, chercherAdresses, resultatsLocaux } from './recherche.js';

	/*
	 * Recherche flottante du socle : communes, résultats des couches (fiches propres et `chercher`), adresses et
	 * lieux swisstopo, dans cet ordre, et « Autour de moi ». La position du visiteur n'est envoyée à personne : elle n'est rendue qu'à `onchoix`.
	 *
	 * Sur téléphone, toucher le champ demande la Recherche plein écran (`onouvrir`), que la coquille ouvre en
	 * passant `plein` : le champ en haut avec « Annuler », puis, avant toute saisie, « Autour de moi » et une ligne
	 * d'aide, et ensuite les résultats sur tout l'écran. Rien de ce qu'on tape n'est retenu.
	 */
	let {
		communes,
		onchoix,
		chercherCouches = () => [],
		texte = $bindable(''),
		plein = false,
		onouvrir,
		onannuler
	}: {
		communes: Commune[];
		onchoix: (r: Resultat) => void;
		/** Résultats des couches pour une saisie, synchrones : fiches propres, puis éléments (n° de dossier…). */
		chercherCouches?: (texte: string) => Resultat[];
		texte?: string;
		/** Recherche plein écran (téléphone). */
		plein?: boolean;
		/** Le champ est touché, tapé ou reçoit le focus : la coquille ouvre la Recherche plein écran, sur téléphone. */
		onouvrir?: () => void;
		/** « Annuler » ou Échap, en plein écran. */
		onannuler?: () => void;
	} = $props();

	let localisation = $state(false);
	let erreur = $state('');

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
				onchoix({ type: 'adresse', categorie: 'Position', libelle: 'Votre position', lon: p.coords.longitude, lat: p.coords.latitude });
			},
			(e) => {
				localisation = false;
				erreur =
					e.code === e.PERMISSION_DENIED
						? 'Position refusée : autorisez la localisation pour ce site, ou cherchez une adresse.'
						: 'Position indisponible pour le moment. Cherchez plutôt une adresse.';
			},
			{ timeout: 15_000, maximumAge: 60_000 }
		);
	}

	let resultats: Resultat[] = $state([]);
	let ouvert = $state(false);
	let vide = $state(false);
	let liste: HTMLUListElement | undefined = $state();
	let champ: HTMLInputElement | undefined = $state();
	let timer: ReturnType<typeof setTimeout> | undefined;
	let fermeture: ReturnType<typeof setTimeout> | undefined;
	let requete = 0;
	let garderFerme = false;
	/** Texte pour lequel `resultats` a été calculé. */
	let cherche = '';

	/** Avant toute saisie, en plein écran : « Autour de moi » et la ligne d'aide. */
	const accueil = $derived(plein && !texte);
	/** En plein écran, les résultats remplissent l'écran tant qu'il y a une saisie. */
	const deroule = $derived((ouvert || plein) && !accueil);

	// Communes actuelles, anciennes communes et anciens noms (« Cully → Bourg-en-Lavaux »), puis les couches.
	const locaux = (q: string): Resultat[] => resultatsLocaux(communes, q, chercherCouches);

	/** Les adresses n'ont pas pu être cherchées pour la dernière saisie : dit sous le champ, à la place de « Aucun résultat ». */
	let erreurAdresses = $state('');

	async function chercher(q: string) {
		const n = ++requete;
		const local = locaux(q);
		resultats = local;
		cherche = q;
		vide = false;
		erreurAdresses = '';
		if (normaliser(q).length < 3) return;
		try {
			const adresses = await chercherAdresses(fetch, q, communes);
			if (n !== requete) return;
			resultats = avecAdresses(local, adresses);
			vide = resultats.length === 0;
		} catch {
			// Hors ligne, trop lent ou en erreur : les résultats locaux restent, et le visiteur sait qu'il manque les adresses.
			if (n === requete)
				erreurAdresses = 'La recherche d’adresses est indisponible pour le moment. Réessayez dans un instant.';
		}
	}

	function saisie() {
		onouvrir?.();
		ouvert = true;
		clearTimeout(timer);
		timer = setTimeout(() => chercher(texte), 200);
	}

	function choisir(r: Resultat) {
		// Choix au clavier dans la liste : le focus revient au champ, sans rouvrir la liste.
		if (liste?.contains(document.activeElement)) {
			garderFerme = true;
			champ?.focus();
		}
		// « Cully → Bourg-en-Lavaux » : le champ garde le nom de la commune actuelle, dont la fiche s'ouvre.
		texte = r.type === 'commune' ? r.commune.nom : r.libelle;
		ouvert = false;
		onchoix(r);
	}

	function entree() {
		if (!garderFerme) {
			ouvert = resultats.length > 0;
			onouvrir?.();
		}
		garderFerme = false;
	}

	/** Hauteur et haut de la partie visible de l'écran, au-dessus du clavier, en plein écran. */
	let visible: { hauteur: number; haut: number } | null = $state(null);
	$effect(() => {
		const vv = window.visualViewport;
		if (!plein || !vv) return;
		const suivre = () => (visible = { hauteur: vv.height, haut: vv.offsetTop });
		suivre();
		vv.addEventListener('resize', suivre);
		vv.addEventListener('scroll', suivre);
		return () => {
			vv.removeEventListener('resize', suivre);
			vv.removeEventListener('scroll', suivre);
			visible = null;
		};
	});

	let pleinAvant = false;
	$effect(() => {
		const p = plein;
		untrack(() => {
			if (p && !pleinAvant) ouvrirPlein();
			else if (!p && pleinAvant) fermerPlein();
			pleinAvant = p;
		});
	});

	/** À l'ouverture du plein écran, les résultats suivent le texte du champ, que la coquille vient de vider. */
	function ouvrirPlein() {
		ouvert = true;
		if (cherche !== texte) {
			clearTimeout(timer);
			chercher(texte);
		}
	}

	/**
	 * À la fermeture du plein écran, le focus revient au champ de la carte ; au toucher, le champ le quitte plutôt,
	 * pour que le clavier se ferme sur la carte.
	 */
	function fermerPlein() {
		ouvert = false;
		if (matchMedia('(pointer: coarse)').matches) champ?.blur();
		else if (document.activeElement !== champ) {
			garderFerme = true;
			champ?.focus();
		}
	}

	const boutons = () => [...(liste?.querySelectorAll('button') ?? [])];

	async function clavierChamp(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			// Entrée avant la fin du délai de saisie : on lance la recherche tout de suite.
			if (cherche !== texte) {
				clearTimeout(timer);
				await chercher(texte);
			}
			if (resultats[0]) choisir(resultats[0]);
		} else if (e.key === 'ArrowDown' && deroule && resultats.length) {
			e.preventDefault();
			boutons()[0]?.focus();
		} else if (e.key === 'Escape' && plein) {
			e.preventDefault();
			onannuler?.();
		} else if (e.key === 'Escape' && ouvert) {
			// Premier Échap : ferme la liste ; le suivant vide le champ (comportement natif).
			e.preventDefault();
			ouvert = false;
		}
	}

	function clavierListe(e: KeyboardEvent) {
		const liste = boutons();
		const i = liste.indexOf(document.activeElement as HTMLButtonElement);
		if (i < 0) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			liste[Math.min(i + 1, liste.length - 1)].focus();
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (i === 0) champ?.focus();
			else liste[i - 1].focus();
		} else if (e.key === 'Escape') {
			if (plein) return onannuler?.();
			ouvert = false;
			champ?.focus();
		}
	}

	// La liste reste ouverte tant que le focus est dans le composant (clavier) ; le délai
	// laisse passer le clic sur un résultat dans les navigateurs qui ne donnent pas le focus aux boutons.
	function sortie(e: FocusEvent) {
		if (plein) return;
		const cible = e.relatedTarget as Node | null;
		if (cible && (e.currentTarget as HTMLElement).contains(cible)) return;
		clearTimeout(fermeture);
		fermeture = setTimeout(() => (ouvert = false), 150);
	}
</script>

<div
	class="recherche"
	class:plein
	style:height={visible ? `${visible.hauteur}px` : undefined}
	style:translate={visible?.haut ? `0 ${visible.haut}px` : undefined}
	onfocusout={sortie}
	onfocusin={() => clearTimeout(fermeture)}
>
	<div class="ligne">
		<div class="champ">
			<input
				bind:this={champ}
				type="search"
				name="q"
				placeholder="Adresse, commune, n°&nbsp;de dossier…"
				aria-label="Rechercher une adresse, une commune, un numéro de dossier ou d’objet"
				autocomplete="off"
				spellcheck="false"
				bind:value={texte}
				oninput={saisie}
				onfocus={entree}
				onclick={() => onouvrir?.()}
				onkeydown={clavierChamp}
			/>
			{#if !plein}
				<button
					class="autour"
					type="button"
					onclick={autourDeMoi}
					disabled={localisation}
					title="Autour de moi"
					aria-label={localisation ? 'Localisation en cours' : 'Autour de moi'}
				>
					<span aria-hidden="true">◎</span>
				</button>
			{/if}
		</div>
		{#if plein}
			<button class="annuler" type="button" onclick={() => onannuler?.()}>Annuler</button>
		{/if}
	</div>
	{#if accueil}
		<div class="accueil">
			<button class="autour-large" type="button" onclick={autourDeMoi} disabled={localisation}>
				<span aria-hidden="true">◎</span>
				{localisation ? 'Localisation en cours…' : 'Autour de moi'}
			</button>
			<p class="aide">Une adresse, une commune, un n°&nbsp;de dossier ou d’objet</p>
		</div>
	{:else if deroule && resultats.length}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<ul bind:this={liste} aria-label="Résultats de recherche" onkeydown={clavierListe}>
			{#each resultats as r, i (i)}
				{@const ancien = ancienEtActuelle(r)}
				<li>
					<button type="button" onclick={() => choisir(r)}>
						<span class="type">{r.type === 'commune' ? 'Commune' : r.type === 'adresse' ? r.categorie : r.nomCouche}</span>
						{#if ancien}
							<span
								>{ancien[0]}<span aria-hidden="true">&nbsp;→ </span><span class="lecteur-seul"
									>, aujourd’hui </span
								>{ancien[1]}</span
							>
						{:else}
							<span>{typographier(r.libelle)}</span>
						{/if}
					</button>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="annonce" aria-live="polite">
		{#if deroule && resultats.length}
			{resultats.length}&nbsp;résultat{resultats.length > 1 ? 's' : ''}, flèche bas pour les parcourir.
		{:else if deroule && vide}
			Aucun résultat. Essayez un nom de commune, une adresse ou un n°&nbsp;de dossier.
		{/if}
	</p>
	{#if deroule && vide && !resultats.length}
		<p class="aucun">
			Aucun résultat pour cette recherche. Essayez un nom de commune, une adresse ou un n°&nbsp;de dossier.
		</p>
	{/if}
	<p class="erreur" role="status">{erreur || (deroule ? erreurAdresses : '')}</p>
</div>

<style>
	.recherche {
		position: relative;
	}
	.ligne {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.champ {
		flex: 1;
		min-width: 0;
		display: flex;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: var(--surface);
	}
	input {
		flex: 1;
		min-width: 0;
		min-height: 44px;
		padding: 10px 12px;
		font-size: 16px;
		border: 0;
		border-radius: 10px 0 0 10px;
		background: none;
		color: inherit;
	}
	.autour {
		flex: none;
		width: 44px;
		justify-content: center;
		align-items: center;
		border-left: 1px solid var(--line);
		border-radius: 0 10px 10px 0;
		font-size: 18px;
		color: var(--accent);
	}
	.autour:disabled {
		cursor: progress;
		opacity: 0.6;
	}
	.erreur {
		margin: 4px 0 0;
		padding: 6px 10px;
		border-radius: 8px;
		background: var(--surface);
		color: var(--erreur);
		font-size: 13px;
	}
	/* Région annoncée par les lecteurs d'écran : vide, elle ne doit pas créer d'espace. */
	.erreur:empty {
		position: absolute;
		padding: 0;
	}
	ul,
	.aucun {
		position: absolute;
		z-index: 20;
		left: 0;
		right: 0;
		top: calc(100% + 4px);
		margin: 0;
		padding: 4px;
		list-style: none;
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 10px;
		box-shadow: 0 8px 24px rgb(0 0 0 / 0.12);
	}
	/* La liste tient dans la partie visible (clavier ouvert sur téléphone) et défile au-delà. */
	ul {
		max-height: calc(100dvh - 180px);
		overflow-y: auto;
	}
	.aucun {
		padding: 10px 12px;
		font-size: 14px;
		color: var(--muted);
	}
	button {
		display: flex;
		align-items: baseline;
		gap: 8px;
		width: 100%;
		min-height: 40px;
		text-align: left;
		padding: 8px 10px;
		border: 0;
		background: none;
		font: inherit;
		font-size: 14px;
		color: inherit;
		border-radius: 6px;
		cursor: pointer;
	}
	button:hover,
	button:focus-visible {
		background: var(--bg);
	}
	.type {
		flex: none;
		width: 64px;
		color: var(--muted);
		font-size: 12px;
	}
	.annuler {
		flex: none;
		width: auto;
		min-height: 44px;
		padding: 8px;
		font-size: 16px;
		font-weight: 600;
		color: var(--accent);
	}
	.accueil {
		margin-top: 12px;
	}
	.autour-large {
		align-items: center;
		gap: 10px;
		min-height: 48px;
		font-size: 16px;
		font-weight: 600;
		color: var(--accent);
	}
	.autour-large:disabled {
		cursor: progress;
		opacity: 0.6;
	}
	.aide {
		margin: 4px 10px 0;
		font-size: 14px;
		color: var(--muted);
	}

	/* Plein écran (téléphone) : le champ en haut, puis les résultats jusqu'au clavier, qui défilent. */
	.plein {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 8px 8px 0 12px;
		padding-top: max(8px, env(safe-area-inset-top));
		background: var(--surface);
	}
	.plein ul,
	.plein .aucun {
		position: static;
		margin-top: 8px;
		padding: 0 0 8px;
		border: 0;
		border-radius: 0;
		box-shadow: none;
	}
	.plein ul {
		flex: 1 1 auto;
		/* Arrivée en bas de la liste, le défilement ne passe pas à la page dessous. */
		overscroll-behavior: contain;
		min-height: 0;
		max-height: none;
		border-top: 1px solid var(--line);
	}
	.plein li button {
		min-height: 48px;
		font-size: 16px;
		align-items: center;
	}
	.plein .type {
		width: 72px;
		font-size: 13px;
	}
	.annonce {
		position: absolute;
		width: 1px;
		height: 1px;
		margin: -1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
