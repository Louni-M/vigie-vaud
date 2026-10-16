<script lang="ts">
	/*
	 * En-tête de séance, en tête de l'onglet Conseil (et plus tard de la fiche du Grand Conseil) : la prochaine
	 * Séance si elle est annoncée, sinon la dernière, avec les 5 premiers points de son ordre du jour, lus dans son
	 * fichier d'archive, et « Les N points ». Avec `ouvrir`, le nom et « Les N points » ouvrent la Séance, et un
	 * point lié à un Objet ouvre cet Objet.
	 */
	import type { ConseilIndexe } from '#lib/schema.js';
	import { conseils } from './donnees.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { nomSeance, teteSeance } from './lignes.js';

	let { conseil, ouvrir }: { conseil: ConseilIndexe; ouvrir?: (cle: string) => void } = $props();

	/** Points de l'ordre du jour montrés dans l'en-tête. */
	const POINTS = 5;

	const tete = $derived(teteSeance(conseil));
	let lecture = $derived(tete ? conseils.seance(tete.cle) : null);
	const reessayer = () => tete && (lecture = conseils.seance(tete.cle));
</script>

{#if tete}
	<section class="tete" style:--c={COULEUR_CONSEILS} aria-label={tete.prochaine ? 'Prochaine séance' : 'Dernière séance'}>
		<p class="etiquette">{tete.prochaine ? 'Prochaine séance' : 'Dernière séance'}</p>
		{#await lecture}
			<p class="nom">{nomSeance(tete.cle.split('/')[1])}</p>
			<p class="note">Lecture de l’ordre du jour…</p>
		{:then seance}
			{#if seance}
				{@const nom = nomSeance(seance.date)}
				{#if ouvrir}
					<button type="button" class="nom lien" onclick={() => ouvrir(tete.cle)}>{nom} ›</button>
				{:else}
					<p class="nom">{nom}</p>
				{/if}
				{#if seance.ordre_du_jour.length}
					<ol>
						{#each seance.ordre_du_jour.slice(0, POINTS) as point, i (i)}
							<li>
								{#if ouvrir && point.objet}
									{@const objet = point.objet}
									<button type="button" class="point" onclick={() => ouvrir(objet)}>{point.titre}</button>
								{:else}
									{point.titre}
								{/if}
							</li>
						{/each}
					</ol>
					{#if seance.ordre_du_jour.length > POINTS}
						{@const n = seance.ordre_du_jour.length}
						{#if ouvrir}
							<button type="button" class="plus" onclick={() => ouvrir(tete.cle)}>Les {n} points ›</button>
						{:else}
							<p class="plus">Les {n} points</p>
						{/if}
					{/if}
				{:else}
					<p class="note">Ordre du jour pas encore publié.</p>
				{/if}
			{/if}
		{:catch}
			<p class="nom">{nomSeance(tete.cle.split('/')[1])}</p>
			<p class="note">
				L’ordre du jour n’a pas pu être chargé.
				<button type="button" class="point" onclick={reessayer}>Réessayer</button>
			</p>
		{/await}
		{#if !tete.prochaine}<p class="note">Prochaine séance pas encore annoncée.</p>{/if}
	</section>
{/if}

<style>
	.tete {
		margin: 8px 0 4px;
		padding: 10px 12px;
		border-radius: 8px;
		border-left: 4px solid var(--c);
		background: #e3f2f4;
	}
	.etiquette {
		margin: 0;
		font-size: 12px;
		font-weight: 600;
		color: var(--c);
	}
	.nom {
		margin: 0;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		font-size: 15px;
		font-weight: 700;
		text-align: left;
		color: inherit;
	}
	.lien {
		cursor: pointer;
	}
	ol {
		margin: 6px 0 0;
		padding-left: 20px;
		font-size: 13px;
	}
	ol li {
		margin: 2px 0;
	}
	.point {
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: var(--accent);
		text-align: left;
		text-decoration: underline;
		cursor: pointer;
	}
	.note {
		margin: 4px 0 0;
		font-size: 12px;
		color: var(--muted);
	}
	.plus {
		margin: 4px 0 0;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		font-size: 13px;
		color: var(--accent);
	}
	button.plus {
		cursor: pointer;
	}
</style>
