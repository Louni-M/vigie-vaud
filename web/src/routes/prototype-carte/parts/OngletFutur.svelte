<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : contenu fictif des onglets des couches à venir, pour juger la disposition.
	import type { Onglet } from '../proto.svelte.js';
	let { onglet, nom }: { onglet: Onglet; nom: string } = $props();
	const lignes: Record<string, string[]> = {
		conseil: ['Séance du conseil communal · 21 octobre', 'Préavis 2026/14 : rénovation du collège', 'Interpellation : sécurité du chemin de l’école'],
		presse: ['Le nouveau giratoire inauguré', 'La piscine fermera plus tôt cet hiver', 'Budget 2027 : une hausse d’impôt évitée'],
		meteo: ['Maintenant : 12 °C, nuageux', 'Demain : 15 °C / 6 °C, averses', 'Après-demain : 17 °C / 8 °C, ensoleillé']
	};
</script>

<div class="futur">
	<p class="maquette">Maquette : la couche {nom} n’existe pas encore (après J0).</p>
	<ul>{#each lignes[onglet] ?? [] as l (l)}<li>{l}</li>{/each}</ul>
</div>

<style>
	.maquette {
		font-size: 12px;
		color: #8a5a00;
		background: #fff6e0;
		padding: 4px 8px;
		border-radius: 6px;
		margin: 0 0 8px;
	}
	ul {
		margin: 0;
		padding-left: 18px;
		font-size: 14px;
		line-height: 1.7;
	}
</style>
