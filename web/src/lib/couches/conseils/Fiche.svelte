<script lang="ts">
	/*
	 * Fiche d'un Objet ou d'une Séance ouvert, dans l'onglet Conseil de sa commune ou dans la fiche du Grand Conseil :
	 * le registre a rendu le fil « Conseils › POS25/115 » au-dessus, et la remonte pour un autre élément. Lue dans le
	 * fichier d'archive de l'élément, déjà en mémoire le plus souvent : le registre vient de le lire pour trouver ses
	 * fiches.
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { messageIntrouvable } from './cles.js';
	import { conseils } from './donnees.js';
	import { coucheConseils } from './index.js';
	import FicheObjet from './FicheObjet.svelte';
	import FicheSeance from './FicheSeance.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	const cle = untrack(() => ctx.ouvert?.element) ?? '';
	const ouvrir = (c: string) => ctx.ouvrir({ couche: coucheConseils.id, element: c });

	let lecture = $state(conseils.element(cle));
</script>

{#await lecture}
	<p class="note" aria-busy="true">Lecture de l’archive…</p>
{:then element}
	{#if !element}
		<p>{messageIntrouvable(cle)}</p>
	{:else if 'ordre_du_jour' in element}
		<FicheSeance {cle} seance={element} {ouvrir} />
	{:else}
		<FicheObjet {cle} objet={element} communes={ctx.communes} />
	{/if}
{:catch}
	<p class="erreur" role="alert">
		L’archive n’a pas pu être lue.
		<button class="bouton secondaire petit" type="button" onclick={() => (lecture = conseils.element(cle))}>
			Réessayer
		</button>
	</p>
{/await}

<style>
	.note {
		margin: 0;
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
