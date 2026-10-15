<script lang="ts">
	// PROTOTYPE (ticket #45) : un élément sans commune, déplié dans le fil (il n'a pas de fiche commune où s'ouvrir).
	import type { Entree } from './entrees.svelte.js';
	let { e }: { e: Entree } = $props();
	const jour = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long' });
</script>

<div class="deplie">
	<p>{e.conseil?.sorte === 'seance' ? 'Le' : 'Déposé le'} {jour.format(e.date)}{#if e.conseil?.auteur} · {e.conseil.auteur}{/if}</p>
	{#if e.conseil?.statut}<p>Statut : {e.conseil.statut}</p>{/if}
	{#if e.conseil?.ordreDuJour}
		<ol>{#each e.conseil.ordreDuJour as o (o)}<li>{o}</li>{/each}</ol>
	{/if}
	<p><a href="https://openparldata.ch" target="_blank" rel="noopener">Voir sur OpenParlData ↗</a></p>
</div>

<style>
	.deplie { padding: 2px 8px 10px 32px; font-size: 13px; }
	p { margin: 3px 0; }
	ol { margin: 4px 0; padding-left: 18px; }
</style>
