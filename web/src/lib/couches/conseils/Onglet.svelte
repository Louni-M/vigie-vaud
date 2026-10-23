<script lang="ts">
	/*
	 * Onglet Conseil, de la fiche commune ou de la fiche du Grand Conseil (`ctx.fiche`). Le registre a déjà rendu les
	 * badges et, pour une commune que la couche ne couvre pas, « Non couvert » en tête ; il remonte l'onglet quand on
	 * change de fiche. Le conseil est lu dans `conseils/index.json`.
	 *
	 * Commune dont le conseil est couvert : le nom du conseil (et, s'il ne donne que ses Séances, la note « Séances
	 * seulement : les objets sont sur le site de la commune › », `noteDeNiveau`), l'en-tête de séance, « Objets récents », « Séances passées », puis, après un
	 * séparateur, « Au Grand Conseil ». Commune non couverte : « Au Grand Conseil » seul, sous « Non couvert ».
	 *
	 * Fiche du Grand Conseil : l'en-tête de séance, « Objets récents » avec les puces « Tous · Nomment une commune ·
	 * Sans commune », « Séances passées », aux mêmes longueurs que dans l'onglet d'une commune.
	 *
	 * Une ligne d'Objet ou de Séance, et un point de l'en-tête lié à un Objet, ouvrent l'élément par le registre, dans
	 * cet onglet (`?c=`).
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { ConseilIndexe, IndexConseils } from '#lib/schema.js';
	import AuGrandConseil from './AuGrandConseil.svelte';
	import { FICHE_GRAND_CONSEIL } from './cles.js';
	import { conseils } from './donnees.js';
	import { coucheConseils } from './index.js';
	import ObjetsRecents from './ObjetsRecents.svelte';
	import { donneDesObjets, SOURCES } from '#lib/sources.js';
	import SeancesPassees from './SeancesPassees.svelte';
	import { noteDeNiveau } from './source.js';
	import TeteSeance from './TeteSeance.svelte';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	// Le registre ne monte l'onglet que pour une fiche ouverte, et le remonte pour une autre.
	const commune = untrack(() => ctx.commune);
	const grandConseil = untrack(() => ctx.fiche?.id === FICHE_GRAND_CONSEIL);

	/** Le conseil de la fiche : le Grand Conseil dans sa fiche, sinon celui de la commune s'il est couvert. */
	const conseilDeLaFiche = (index: IndexConseils): ConseilIndexe | undefined =>
		grandConseil
			? index.conseils.find((c) => c.commune === null)
			: index.conseils.find((c) => commune !== null && c.commune === commune.bfs);

	let lecture = $state(conseils.index());

	const ouvrir = (cle: string) => ctx.ouvrir({ couche: coucheConseils.id, element: cle });
</script>

{#await lecture}
	<p class="note" aria-busy="true">Lecture du conseil…</p>
{:then index}
	{@const conseil = conseilDeLaFiche(index)}
	{#if grandConseil}
		{#if conseil}
			<TeteSeance {conseil} {ouvrir} />
			<ObjetsRecents {conseil} {ouvrir} puces communes={ctx.communes} />
			<SeancesPassees {conseil} {ouvrir} />
		{/if}
	{:else}
		{#if conseil}
			{@const source = SOURCES.find((s) => s.id === conseil.source)}
			{@const note = source && noteDeNiveau(source)}
			<h3>{conseil.nom}</h3>
			{#if note}
				<p class="note">
					{note.niveau} :
					{#if note.lien}<a href={note.lien} target="_blank" rel="noopener">{note.suite}</a>{:else}{note.suite}{/if}
				</p>
			{/if}
			<TeteSeance {conseil} {ouvrir} />
			{#if donneDesObjets(conseil)}<ObjetsRecents {conseil} {ouvrir} />{/if}
			{#if conseil.donne.includes('seances')}<SeancesPassees {conseil} {ouvrir} />{/if}
			<hr />
		{/if}
		{#if commune}<AuGrandConseil {commune} communes={ctx.communes} {ouvrir} />{/if}
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
	hr {
		margin: 22px 0 12px;
		border: 0;
		border-top: 2px solid var(--line);
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
