<script lang="ts">
	// PROTOTYPE (ticket #45) : fiche factice d'un objet ou d'une séance, dans l'onglet Conseil de sa commune.
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { element, dateDe, nomConseil } from './donnees.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	const x = element(untrack(() => ctx.ouvert?.element) ?? '');
	const nom = (s: string) => ctx.communes.find((c) => c.slug === s)?.nom ?? s;
	const jour = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
</script>

{#if x}
	<p class="type">{x.type} · {nomConseil(x, nom)}</p>
	<h3>{x.titre}</h3>
	<p>{x.sorte === 'seance' ? 'Le' : 'Déposé le'} {jour.format(dateDe(x))}</p>
	{#if x.auteur}<p>Auteur·e : {x.auteur}</p>{/if}
	{#if x.statut}<p>Statut : {x.statut}</p>{/if}
	{#if x.ordreDuJour}
		<p>Ordre du jour :</p>
		<ol>{#each x.ordreDuJour as o (o)}<li>{o}</li>{/each}</ol>
	{/if}
	{#if x.conseil === null && x.communes.length}
		<p class="cite">Communes citées : {x.communes.map(nom).join(', ')}</p>
	{/if}
	<p class="source">Source: OpenParlData.ch (données fictives du prototype)</p>
{:else}
	<p>Élément inconnu.</p>
{/if}

<style>
	.type { font-size: 13px; color: #7a3e9d; font-weight: 600; margin: 0; }
	h3 { margin: 4px 0 10px; font-size: 17px; }
	p { margin: 4px 0; font-size: 14px; }
	.cite { margin-top: 10px; }
	.source { margin-top: 14px; font-size: 12px; color: var(--muted); }
</style>
