<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51) : la fiche d'un objet ou d'une séance, la même dans toutes les variantes. Étapes,
	 * documents et ordre du jour sont lus à l'ouverture.
	 */
	import { dateDe, detailsDe, jourCourt, jourLong, nomConseil, type ElementConseil } from './donnees.svelte.js';

	let { x, ouvrir, nom }: { x: ElementConseil; ouvrir: (id: string) => void; nom: (s: string) => string } = $props();
	const lien = (u: string) => new URL(u).hostname.replace(/^www\./, '');
</script>

<p class="type">{x.type}{x.numero ? ` ${x.numero}` : ''} · {nomConseil(x)}</p>
<h3>{x.titre}</h3>
<dl>
	<dt>{x.sorte === 'seance' ? 'Date' : 'Déposé le'}</dt>
	<dd>{jourLong.format(dateDe(x))}{x.age < 0 ? ' (à venir)' : ''}</dd>
	{#if x.auteurs.length}
		<dt>Auteur·e{x.auteurs.length > 1 ? '·s' : ''}</dt>
		<dd>{x.auteurs.map((a) => a.nom + (a.parti ? ` (${a.parti})` : '')).join(', ')}</dd>
	{/if}
	{#if x.statut}
		<dt>Statut</dt>
		<dd>{x.statut}</dd>
	{/if}
	{#if x.conseil === null && x.sorte === 'objet'}
		<dt>Communes</dt>
		<dd>
			{#if x.communes.length}{x.communes.map(nom).join(', ')}{:else}aucune nommée{/if}
			<span class="aide">rattachement automatique d’après le titre · <a href="#signaler" onclick={(e) => e.preventDefault()}>signaler une erreur</a></span>
		</dd>
	{/if}
</dl>

{#await detailsDe(x)}
	<p class="note">Lecture des détails…</p>
{:then d}
	{#if d.etapes.length}
		<h4>Étapes</h4>
		<ol class="etapes">
			{#each d.etapes as e, i (i)}<li><span class="d">{e.date ? jourCourt.format(new Date(`${e.date}T12:00:00`)) : '–'}</span> {e.titre}</li>{/each}
		</ol>
	{/if}
	{#if d.documents.length}
		<h4>Documents</h4>
		<ul class="docs">
			{#each d.documents as doc (doc.url)}<li><a href={doc.url} target="_blank" rel="noopener">{doc.nom}</a> <span class="d">{doc.categorie}{doc.date ? ` · ${jourCourt.format(new Date(`${doc.date}T12:00:00`))}` : ''}</span></li>{/each}
		</ul>
	{/if}
	{#if x.sorte === 'seance'}
		<h4>Ordre du jour</h4>
		{#if d.ordreDuJour.length}
			<ol class="odj">
				{#each d.ordreDuJour as p, i (i)}
					<li>
						{#if p.categorie && p.categorie !== d.ordreDuJour[i - 1]?.categorie}<span class="cat">{p.categorie}</span>{/if}
						{#if p.objet}<button type="button" class="point" onclick={() => ouvrir(p.objet!)}>{p.titre}</button>{:else}{p.titre}{/if}
						{#if p.resultat}<span class="d"> · {p.resultat}</span>{/if}
					</li>
				{/each}
			</ol>
		{:else}
			<p class="note">Pas encore publié.</p>
		{/if}
	{/if}
{:catch}
	<p class="note">Détails indisponibles.</p>
{/await}

{#if x.url}<p class="externe"><a href={x.url} target="_blank" rel="noopener">Voir sur {lien(x.url)} ›</a></p>{/if}
<p class="source">Source: OpenParlData.ch</p>

<style>
	.type { font-size: 13px; color: #7a3e9d; font-weight: 600; margin: 0; }
	h3 { margin: 4px 0 10px; font-size: 17px; line-height: 1.3; }
	dl { display: grid; grid-template-columns: max-content 1fr; gap: 3px 10px; margin: 0 0 8px; font-size: 14px; }
	dt { color: var(--muted); }
	dd { margin: 0; }
	.aide { display: block; font-size: 12px; color: var(--muted); }
	h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 14px 0 4px; }
	.etapes { list-style: none; margin: 0; padding: 0 0 0 12px; border-left: 2px solid #d9c8e4; font-size: 13px; }
	.etapes li { margin: 3px 0; }
	.d { color: var(--muted); font-size: 12px; }
	.docs { margin: 0; padding-left: 18px; font-size: 13px; }
	.odj { margin: 0; padding-left: 22px; font-size: 13px; }
	.odj li { margin: 3px 0; }
	.cat { display: block; margin-top: 8px; font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; }
	.point { padding: 0; border: 0; background: none; font: inherit; color: var(--accent); text-align: left; cursor: pointer; text-decoration: underline; }
	.note { font-size: 13px; color: var(--muted); }
	.externe { margin-top: 14px; font-size: 14px; }
	.source { margin-top: 6px; font-size: 12px; color: var(--muted); }
</style>
