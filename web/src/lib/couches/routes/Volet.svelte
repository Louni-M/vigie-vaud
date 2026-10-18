<script lang="ts">
	/*
	 * Volet Routes : sous l'interrupteur, le badge et l'attribution du registre, l'échec de la DGMR s'il y en a un,
	 * avec « Réessayer ». Les puces par sorte et la liste de la zone visible viendront ensuite.
	 */
	import EchecSource from '#lib/components/EchecSource.svelte';
	import type { Contexte } from '#lib/registre/types.js';

	let {}: { ctx: Contexte<undefined> } = $props();
</script>

<EchecSource source="dgmr-restrictions" message="Les restrictions de circulation n’ont pas pu être chargées" />
