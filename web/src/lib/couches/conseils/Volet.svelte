<script lang="ts">
	/*
	 * Volet de la couche Conseils, sous l'interrupteur, les badges et l'attribution du registre : la légende, puis une
	 * carte par conseil couvert, lue dans `conseils/index.json`, et la phrase sur les communes grisées. Un conseil
	 * communal ouvre la fiche de sa commune ; le Grand Conseil ouvrira la sienne quand elle existera.
	 */
	import type { Contexte } from '#lib/registre/types.js';
	import { listerConseils, SOURCES } from '#lib/sources.js';
	import { carteConseil } from './cartes.js';
	import { conseils } from './donnees.js';
	import { COULEUR_CONSEILS } from './index.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	let lecture = $state(conseils.index());

	/** Les communes dont le conseil n'est pas couvert, grisées tant que le volet est ouvert. */
	const couvertes = new Set(
		listerConseils(SOURCES).flatMap(({ source }) =>
			Array.isArray(source.couverture?.communes) ? source.couverture.communes : []
		)
	);
	const autres = $derived(ctx.communes.filter((c) => !couvertes.has(c.bfs)).length);
</script>

<ul class="legende" style:--c={COULEUR_CONSEILS}>
	<li><span class="fronton" aria-hidden="true">GC</span> Le Grand Conseil, au Parlement.</li>
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
		<ul class="conseils" style:--c={COULEUR_CONSEILS}>
			{#each index.conseils as conseil (conseil.cle)}
				{@const carte = carteConseil(conseil, ctx.communes)}
				<li>
					{#if carte.commune}
						{@const slug = carte.commune}
						<button type="button" class="carte" onclick={() => ctx.ouvrir({ commune: slug })}>
							{@render contenu(carte)}
						</button>
					{:else}
						<div class="carte">{@render contenu(carte)}</div>
					{/if}
				</li>
			{/each}
		</ul>
	{:catch}
		<p class="erreur">
			Les conseils couverts n’ont pas pu être chargés.
			<button class="bouton secondaire petit" type="button" onclick={() => (lecture = conseils.index())}>
				Réessayer
			</button>
		</p>
	{/await}
	<p class="note">
		Les {autres} autres communes : pas de conseil couvert, grisées tant que ce volet est ouvert. Leur onglet Conseil
		montre ce que le Grand Conseil dit d’elles.
	</p>
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
	@media (pointer: coarse) {
		.petit {
			min-height: 44px;
		}
	}
</style>
