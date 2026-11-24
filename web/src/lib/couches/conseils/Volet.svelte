<script lang="ts">
	/*
	 * La rubrique Conseils communaux : le compte, puis une ligne par commune suivie de la zone affichée, avec ce que
	 * donne son conseil et sa prochaine Séance, lus dans `conseils/index.json`, et la phrase sur les communes grisées.
	 * Une ligne ouvre la fiche de sa commune, sur l'onglet Conseil : c'est un lien vers sa page, qu'un clic simple ouvre
	 * par le registre, Cmd/Ctrl-clic ou le clic du milieu dans un nouvel onglet. Le Grand Conseil a sa propre rubrique.
	 */
	import { clicSimple, lienCommune } from '#lib/registre/liens.js';
	import { conseils } from './donnees.js';
	import { phraseCompte } from '#lib/registre/rubriques.js';
	import type { Cible, Contexte } from '#lib/registre/types.js';
	import { listerConseils, SOURCES } from '#lib/sources.js';
	import { lignesConseils, noteAutresCommunes } from './cartes.js';
	import { COULEUR_CONSEILS, coucheConseils, type ParametresConseils } from './index.js';

	let { ctx }: { ctx: Contexte<ParametresConseils> } = $props();

	let lecture = $state(conseils.index());

	/** La rubrique de la couche qu'ouvre ce volet : sa phrase de compte est celle du sommaire. */
	const rubrique = coucheConseils.rubriques!.find((r) => r.id === coucheConseils.id)!;

	/** Les communes dont le conseil n'est pas couvert, grisées tant que la rubrique est ouverte. */
	const couvertes = new Set(
		listerConseils(SOURCES).flatMap(({ source }) =>
			Array.isArray(source.couverture?.communes) ? source.couverture.communes : []
		)
	);
	const autres = $derived(ctx.communes.filter((c) => !couvertes.has(c.bfs)).length);

	/** Un clic simple ouvre la cible par le registre ; avec une touche ou un autre bouton, le navigateur suit le lien. */
	function ouvrirAuClic(e: MouseEvent, cible: Cible) {
		if (!clicSimple(e)) return;
		e.preventDefault();
		ctx.ouvrir(cible);
	}
</script>

<section aria-label="Communes suivies">
	{#await lecture}
		<p class="note">Lecture des conseils…</p>
	{:then index}
		{@const lignes = lignesConseils(index.conseils, ctx.communes, ctx.zone)}
		{@const c = phraseCompte(rubrique, lignes.length)}
		<p class="compte">{#if c.nombre}<strong>{c.nombre}</strong>{/if}{c.texte}</p>
		<ul class="lignes" style:--c={COULEUR_CONSEILS}>
			{#each lignes as ligne (ligne.cle)}
				<li>
					<a
						class="ligne"
						href={lienCommune(ligne.slug, coucheConseils.id)}
						onclick={(e) => ouvrirAuClic(e, { commune: ligne.slug, onglet: coucheConseils.id })}
					>
						<strong>{ligne.commune}</strong>
						<span>{ligne.detail}</span>
					</a>
				</li>
			{/each}
		</ul>
	{:catch}
		<p class="erreur" role="alert">
			Les conseils couverts n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={() => (lecture = conseils.index())}>
				Réessayer
			</button>
		</p>
	{/await}
	<p class="note">{noteAutresCommunes(autres)}</p>
</section>

<style>
	.note {
		margin: 8px 0 0;
		font-size: 12px;
		line-height: 1.45;
		color: var(--color-muted);
	}
	.erreur {
		margin: 0;
	}
	.petit {
		margin-left: 6px;
		padding: 6px 10px;
		font-size: 13px;
	}
	.compte {
		margin: 10px 0 4px;
		font-size: 12px;
		color: var(--color-ink-2);
	}
	.compte strong {
		font-family: var(--font-outlier);
		font-weight: 500;
		font-variant-numeric: tabular-nums;
		color: var(--color-ink);
	}
	.lignes {
		list-style: none;
		margin: 0;
		padding: 0;
		border-top: 1px solid var(--color-rule);
	}
	.ligne {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 8px;
		width: 100%;
		box-sizing: border-box;
		padding: 6px 2px;
		border: 0;
		border-bottom: 1px solid var(--color-rule);
		background: none;
		font: inherit;
		font-size: 12px;
		color: var(--color-muted);
		text-align: left;
		text-decoration: none;
	}
	.ligne strong {
		font-size: 13px;
		color: var(--color-ink);
	}
	.ligne:hover strong,
	.ligne:focus-visible strong {
		color: var(--c);
	}
	.ligne:hover strong {
		text-decoration: underline;
	}
	@media (pointer: coarse) {
		.petit,
		.ligne {
			min-height: 44px;
		}
	}
</style>
