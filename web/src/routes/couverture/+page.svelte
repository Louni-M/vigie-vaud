<script lang="ts">
	import {
		dateHeure,
		libelleCellule,
		libelleCommunes,
		libelleEtat,
		libelleLimites,
		libelleMode
	} from '#lib/couverture.js';
	import { couvertureChargee, couvertureCourante } from '#lib/couverture-courante.svelte.js';
	import { lienPannes } from '#lib/etat-sources.js';
	import { dernierImport } from '#lib/imports-conseils.js';
	import { importsCharges, importsCourants } from '#lib/imports-courants.svelte.js';
	import { canonique } from '#lib/indexation.js';
	import { normaliser } from '#lib/labels.js';
	import { lienCommune } from '#lib/registre/liens.js';
	import { libelleDonne, libelleVoie } from '#lib/sources.js';
	import type { PageProps } from './$types';

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
</script>

<svelte:head>
	<title>Couverture – Vigie Vaud</title>
	<meta
		name="description"
		content="Pour chaque couche de Vigie Vaud et chaque commune vaudoise : comment les données sont obtenues, et si leur source répond."
	/>
	<link rel="canonical" href={canonique('/couverture')} />
</svelte:head>

<main class="page">
	<h1>Couverture</h1>
	<p class="intro">
		Pour chaque couche et chaque commune : le <strong>mode</strong> (les données viennent d’une API, sont scrapées,
		ou la commune n’est pas couverte) et l’<strong>état</strong> de la source, vérifié toutes les 30 minutes par une
		sonde. Les conseils sont importés une fois par jour ; une sonde vérifie que leur source répond.
	</p>

	<section class="encarts" aria-label="Sources">
		{#each couverture.sources as s (s.source.id)}
			<article class="encart" aria-labelledby="source-{s.source.id}">
				<h2 id="source-{s.source.id}">{s.source.nom}</h2>
				<p class="etat" data-etat={charge ? s.etat.etat : undefined} aria-live="polite">
					{charge ? libelleEtat(s.etat) : 'État en cours de chargement…'}
				</p>
				{#if s.etat.etat === 'en_panne' && s.sonde?.motif}
					<p class="motif">Dernier échec : {s.sonde.motif}</p>
				{/if}
				{#if s.etat.etat === 'en_panne'}
					<p><a href={lienPannes(s.source)} target="_blank" rel="noopener">Suivre la panne (issues ouvertes)</a></p>
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
					<dd>{libelleCommunes(s, data.communes.length)}</dd>
					{#if s.source.limites}
						<dt>Limites</dt>
						<dd>{libelleLimites(s.source)}</dd>
					{/if}
					{#if s.source.conseil}
						<dt>Donne</dt>
						<dd>{libelleDonne(s.source.conseil)}</dd>
					{/if}
					{#if s.source.voie_acces === 'cron'}
						<dt>Dernier import</dt>
						<dd>{importsCharge ? quand(dernierImport(imports, s.source)?.toISOString()) : '…'}</dd>
					{/if}
					<dt>Dernière sonde</dt>
					<dd>{charge ? quand(s.sonde?.derniere_sonde) : '…'}</dd>
					<dt>Dernier succès</dt>
					<dd>{charge ? quand(s.sonde?.dernier_succes) : '…'}</dd>
				</dl>
			</article>
		{/each}
	</section>

	<section class="communes" aria-labelledby="titre-communes">
		<h2 id="titre-communes">Les {data.communes.length} communes</h2>
		<label class="recherche">
			<span>Chercher une commune</span>
			<input type="search" bind:value={recherche} placeholder="Pully, Yverdon…" autocomplete="off" />
		</label>
		<p class="compte" aria-live="polite">
			{lignes.length === data.communes.length ? `${lignes.length} communes` : `${lignes.length} sur ${data.communes.length}`}
		</p>
		<div class="tableau">
			<table>
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
								<td>
									{#each libelles as libelle, i (i)}
										<span class="paire" data-etat={charge ? couvrantes[i]?.paire.etat?.etat : undefined}>
											{libelle}
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
		</div>
	</section>
</main>

<style>
	.intro {
		color: var(--muted);
		max-width: 65ch;
	}
	.encarts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 12px;
		margin: 20px 0 32px;
	}
	.encart {
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 10px;
		padding: 14px 16px;
	}
	.encart h2 {
		margin: 0 0 6px;
		font-size: 17px;
	}
	.encart p {
		margin: 4px 0;
	}
	.etat {
		font-weight: 600;
	}
	[data-etat='disponible'] {
		color: #1d6b3a;
	}
	[data-etat='en_panne'] {
		color: var(--erreur);
	}
	[data-etat='surveillance_interrompue'],
	[data-etat='inconnu'] {
		color: var(--enquete-texte);
	}
	/* Plusieurs sources qui couvrent la commune : une ligne chacune. */
	.paire {
		display: block;
	}
	.motif {
		font-size: 14px;
		color: var(--muted);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 4px 12px;
		margin: 10px 0 0;
		font-size: 14px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	.licence {
		display: block;
		font-size: 12px;
		color: var(--muted);
	}
	.communes h2 {
		font-size: 19px;
	}
	.recherche {
		display: flex;
		flex-direction: column;
		gap: 4px;
		max-width: 360px;
		font-size: 14px;
	}
	.recherche input {
		font: inherit;
		font-size: 16px;
		min-height: 44px;
		padding: 8px 12px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--surface);
		color: var(--text);
	}
	.compte {
		font-size: 13px;
		color: var(--muted);
	}
	.tableau {
		overflow-x: auto;
		background: var(--surface);
		border: 1px solid var(--line);
		border-radius: 10px;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 14px;
	}
	th,
	td {
		padding: 10px 14px;
		text-align: left;
		border-bottom: 1px solid var(--line);
	}
	thead th {
		background: var(--surface-2);
		font-size: 13px;
	}
	tbody tr {
		/* La ligne entière mène à la fiche : le lien du nom s'étend sur toute la ligne. */
		position: relative;
	}
	tbody tr:hover {
		background: var(--surface-2);
	}
	tbody tr:last-child > * {
		border-bottom: 0;
	}
	tbody th {
		font-weight: 500;
	}
	tbody th a {
		text-decoration: none;
	}
	tbody th a::after {
		content: '';
		position: absolute;
		inset: 0;
	}
	tbody th a:focus-visible {
		outline: none;
	}
	tbody th a:focus-visible::after {
		outline: 3px solid var(--focus);
		outline-offset: -3px;
	}
	.vide {
		color: var(--muted);
	}
</style>
