<script lang="ts">
	/*
	 * Onglet Conseil de la fiche commune. Le registre a déjà rendu les badges et, pour une commune que la couche ne
	 * couvre pas, « Non couvert » en tête ; il remonte l'onglet quand on change de commune. Pour une commune dont le
	 * conseil est couvert, lu dans `conseils/index.json` : le nom du conseil (et, s'il ne donne que ses Séances,
	 * « OpenParlData ne donne que ses séances »), l'en-tête de séance, « Objets récents », « Séances passées ».
	 * « Au Grand Conseil » viendra après, pour toutes les communes. Une ligne d'Objet ou de Séance, et un point de
	 * l'en-tête lié à un Objet, ouvrent l'élément par le registre, dans cet onglet (`?c=`).
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Commune } from '#lib/types.js';
	import { conseils } from './donnees.js';
	import { coucheConseils } from './index.js';
	import ObjetsRecents from './ObjetsRecents.svelte';
	import SeancesPassees from './SeancesPassees.svelte';
	import TeteSeance from './TeteSeance.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	// Le registre ne monte l'onglet que pour une commune ouverte, et le remonte pour une autre.
	const commune = untrack(() => ctx.commune) as Commune;

	let lecture = $state(conseils.index());

	const ouvrir = (cle: string) => ctx.ouvrir({ couche: coucheConseils.id, element: cle });
</script>

{#await lecture}
	<p class="note" aria-busy="true">Lecture du conseil…</p>
{:then index}
	{@const conseil = index.conseils.find((c) => c.commune === commune.bfs)}
	{#if conseil}
		<h3>{conseil.nom}</h3>
		{#if !conseil.donne.includes('objets')}<p class="note">OpenParlData ne donne que ses séances.</p>{/if}
		<TeteSeance {conseil} {ouvrir} />
		{#if conseil.donne.includes('objets')}<ObjetsRecents {conseil} {ouvrir} />{/if}
		{#if conseil.donne.includes('seances')}<SeancesPassees {conseil} {ouvrir} />{/if}
	{/if}
{:catch}
	<p class="erreur" role="alert">
		Le conseil n’a pas pu être chargé.
		<button class="bouton secondaire petit" type="button" onclick={() => (lecture = conseils.index())}>
			Réessayer
		</button>
	</p>
{/await}

<style>
	h3 {
		margin: 0 0 2px;
		font-size: 16px;
	}
	.note {
		margin: 2px 0 6px;
		font-size: 13px;
		color: var(--muted);
	}
	.erreur {
		margin: 0;
		color: var(--erreur);
	}
	.petit {
		margin-left: 6px;
		padding: 6px 10px;
		font-size: 13px;
	}
	@media (pointer: coarse) {
		.petit {
			min-height: 44px;
		}
	}
</style>
