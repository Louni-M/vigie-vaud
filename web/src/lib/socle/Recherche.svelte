<script lang="ts">
	import { normaliser } from '#lib/labels.js';
	import type { Commune, Resultat } from '#lib/types.js';
	import { chercherCommunes } from './recherche.js';

	/*
	 * Recherche flottante du socle : communes, adresses et lieux swisstopo, résultats des couches (`chercher`),
	 * et « Autour de moi ». La position du visiteur n'est envoyée à personne : elle n'est rendue qu'à `onchoix`.
	 */
	let {
		communes,
		onchoix,
		chercherCouches = () => [],
		texte = $bindable('')
	}: {
		communes: Commune[];
		onchoix: (r: Resultat) => void;
		/** Résultats des couches pour une saisie, synchrones (n° de dossier…). */
		chercherCouches?: (texte: string) => Extract<Resultat, { type: 'element' }>[];
		texte?: string;
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
						? 'Position refusée : autorisez la localisation pour ce site, ou cherchez une adresse.'
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

	// Communes actuelles, puis anciennes communes et anciens noms (« Cully → Bourg-en-Lavaux »).
	const locaux = (q: string): Resultat[] => [...chercherCouches(q), ...chercherCommunes(communes, q)];

	interface Lieu {
		attrs: { origin: string; label: string; detail?: string; lat: number; lon: number };
	}

	const TYPES: Record<string, string> = { address: 'Adresse', zipcode: 'NPA', gazetteer: 'Lieu' };

	/**
	 * Le canton figure dans `detail` pour les adresses (« … ch vd ») et dans le libellé des lieux (« (VD) ») ;
	 * pour les NPA, on vérifie que le point tombe dans le cadre d'une commune vaudoise.
	 */
	function vaudois({ attrs: a }: Lieu): boolean {
		if (a.origin === 'address') return / ch vd$/.test(a.detail ?? '');
		if (a.origin === 'gazetteer') return a.label.includes('(VD)');
		return communes.some(({ bbox: [w, s, e, n] }) => a.lon >= w && a.lon <= e && a.lat >= s && a.lat <= n);
	}

	/**
	 * « <i>Lieu</i> <b>Donatyre</b> (VD) - Avenches » → « Donatyre - Avenches », et « Avenches - Avenches » → « Avenches » :
	 * le type est affiché à part.
	 */
	const nettoyer = (label: string) =>
		label
			.replace(/<i>.*?<\/i>/g, '')
			.replace(/<[^>]+>/g, '')
			.replace(' (VD)', '')
			.replace(/\s+/g, ' ')
			.trim()
			.replace(/^(.+) - \1$/, '$1');

	async function chercher(q: string) {
		const n = ++requete;
		const local = locaux(q);
		resultats = local;
		cherche = q;
		vide = false;
		if (normaliser(q).length < 3) return;
		// Recherche d'adresses swisstopo (geo.admin.ch) ; le filtre par cadre (bbox) vide les résultats.
		const url = new URL('https://api3.geo.admin.ch/rest/services/api/SearchServer');
		url.search = new URLSearchParams({
			searchText: q,
			type: 'locations',
			// Pas de « gg25 » : les communes viennent de la liste locale (communes actuelles).
			origins: 'address,zipcode,gazetteer',
			sr: '4326',
			lang: 'fr',
			// Les résultats hors canton sont écartés ensuite : on en demande davantage.
			limit: '20'
		}).toString();
		try {
			const r = await fetch(url);
			const json = await r.json();
			if (n !== requete) return;
			const adresses: Resultat[] = ((json.results ?? []) as Lieu[]).filter(vaudois).map(({ attrs: a }) => ({
				type: 'adresse',
				categorie: TYPES[a.origin] ?? 'Lieu',
				libelle: nettoyer(a.label),
				lon: a.lon,
				lat: a.lat
			}));
			// Un même lieu revient sous plusieurs catégories (sortie d'autoroute, camping…) : un seul suffit.
			const vus = new Set(local.map((r) => r.libelle));
			const uniques = adresses.filter((r) => !vus.has(r.libelle) && vus.add(r.libelle));
			resultats = [...local, ...uniques].slice(0, 10);
		} catch {
			/* hors ligne : on garde les résultats locaux */
		}
		if (n === requete) vide = resultats.length === 0;
	}

	function saisie() {
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
		if (!garderFerme) ouvert = resultats.length > 0;
		garderFerme = false;
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
		} else if (e.key === 'ArrowDown' && ouvert && resultats.length) {
			e.preventDefault();
			boutons()[0]?.focus();
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
			ouvert = false;
			champ?.focus();
		}
	}

	// La liste reste ouverte tant que le focus est dans le composant (clavier) ; le délai
	// laisse passer le clic sur un résultat dans les navigateurs qui ne donnent pas le focus aux boutons.
	function sortie(e: FocusEvent) {
		const cible = e.relatedTarget as Node | null;
		if (cible && (e.currentTarget as HTMLElement).contains(cible)) return;
		clearTimeout(fermeture);
		fermeture = setTimeout(() => (ouvert = false), 150);
	}
</script>

<div class="recherche" onfocusout={sortie} onfocusin={() => clearTimeout(fermeture)}>
	<div class="champ">
		<input
			bind:this={champ}
			type="search"
			placeholder="Adresse, commune ou n° de dossier"
			aria-label="Rechercher une adresse, une commune ou un numéro de dossier"
			autocomplete="off"
			bind:value={texte}
			oninput={saisie}
			onfocus={entree}
			onkeydown={clavierChamp}
		/>
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
	</div>
	{#if ouvert && resultats.length}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
		<ul bind:this={liste} aria-label="Résultats de recherche" onkeydown={clavierListe}>
			{#each resultats as r, i (i)}
				<li>
					<button type="button" onclick={() => choisir(r)}>
						<span class="type">{r.type === 'commune' ? 'Commune' : r.type === 'adresse' ? r.categorie : r.nomCouche}</span>
						<span>{r.libelle}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="annonce" aria-live="polite">
		{#if ouvert && resultats.length}
			{resultats.length} résultat{resultats.length > 1 ? 's' : ''}, flèche bas pour les parcourir.
		{:else if ouvert && vide}
			Aucun résultat.
		{/if}
	</p>
	{#if ouvert && vide && !resultats.length}
		<p class="aucun">Aucun résultat pour cette recherche.</p>
	{/if}
	<p class="erreur" role="status">{erreur}</p>
</div>

<style>
	.recherche {
		position: relative;
	}
	.champ {
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
