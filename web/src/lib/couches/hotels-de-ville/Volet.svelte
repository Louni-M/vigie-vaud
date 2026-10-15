<script lang="ts">
	/* Volet Hôtels de ville : ce que montre un marqueur. L'interrupteur est remplacé par « permanente » (registre). */
	import type { Contexte } from '#lib/registre/types.js';

	let {}: { ctx: Contexte<undefined> } = $props();
</script>

<p>
	Un marqueur par commune, sur le siège de son administration communale. Quand l’adresse du siège n’a pas pu être
	retrouvée, il est placé sur un point de la commune en terre ferme, et sa position est dite approximative.
	Un clic sur un marqueur ouvre la fiche de la commune.
</p>

<style>
	p {
		margin: 0;
		line-height: 1.45;
	}
</style>
