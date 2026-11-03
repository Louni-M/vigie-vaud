<script lang="ts">
	import '#lib/almanach/almanach.css';
	import { insecables } from '#lib/almanach/typographie.js';
	import {
		dateHeure,
		libelleCellule,
		libelleCommunes,
		libelleEtat,
		libelleLimites,
		libelleMode,
		libellePlateforme,
		type CommunePlateforme
	} from '#lib/couverture.js';
	import { couvertureChargee, couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import { lienIssuePlateforme, lienPannes } from '#lib/etat-sources.js';
	import { dernierImport } from '#lib/imports-conseils.js';
	import { importsCharges, importsCourants } from '#lib/imports-courants.svelte.js';
	import { canonique } from '#lib/indexation.js';
	import { normaliser } from '#lib/labels.js';
	import { lienCommune } from '#lib/registre/liens.js';
	import { libelleDonne, libelleVoie } from '#lib/sources.js';
	import type { PageProps } from './$types';
	import JourneeVerification from './JourneeVerification.svelte';

	let { data }: PageProps = $props();

	// La page est pré-générée sans l'état des sources ni le dernier import des conseils : ils sont chargés dans le
	// navigateur.
	const couverture = $derived(couvertureCourante(data.communes));
	const charge = $derived(couvertureChargee());
	const imports = $derived(importsCourants());
	const importsCharge = $derived(importsCharges());

	let recherche = $state('');
	const lignes = $derived.by(() => {
		const q = normaliser(recherche);
		return q ? data.communes.filter((c) => normaliser(c.nom).includes(q)) : data.communes;
	});

	const quand = (iso: string | null | undefined) => (iso ? `le ${dateHeure(iso)}` : '—');

	// Les communes d'une fiche de plateforme, par nom, pour qu'on y trouve la sienne.
	const parBfs = $derived(new Map(data.communes.map((c) => [c.bfs, c])));
	const communesTriees = (liste: readonly CommunePlateforme[]) =>
		[...liste].sort((a, b) =>
			(parBfs.get(a.bfs)?.nom ?? a.source.nom_court).localeCompare(parBfs.get(b.bfs)?.nom ?? b.source.nom_court, 'fr')
		);
</script>

<svelte:head>
	<title>Couverture – Vigie Vaud</title>
	<meta
		name="description"
		content="Pour chaque couche de Vigie Vaud et chaque commune vaudoise : comment les données sont obtenues, et si leur source répond."
	/>
	<link rel="canonical" href={canonique('/couverture')} />
</svelte:head>

<main class="almanach" data-theme="almanach">
	<div class="cadre">
		<header class="tete">
			<h1>Couverture</h1>
		</header>

		<div class="corps">
			<p class="chapeau">
				Pour chaque couche et chaque commune&nbsp;: le <strong>mode</strong> (les données viennent d’une API, sont
				scrapées, ou la commune n’est pas couverte) et l’<strong>état</strong> de la source, vérifié plusieurs fois par
				jour par une sonde. Les conseils sont importés une fois par jour&nbsp;; une sonde vérifie que leur source
				répond. Le site d’une commune n’est sondé qu’une fois par jour, juste avant son import&nbsp;: ses communes sont
				regroupées par plateforme.
			</p>

			<JourneeVerification />

			<section class="encarts" aria-label="Sources">
				{#each couverture.sources as s (s.source.id)}
					<article class="encart" aria-labelledby="source-{s.source.id}">
						<h2 id="source-{s.source.id}">{s.source.nom}</h2>
						<p class="etat" data-etat={charge ? s.etat.etat : undefined} aria-live="polite">
							{charge ? libelleEtat(s.etat) : 'État en cours de chargement…'}
						</p>
						{#if s.etat.etat === 'en_panne' && s.sonde?.motif}
							<p class="motif">Dernier échec&nbsp;: {insecables(s.sonde.motif)}</p>
						{/if}
						{#if s.etat.etat === 'en_panne'}
							<p class="panne">
								<a href={lienPannes(s.source)} target="_blank" rel="noopener">Suivre la panne (issues ouvertes)</a>
							</p>
						{/if}
						<dl>
							<dt>Attribution</dt>
							<dd>
								<a href={s.source.attribution.lien} target="_blank" rel="noopener">{s.source.attribution.texte}</a>
								<span class="licence">{s.source.attribution.licence}</span>
							</dd>
							<dt>Voie d’accès</dt>
							<dd>{libelleVoie(s.source)}</dd>
							{#if s.source.couverture}
								<dt>Mode</dt>
								<dd>{libelleMode(s.source.couverture.mode)}</dd>
							{/if}
							<dt>Communes</dt>
							<dd>{insecables(libelleCommunes(s, data.communes.length))}</dd>
							{#if s.source.limites}
								<dt>Limites</dt>
								<dd>{insecables(libelleLimites(s.source) ?? '')}</dd>
							{/if}
							{#if s.source.conseil}
								<dt>Donne</dt>
								<dd>{insecables(libelleDonne(s.source.conseil))}</dd>
							{/if}
							{#if s.source.voie_acces === 'cron'}
								<dt>Dernier import</dt>
								<dd class="quand">{importsCharge ? quand(dernierImport(imports, s.source)?.toISOString()) : '…'}</dd>
							{/if}
							<dt>Dernière sonde</dt>
							<dd class="quand">{charge ? quand(s.sonde?.derniere_sonde) : '…'}</dd>
							<dt>Dernier succès</dt>
							<dd class="quand">{charge ? quand(s.sonde?.dernier_succes) : '…'}</dd>
						</dl>
					</article>
				{/each}
			</section>

			{#if couverture.plateformes.length > 0}
				<section class="plateformes" aria-label="Sites des communes, par plateforme">
					{#each couverture.plateformes as p (p.id)}
						{@const issue = charge ? lienIssuePlateforme(p) : null}
						<article class="encart fiche" aria-labelledby="plateforme-{p.id}">
							<h2 id="plateforme-{p.id}">{insecables(libellePlateforme(p, charge))}</h2>
							{#if issue}
								<p class="panne"><a href={issue} target="_blank" rel="noopener">Suivre la panne (issue ouverte)</a></p>
							{/if}
							<details>
								<summary>
									<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
										<path d="m6 3.5 4.5 4.5L6 12.5" />
									</svg>
									Ses {p.communes.length} communes
								</summary>
								<ul>
									{#each communesTriees(p.communes) as c (c.source.id)}
										{@const commune = parBfs.get(c.bfs)}
										<li>
											<p class="nom">
												{#if commune}
													<a href={lienCommune(commune.slug)}>{commune.nom}</a>
												{:else}
													{c.source.nom_court}
												{/if}
											</p>
											<p class="paire" data-etat={charge ? c.paire.etat?.etat : undefined}>
												{insecables(libelleCellule([c], charge)[0])}
											</p>
											{#if c.paire.mode !== 'non_couvert'}
												<dl>
													<dt>Dernier import</dt>
													<dd class="quand">
														{importsCharge ? quand(dernierImport(imports, c.source)?.toISOString()) : '…'}
													</dd>
													<dt>Dernière sonde</dt>
													<dd class="quand">{charge ? quand(c.sonde?.derniere_sonde) : '…'}</dd>
												</dl>
											{/if}
											<p>
												<a href={c.source.attribution.lien} target="_blank" rel="noopener">
													Le conseil sur le site de la commune ›
												</a>
											</p>
										</li>
									{/each}
								</ul>
							</details>
						</article>
					{/each}
				</section>
			{/if}

			<section class="partie communes" aria-labelledby="titre-communes">
				<h2 id="titre-communes">Les {data.communes.length} communes</h2>
				<div class="outils">
					<label class="recherche">
						<span>Chercher une commune</span>
						<input type="search" bind:value={recherche} placeholder="Pully, Yverdon…" autocomplete="off" />
					</label>
					<p class="compte" aria-live="polite">
						{lignes.length === data.communes.length
							? `${lignes.length} communes`
							: `${lignes.length} sur ${data.communes.length}`}
					</p>
				</div>
				<table class="tableau">
					<thead>
						<tr>
							<th scope="col">Commune</th>
							{#each couverture.colonnes as couche (couche.id)}
								<th scope="col">{couche.nom}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each lignes as c (c.bfs)}
							<tr>
								<th scope="row"><a href={lienCommune(c.slug)}>{c.nom}</a></th>
								{#each couverture.colonnes as couche (couche.id)}
									{@const couvrantes = couverture.cellule(couche.id, c.bfs)}
									{@const libelles = libelleCellule(couvrantes, charge)}
									<td data-titre={couche.nom}>
										{#each libelles as libelle, i (i)}
											<span
												class="paire"
												class:non-couvert={!couvrantes[i] || couvrantes[i].paire.mode === 'non_couvert'}
												data-etat={charge ? couvrantes[i]?.paire.etat?.etat : undefined}
											>
												{insecables(libelle)}
											</span>
										{/each}
									</td>
								{/each}
							</tr>
						{:else}
							<tr>
								<td colspan={couverture.colonnes.length + 1} class="vide">Aucune commune ne correspond.</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		</div>
	</div>
</main>

<style>
	/* Les jetons, la base et l'en-tête sont communs aux pages Almanach (#lib/almanach). */

	/* L'état, partout sur la page : une marque devant son libellé. Disponible, un point d'encre ; en panne, un point
	   orange, le seul signal de la page ; surveillance interrompue ou inconnu, un anneau pâle. */
	.etat,
	.paire {
		--marque: 0.5rem;
	}
	[data-etat]::before {
		content: '';
		display: inline-block;
		width: var(--marque);
		height: var(--marque);
		margin-right: 0.45em;
		border-radius: 50%;
		background: var(--color-ink);
		vertical-align: 0.08em;
	}
	[data-etat='en_panne'] {
		color: var(--color-accent-2);
	}
	[data-etat='en_panne']::before {
		background: var(--color-accent);
	}
	[data-etat='surveillance_interrompue'],
	[data-etat='inconnu'],
	[data-etat='non_surveillee'] {
		color: var(--color-muted);
	}
	[data-etat='surveillance_interrompue']::before,
	[data-etat='inconnu']::before,
	[data-etat='non_surveillee']::before {
		border: var(--rule-bar) solid currentColor;
		background: none;
	}

	/* Les sources : une feuille chacune, un filet d'encre en tête, ses caractéristiques réglées ligne à ligne. */
	.encarts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
		gap: var(--space-lg);
		margin-top: var(--space-2xl);
	}
	.encart {
		padding: var(--space-lg);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
	}
	.encart h2 {
		font-size: var(--text-lg);
		line-height: 1.25;
	}
	.etat {
		margin-top: var(--space-xs);
		font-family: var(--font-display);
		font-size: var(--text-md);
		font-weight: 600;
		color: var(--color-ink);
	}
	.etat:not([data-etat]) {
		font-weight: 400;
		color: var(--color-muted);
	}
	.motif {
		margin-top: var(--space-2xs);
		font-size: var(--text-sm);
		color: var(--color-muted);
	}
	.panne {
		margin-top: var(--space-2xs);
		font-size: var(--text-sm);
	}
	dl {
		display: grid;
		grid-template-columns: max-content minmax(0, 1fr);
		margin: var(--space-md) 0 0;
		font-size: var(--text-sm);
		line-height: 1.45;
	}
	dt,
	dd {
		padding-block: var(--space-2xs);
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	dt {
		padding-right: var(--space-md);
		font-family: var(--font-display);
		font-size: var(--text-xs);
		color: var(--color-muted);
		/* Le libellé se cale sur la première ligne de sa valeur. */
		padding-top: calc(var(--space-2xs) + 0.1em);
	}
	dd {
		margin: 0;
		min-width: 0;
		overflow-wrap: break-word;
	}
	/* Les dates et heures en chiffres de machine, alignées. */
	.quand {
		font-family: var(--font-outlier);
		font-size: var(--text-xs);
		font-variant-numeric: tabular-nums;
		padding-top: calc(var(--space-2xs) + 0.1em);
	}
	.licence {
		display: block;
		font-size: var(--text-xs);
		color: var(--color-muted);
	}

	/* Une fiche par plateforme, sur toute la largeur : sa liste de communes se déplie au doigt. */
	.plateformes {
		display: grid;
		gap: var(--space-lg);
		margin-top: var(--space-lg);
	}
	.fiche summary {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		min-height: 44px;
		margin-top: var(--space-xs);
		cursor: pointer;
		list-style: none;
		font-family: var(--font-display);
		font-size: var(--text-md);
		font-weight: 600;
		color: var(--color-ink);
	}
	.fiche summary::-webkit-details-marker {
		display: none;
	}
	.fiche summary svg {
		flex: none;
		color: var(--color-accent);
		stroke-width: 2;
		transition: transform var(--dur-short) var(--ease-out);
	}
	.fiche details[open] summary svg {
		transform: rotate(90deg);
	}
	.fiche summary:hover {
		text-decoration: underline var(--rule-hair) var(--color-accent);
		text-underline-offset: 0.18em;
	}
	.fiche ul {
		list-style: none;
		margin: var(--space-xs) 0 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 16rem), 1fr));
		column-gap: var(--space-xl);
	}
	.fiche li {
		padding-block: var(--space-sm);
		border-top: var(--rule-hair) solid var(--color-rule);
		font-size: var(--text-sm);
		line-height: 1.45;
	}
	.fiche li p {
		margin: 0;
	}
	.fiche li .paire {
		margin-top: var(--space-2xs);
	}
	.fiche li dl {
		margin-top: var(--space-xs);
	}
	.fiche li a {
		display: inline-block;
		padding-block: var(--space-2xs);
	}
	.fiche .nom {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--text-md);
	}

	/* Les communes : un outil de recherche, puis la table du manuel, sur sa feuille. */
	.outils {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--space-sm) var(--space-lg);
		margin-top: var(--space-lg);
	}
	.recherche {
		display: flex;
		flex-direction: column;
		gap: var(--space-2xs);
		width: min(100%, 22rem);
		font-family: var(--font-display);
		font-size: var(--text-sm);
		color: var(--color-muted);
	}
	.recherche input {
		min-height: 44px;
		padding: var(--space-xs) var(--space-sm);
		border: 0;
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
		border-radius: 0;
		background: var(--color-sheet);
		color: var(--color-ink);
		font-family: var(--font-body);
		font-size: max(16px, var(--text-md));
	}
	.recherche input::placeholder {
		color: var(--color-muted);
	}
	.compte {
		margin: 0;
		font-family: var(--font-outlier);
		font-size: var(--text-sm);
		font-variant-numeric: tabular-nums;
		color: var(--color-muted);
	}
	.tableau {
		width: 100%;
		margin-top: var(--space-md);
		border-collapse: collapse;
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		font-size: var(--text-sm);
		line-height: 1.45;
	}
	.tableau th,
	.tableau td {
		padding: var(--space-sm);
		text-align: left;
		vertical-align: top;
		/* La page ne défile pas en largeur (almanach.css) : une colonne de trop se resserre plutôt que d'être coupée. */
		overflow-wrap: anywhere;
	}
	/* L'en-tête de la table reste sous la barre du site pendant qu'on parcourt les 300 lignes. Son filet est dessiné
	   par un fond, qui suit la cellule collée, quand une bordure resterait sur place. */
	.tableau thead th {
		position: sticky;
		top: var(--header-h);
		z-index: 1;
		padding-block: var(--space-xs);
		background:
			linear-gradient(var(--color-rule-2), var(--color-rule-2)) no-repeat left bottom / 100% var(--rule-bar),
			var(--color-sheet);
		font-family: var(--font-display);
		font-weight: 500;
		color: var(--color-muted);
	}
	.tableau tbody tr {
		/* La ligne entière mène à la fiche : le lien du nom s'étend sur toute la ligne. */
		position: relative;
		transition: background-color var(--dur-short) var(--ease-out);
	}
	.tableau tbody tr + tr {
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.tableau tbody tr:hover {
		background: var(--color-paper);
	}
	.tableau tbody th {
		width: 28%;
		font-family: var(--font-display);
		font-weight: 600;
	}
	.tableau tbody th a {
		text-decoration: none;
	}
	.tableau tbody tr:hover th a {
		text-decoration: underline var(--rule-hair) var(--color-accent);
	}
	.tableau tbody th a::after {
		content: '';
		position: absolute;
		inset: 0;
	}
	.tableau tbody th a:focus-visible {
		outline: none;
	}
	.tableau tbody th a:focus-visible::after {
		outline: var(--rule-bar) solid var(--color-focus);
		outline-offset: calc(-1 * var(--rule-bar));
	}
	/* Plusieurs sources qui couvrent la commune : une ligne chacune. */
	.paire {
		display: block;
	}
	.non-couvert {
		color: var(--color-muted);
	}
	.vide {
		color: var(--color-muted);
	}

	@media (max-width: 40rem) {
		.encart {
			margin-inline: calc(-1 * var(--space-xs));
			padding: var(--space-md) var(--space-sm);
		}
		.recherche {
			width: 100%;
		}
		/* La table devient une fiche par commune, chaque couche précédée de son nom, sur la même ligne. */
		.tableau,
		.tableau tbody,
		.tableau tr,
		.tableau th,
		.tableau td {
			display: block;
			width: auto;
		}
		.tableau {
			margin-inline: calc(-1 * var(--space-xs));
		}
		.tableau thead {
			display: none;
		}
		.tableau tbody tr {
			padding-block: var(--space-xs);
		}
		.tableau tbody th,
		.tableau td {
			width: auto;
			padding: var(--space-3xs) var(--space-sm);
		}
		.tableau tbody th {
			font-size: var(--text-md);
		}
		.tableau td[data-titre] {
			display: grid;
			grid-template-columns: 5.5rem minmax(0, 1fr);
			column-gap: var(--space-sm);
		}
		.tableau td[data-titre]::before {
			content: attr(data-titre);
			grid-row: 1 / span 9;
			font-family: var(--font-display);
			font-size: var(--text-xs);
			font-weight: 500;
			color: var(--color-muted);
			padding-top: 0.15em;
		}
	}

	/* Quand l'état des sources arrive dans le navigateur, chaque marque s'allume une fois. Sans JavaScript, à
	   l'impression ou quand le mouvement est réduit, elle est simplement là. */
	@media screen and (prefers-reduced-motion: no-preference) {
		.etat[data-etat] {
			animation: arrive 0.5s var(--ease-out) both;
		}
		.etat[data-etat]::before {
			animation: allume 0.6s var(--ease-out) 0.1s both;
		}
	}
	@keyframes arrive {
		from {
			opacity: 0;
			transform: translateY(0.3em);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes allume {
		0% {
			opacity: 0;
			transform: scale(0.2);
		}
		60% {
			opacity: 1;
			transform: scale(1.5);
		}
		100% {
			opacity: 1;
			transform: none;
		}
	}

	@media print {
		.encart,
		.tableau {
			background: none;
		}
		.encart {
			break-inside: avoid;
			padding-inline: 0;
		}
		.recherche {
			display: none;
		}
		.tableau thead th {
			position: static;
			background: none;
			border-bottom: var(--rule-bar) solid var(--color-rule-2);
		}
		.tableau tr {
			break-inside: avoid;
		}
	}
</style>
