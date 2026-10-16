<script lang="ts">
	/*
	 * Fiche d'une Séance : son nom composé (« Séance du mardi 6 octobre 2026 »), puis l'ordre du jour par catégorie,
	 * avec le résultat de chaque point ; un point lié à un Objet ouvre cet Objet. Puis « Voir sur … › » et la source.
	 */
	import type { Seance } from '#lib/schema.js';
	import { lireCle, nomConseil } from './cles.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { nomSeance, ordreDuJour, siteDuLien } from './lignes.js';
	import Source from './SourceElement.svelte';

	let { cle, seance, ouvrir }: { cle: string; seance: Seance; ouvrir: (cle: string) => void } = $props();

	const conseil = $derived(nomConseil(lireCle(cle)?.conseil ?? ''));
	const groupes = $derived(ordreDuJour(seance.ordre_du_jour));
</script>

<article class="fiche" style:--c={COULEUR_CONSEILS}>
	<p class="type"><span class="pastille" aria-hidden="true"></span>Séance{conseil ? ` · ${conseil}` : ''}</p>
	<h3>{nomSeance(seance.date)}</h3>

	<h4>Ordre du jour</h4>
	{#if groupes.length}
		{#each groupes as g, i (i)}
			{#if g.categorie}<p class="categorie">{g.categorie}</p>{/if}
			<ol>
				{#each g.points as p, j (j)}
					<li>
						{#if p.numero}<span class="numero">{p.numero}.</span>{/if}
						{#if p.objet}
							{@const objet = p.objet}
							<button type="button" class="point" onclick={() => ouvrir(objet)}>{p.titre}</button>
						{:else}
							{p.titre}
						{/if}
						{#if p.resultat}<span class="resultat"> · {p.resultat}</span>{/if}
					</li>
				{/each}
			</ol>
		{/each}
	{:else}
		<p class="note">Ordre du jour pas encore publié.</p>
	{/if}

	{#if seance.lien}
		<p class="externe"><a href={seance.lien} target="_blank" rel="noopener">Voir sur {siteDuLien(seance.lien)} ›</a></p>
	{/if}
	<Source />
</article>

<style>
	.fiche {
		display: grid;
		gap: 6px;
	}
	.type {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0;
		font-size: 13px;
		font-weight: 600;
		color: var(--c);
	}
	.pastille {
		flex: none;
		width: 10px;
		height: 10px;
		box-sizing: border-box;
		border-radius: 50%;
		border: 2px solid var(--c);
	}
	h3 {
		margin: 0;
		font-size: 18px;
		line-height: 1.3;
	}
	h4 {
		margin: 8px 0 0;
		font-size: 12px;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.categorie {
		margin: 6px 0 0;
		font-size: 13px;
		font-weight: 700;
	}
	ol {
		margin: 0;
		padding-left: 0;
		list-style: none;
		font-size: 13px;
	}
	li {
		margin: 4px 0;
	}
	.numero {
		margin-right: 4px;
		color: var(--muted);
	}
	.point {
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: var(--accent);
		text-align: left;
		text-decoration: underline;
		cursor: pointer;
	}
	.resultat {
		font-size: 12px;
		color: var(--muted);
	}
	.note {
		margin: 0;
		font-size: 13px;
		color: var(--muted);
	}
	.externe {
		margin: 8px 0 0;
		font-size: 14px;
	}
</style>
