<script lang="ts">
	// PROTOTYPE (tickets #45 et #51) : un élément sans commune, déplié dans le fil (il n'a pas de fiche commune où s'ouvrir).
	import { detailsDe } from '#lib/couches/conseils-prototype/donnees.svelte.js';
	import type { Entree } from './entrees.svelte.js';
	let { e }: { e: Entree } = $props();
	const jour = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long' });
	const x = $derived(e.conseil);
</script>

<div class="deplie">
	<p>{x?.sorte === 'seance' ? 'Le' : 'Déposé le'} {jour.format(e.date)}{#if x?.auteurs.length} · {x.auteurs.map((a) => a.nom).join(', ')}{/if}</p>
	{#if x?.statut}<p>Statut : {x.statut}</p>{/if}
	{#if x?.sorte === 'seance'}
		{#await detailsDe(x) then d}
			<ol>{#each d.ordreDuJour.slice(0, 12) as p, i (i)}<li>{p.titre}</li>{/each}</ol>
		{/await}
	{/if}
	{#if x?.url}<p><a href={x.url} target="_blank" rel="noopener">Voir sur vd.ch ↗</a></p>{/if}
</div>

<style>
	.deplie { padding: 2px 8px 10px 32px; font-size: 13px; }
	p { margin: 3px 0; }
	ol { margin: 4px 0; padding-left: 18px; }
</style>
