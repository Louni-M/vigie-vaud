<script lang="ts">
	/*
	 * Aperçu de la restriction ouverte, en bas de la carte sur téléphone : sa carte (sorte, communes, période,
	 * échéance, remarque), qui mène à la vue Fiche par « Voir la fiche › ». La restriction est le plus souvent déjà
	 * en mémoire : la couche l'a chargée, ou le registre vient de la chercher pour trouver sa commune.
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { routes, type Restriction } from './donnees.svelte.js';
	import RestrictionCarte from './RestrictionCarte.svelte';

	let { ctx, voir }: { ctx: Contexte<undefined>; voir: () => void } = $props();

	const id = Number(untrack(() => ctx.ouvert?.element));

	let trouvee = $state.raw<Restriction | null>(null);
	routes.restriction(id).then(
		(r) => (trouvee = r),
		() => {}
	);
	// Celle de la couche quand elle est chargée : elle a ses communes dès que les limites sont là.
	const r = $derived(routes.restrictions.find((x) => x.id === id && x.communes) ?? trouvee);
</script>

{#if r}
	<RestrictionCarte {r} onclick={voir}><span class="voir">Voir la fiche ›</span></RestrictionCarte>
{:else}
	<!-- Restriction pas encore chargée, ou que la DGMR n'a pas rendue : la fiche dira pourquoi. -->
	<button class="attente" type="button" onclick={voir}>
		<strong>Restriction de circulation</strong>
		<span class="voir">Voir la fiche ›</span>
	</button>
{/if}

<style>
	.voir {
		font-size: 14px;
		font-weight: 600;
		color: var(--accent);
	}
	.attente {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		width: 100%;
		padding: 10px 12px;
		border: 1px solid var(--line);
		border-radius: 10px;
		background: var(--surface);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
</style>
