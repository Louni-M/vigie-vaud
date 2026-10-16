<script lang="ts">
	// PROTOTYPE (ticket #51) : l'onglet Conseil de la fiche commune, une mise en page par variante.
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Commune } from '#lib/types.js';
	import { charger, conseils } from './donnees.svelte.js';
	import { proto } from './proto.svelte.js';
	import OngletA from './OngletA.svelte';
	import OngletB from './OngletB.svelte';
	import OngletC from './OngletC.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	const commune = untrack(() => ctx.commune) as Commune;
	charger(untrack(() => ctx.communes));
	const ouvrir = (id: string) => ctx.ouvrir({ couche: 'conseils', element: id });
	const nom = (s: string) => ctx.communes.find((c) => c.slug === s)?.nom ?? s;
</script>

{#if conseils.erreur}
	<p class="erreur">OpenParlData n’a pas répondu : {conseils.erreur}</p>
{:else if !conseils.charge}
	<p class="attente">Lecture d’OpenParlData…</p>
{:else if proto.variante === 'A'}
	<OngletA {commune} {ouvrir} {nom} />
{:else if proto.variante === 'B'}
	<OngletB {commune} {ouvrir} {nom} />
{:else}
	<OngletC {commune} {ouvrir} {nom} />
{/if}

<style>
	.attente { color: var(--muted); }
	.erreur { color: var(--erreur); }
</style>
