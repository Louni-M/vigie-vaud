<script lang="ts">
	// PROTOTYPE jetable (ticket #7) : recherche de commune réduite au strict nécessaire.
	import type { Proto } from '../proto.svelte.js';
	let { p }: { p: Proto } = $props();
	let texte = $state('');
	function choisir() {
		const c = p.communes.find((c) => c.nom.toLowerCase() === texte.trim().toLowerCase());
		if (c) {
			p.ouvrirCommune(c);
			texte = '';
		}
	}
</script>

<input
	class="chercher"
	type="search"
	list="proto-communes"
	placeholder="Commune, adresse, n° CAMAC…"
	bind:value={texte}
	onchange={choisir}
/>
<datalist id="proto-communes">
	{#each p.communes as c (c.slug)}<option value={c.nom}></option>{/each}
</datalist>

<style>
	.chercher {
		width: 100%;
		padding: 9px 12px;
		border-radius: 8px;
		border: 1px solid var(--line);
		font: inherit;
		font-size: 14px;
		background: var(--surface);
	}
</style>
