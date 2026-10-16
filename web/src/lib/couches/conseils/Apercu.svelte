<script lang="ts">
	/*
	 * Aperçu de l'Objet ou de la Séance ouvert, en bas de la carte sur téléphone : « Motion · Conseil communal de
	 * Lausanne · 29 sept. », le titre, puis « Lausanne · Voir la fiche › », le nom de la fiche où il est ouvert.
	 * L'élément est déjà en mémoire le plus souvent : le registre vient de lire son fichier d'archive pour trouver
	 * ses fiches.
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Objet, Seance } from '#lib/schema.js';
	import { apercuElement } from './apercu.js';
	import { conseils } from './donnees.js';
	import { COULEUR_CONSEILS } from './index.js';

	let { ctx, voir }: { ctx: Contexte<undefined>; voir: () => void } = $props();

	const cle = untrack(() => ctx.ouvert?.element) ?? '';
	let element = $state<Objet | Seance | null>(null);
	conseils.element(cle).then(
		(e) => (element = e),
		() => (element = null)
	);

	const texte = $derived(apercuElement(cle, element));
	const fiche = $derived(ctx.commune?.nom ?? ctx.fiche?.nom ?? '');
</script>

<button class="apercu-element" type="button" style:--c={COULEUR_CONSEILS} onclick={voir}>
	<span class="meta">{texte.meta}</span>
	<strong class="titre">{texte.titre}</strong>
	<span class="fiche"><span class="nom">{fiche}</span> · <span class="voir">Voir la fiche ›</span></span>
</button>

<style>
	.apercu-element {
		display: grid;
		gap: 3px;
		width: 100%;
		padding: 10px 14px 12px;
		border: 0;
		border-left: 4px solid var(--c);
		border-radius: 10px;
		background: var(--surface);
		font: inherit;
		text-align: left;
		cursor: pointer;
	}
	.meta {
		font-size: 13px;
		color: var(--muted);
	}
	.titre {
		display: -webkit-box;
		overflow: hidden;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		font-size: 15px;
		font-weight: 600;
		color: var(--text);
	}
	.fiche {
		font-size: 14px;
		color: var(--muted);
	}
	.nom {
		color: var(--text);
		font-weight: 600;
	}
	.voir {
		color: var(--accent);
		font-weight: 600;
	}
</style>
