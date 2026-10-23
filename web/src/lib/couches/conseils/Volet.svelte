<script lang="ts">
	/*
	 * Volet de la couche Conseils, sous l'interrupteur, les badges et l'attribution du registre : la légende, puis la
	 * carte du Grand Conseil et une ligne par conseil communal de la zone affichée, lus dans `conseils/index.json`, et
	 * la phrase sur les communes grisées. Un conseil communal ouvre la fiche de sa commune, sur l'onglet Conseil ; le
	 * Grand Conseil ouvre la sienne.
	 */
	import type { Contexte } from '#lib/registre/types.js';
	import { listerConseils, SOURCES } from '#lib/sources.js';
	import { MediaQuery } from 'svelte/reactivity';
	import { TELEPHONE } from '#lib/socle/telephone.js';
	import { carteConseil, lignesConseils, noteAutresCommunes } from './cartes.js';
	import { FICHE_GRAND_CONSEIL } from './cles.js';
	import { conseils } from './donnees.js';
	import { COULEUR_CONSEILS, coucheConseils } from './index.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	let lecture = $state(conseils.index());

	/** Les communes dont le conseil n'est pas couvert, grisées tant que le volet est ouvert. */
	const couvertes = new Set(
		listerConseils(SOURCES).flatMap(({ source }) =>
			Array.isArray(source.couverture?.communes) ? source.couverture.communes : []
		)
	);
	const autres = $derived(ctx.communes.filter((c) => !couvertes.has(c.bfs)).length);
	/** Sur téléphone, le grisage ne suit pas le volet mais « Voir sur la carte » : la phrase le dit. */
	const telephone = new MediaQuery(TELEPHONE, false);
</script>

<ul class="legende" style:--c={COULEUR_CONSEILS}>
	<li><span class="fronton" aria-hidden="true">GC</span> Le Grand Conseil, au Parlement : un clic ouvre sa fiche.</li>
	<li>
		<span class="hotel" aria-hidden="true"></span> Les conseils communaux sont dans la fiche de leur commune, onglet
		Conseil.
	</li>
	<li>
		<span class="pastilles" aria-hidden="true"><span class="seance"></span><span class="objet"></span></span>
		Une pastille cerclée pour une Séance, pleine pour un Objet.
	</li>
</ul>

<section aria-labelledby="conseils-couverts">
	<h3 id="conseils-couverts">Conseils couverts</h3>
	{#await lecture}
		<p class="note">Lecture des conseils…</p>
	{:then index}
		{@const communaux = index.conseils.filter((c) => c.commune !== null)}
		{@const lignes = lignesConseils(index.conseils, ctx.communes, ctx.zone)}
		<ul class="conseils" style:--c={COULEUR_CONSEILS}>
			{#each index.conseils.filter((c) => c.commune === null) as conseil (conseil.cle)}
				<li>
					<button type="button" class="carte" onclick={() => ctx.ouvrir({ fiche: FICHE_GRAND_CONSEIL })}>
						{@render contenu(carteConseil(conseil, ctx.communes))}
					</button>
				</li>
			{/each}
		</ul>
		{#if communaux.length}
			<p class="compte">
				<strong>{communaux.length}</strong> conseil{communaux.length > 1 ? 's' : ''} communa{communaux.length > 1
					? 'ux'
					: 'l'}{#if lignes.length < communaux.length}, dont <strong>{lignes.length}</strong> dans la zone affichée{/if}
			</p>
			<ul class="lignes" style:--c={COULEUR_CONSEILS}>
				{#each lignes as ligne (ligne.cle)}
					<li>
						<button
							type="button"
							class="ligne"
							onclick={() => ctx.ouvrir({ commune: ligne.slug, onglet: coucheConseils.id })}
						>
							<strong>{ligne.commune}</strong>
							<span>{ligne.detail}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	{:catch}
		<p class="erreur">
			Les conseils couverts n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={() => (lecture = conseils.index())}>
				Réessayer
			</button>
		</p>
	{/await}
	<p class="note">{noteAutresCommunes(autres, telephone.current)}</p>
</section>

{#snippet contenu(carte: ReturnType<typeof carteConseil>)}
	<strong>{carte.nom}</strong>
	<span>{carte.donne}{#if carte.recents}{` · ${carte.recents}`}{/if}</span>
	{#if carte.seance}<span>{carte.seance}</span>{/if}
{/snippet}

<style>
	h3 {
		margin: 4px 0 6px;
		font-size: 13px;
	}
	.note {
		margin: 8px 0 0;
		font-size: 12px;
		line-height: 1.45;
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
	.legende {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
		font-size: 13px;
		line-height: 1.4;
	}
	.legende li {
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.fronton {
		flex: none;
		display: grid;
		place-items: center;
		width: 26px;
		height: 22px;
		padding-top: 4px;
		box-sizing: border-box;
		background: var(--c);
		color: #fff;
		font-size: 10px;
		font-weight: 700;
		clip-path: polygon(50% 0, 100% 28%, 100% 100%, 0 100%, 0 28%);
	}
	.hotel {
		flex: none;
		width: 14px;
		height: 14px;
		margin: 0 6px;
		border-radius: 50%;
		background: #1f3a5f;
		border: 2px solid #fff;
		box-shadow: 0 0 0 1px #1f3a5f;
		box-sizing: border-box;
	}
	.pastilles {
		flex: none;
		display: flex;
		gap: 4px;
		width: 26px;
		justify-content: center;
	}
	.pastilles span {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		box-sizing: border-box;
	}
	.seance {
		border: 2px solid var(--c);
	}
	.objet {
		background: var(--c);
	}
	.conseils {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
	}
	.carte {
		display: grid;
		gap: 1px;
		width: 100%;
		box-sizing: border-box;
		padding: 8px 10px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--surface);
		font: inherit;
		font-size: 12px;
		color: var(--muted);
		text-align: left;
	}
	button.carte {
		cursor: pointer;
	}
	button.carte:hover,
	button.carte:focus-visible {
		border-color: var(--c);
	}
	.carte strong {
		font-size: 14px;
		color: var(--text);
	}
	.compte {
		margin: 10px 0 4px;
		font-size: 12px;
		color: var(--muted);
	}
	.compte strong {
		color: var(--text);
	}
	.lignes {
		list-style: none;
		margin: 0;
		padding: 0;
		border-top: 1px solid var(--line);
	}
	.ligne {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 8px;
		width: 100%;
		padding: 6px 2px;
		border: 0;
		border-bottom: 1px solid var(--line);
		background: none;
		font: inherit;
		font-size: 12px;
		color: var(--muted);
		text-align: left;
		cursor: pointer;
	}
	.ligne strong {
		font-size: 13px;
		color: var(--text);
	}
	.ligne:hover strong,
	.ligne:focus-visible strong {
		color: var(--c);
	}
	@media (pointer: coarse) {
		.petit,
		.ligne {
			min-height: 44px;
		}
	}
</style>
