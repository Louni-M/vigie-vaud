<script lang="ts">
	/*
	 * Onglet Routes de la fiche commune : l'encadré des limites de la source, puis « En cours (n) » et « À venir (n) »,
	 * en cartes de restriction, dans l'ordre des listes. Le registre a déjà rendu l'en-tête, la barre d'onglets et le
	 * badge de la DGMR sous le nom de l'onglet ; il remonte l'onglet quand on change de commune. Les restrictions sont
	 * lues en direct, puis rattachées aux communes une fois chargées leurs limites. Une carte ouvre sa restriction,
	 * dans cette fiche : la commune de l'onglet est l'une des siennes.
	 */
	import { untrack } from 'svelte';
	import EchecSource from '#lib/components/EchecSource.svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { source } from '#lib/sources.js';
	import type { Commune } from '#lib/types.js';
	import { encadreLimites, sectionsDeLaCommune } from './cartes.js';
	import { routes, type EtatRestriction } from './donnees.svelte.js';
	import { ouvrirRestriction } from './index.js';
	import RestrictionCarte from './RestrictionCarte.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	// Le registre ne monte l'onglet que pour une commune ouverte, et le remonte pour une autre.
	const commune = untrack(() => ctx.commune) as Commune;
	const encadre = encadreLimites(source('dgmr-restrictions'));

	/** Les limites des communes n'ont pas pu être chargées (la DGMR, elle, a répondu). */
	let echecLimites = $state(false);

	function charger() {
		echecLimites = false;
		routes.rattachees().catch(() => (echecLimites = !routes.source.erreur));
	}
	// Au montage, et de nouveau quand l'erreur de la source est levée (« Réessayer », ici ou dans le volet).
	$effect(() => {
		if (!routes.source.erreur) untrack(charger);
	});

	const sections = $derived(sectionsDeLaCommune(routes.restrictions, commune.slug));
	const SECTIONS: { etat: EtatRestriction; titre: string; vide: string; echec: string }[] = [
		{
			etat: 'en_cours',
			titre: 'En cours',
			vide: 'Aucune restriction en cours.',
			echec: 'Les restrictions en cours n’ont pas pu être chargées.'
		},
		{
			etat: 'a_venir',
			titre: 'À venir',
			vide: 'Aucune restriction à venir.',
			echec: 'Les restrictions à venir n’ont pas pu être chargées.'
		}
	];
</script>

<EchecSource source="dgmr-restrictions" message="Les restrictions de circulation n’ont pas pu être chargées" />

{#if encadre}<p class="encadre">{encadre}</p>{/if}

{#if echecLimites}
	<p class="erreur" role="alert">
		Les limites des communes n’ont pas pu être chargées : les restrictions ne peuvent pas être rattachées.
		<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
	</p>
{/if}

{#each SECTIONS as s (s.etat)}
	{@const liste = s.etat === 'en_cours' ? sections.enCours : sections.aVenir}
	{@const pret = routes.rattache && routes.chargee(s.etat)}
	<h3>{s.titre}{pret ? ` (${liste.length})` : ''}</h3>
	{#if pret && liste.length}
		<ul class="grille">
			{#each liste as r (r.id)}
				<li><RestrictionCarte {r} commune={commune.slug} onclick={() => ouvrirRestriction(ctx, r)} /></li>
			{/each}
		</ul>
	{:else if pret}
		<p class="muted">{s.vide}</p>
	{:else if routes.source.erreur && !routes.chargee(s.etat)}
		<p class="muted">{s.echec}</p>
	{:else if !echecLimites}
		<ul class="grille" aria-busy="true"><li class="attente"></li></ul>
	{/if}
{/each}

<p class="source">
	Restrictions de circulation lues en direct auprès de la DGMR depuis votre navigateur ; ce site ne les conserve pas.
	La signalisation sur place fait foi. Chaque restriction est rattachée aux communes que son tracé parcourt (limites
	swisstopo).
</p>

<style>
	.encadre {
		margin: 0 0 4px;
		padding: 8px 10px;
		border-radius: 8px;
		background: var(--bg);
		border: 1px solid var(--line);
		font-size: 13px;
		line-height: 1.45;
	}
	h3 {
		font-size: 16px;
		margin: 22px 0 8px;
	}
	.grille {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 8px;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		margin: 10px 0;
		color: var(--erreur);
	}
	.source {
		margin-top: 28px;
	}
	.attente {
		min-height: 78px;
		border-radius: 10px;
		background: var(--line);
		opacity: 0.6;
	}
</style>
