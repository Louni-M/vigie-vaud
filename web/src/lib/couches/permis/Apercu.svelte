<script lang="ts">
	/*
	 * Aperçu du dossier ouvert, en bas de la carte sur téléphone : la carte de dossier, qui montre sa fiche quand
	 * on la touche. Le dossier est le plus souvent déjà en mémoire : le registre vient de le chercher pour trouver
	 * sa commune.
	 */
	import { untrack } from 'svelte';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Dossier } from '#lib/types.js';
	import { permis, type Parametres } from './donnees.svelte.js';

	let { ctx, voir }: { ctx: Contexte<Parametres>; voir: () => void } = $props();

	const id = Number(untrack(() => ctx.ouvert?.element));

	const enMemoire = untrack(() => permis.actifs.find((x) => x.id === id));
	let d = $state<Dossier | null | undefined>(enMemoire);
	if (!enMemoire)
		permis.fiche(id).then(
			(r) => (d = r ?? null),
			() => (d = null)
		);
</script>

{#if d}
	<DossierCarte {d} onclick={voir} />
{:else}
	<!-- Dossier pas encore chargé, ou que le service du canton n'a pas rendu : la fiche dira pourquoi. -->
	<button class="attente" type="button" onclick={voir}>
		<strong>Dossier n° {id}</strong>
		<span>Voir la fiche ›</span>
	</button>
{/if}

<style>
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
	.attente span {
		font-size: 13px;
		color: var(--accent);
	}
</style>
