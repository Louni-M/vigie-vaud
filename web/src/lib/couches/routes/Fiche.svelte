<script lang="ts">
	/*
	 * Fiche d'une restriction de circulation ouverte, dans l'onglet Routes de sa commune : le registre a rendu le fil
	 * « Routes › Restriction de circulation » au-dessus, et la remonte pour une autre restriction ; la fermer ramène à
	 * l'onglet. Dans l'ordre : sorte, état et échéance, puis le nom des travaux ; période et horaires ; route,
	 * travaux, remarque et longueur ; communes traversées, chacune ouvrant son onglet Routes ; « Mêmes travaux »,
	 * chacune ouvrant sa fiche ; badge de la source. Ni `OBJECTID`, ni `ENTITE`, ni `ARRDT`.
	 */
	import { untrack } from 'svelte';
	import { ErreurApi } from '#lib/api.js';
	import BadgeFraicheur from '#lib/components/BadgeFraicheur.svelte';
	import { jourDe } from '#lib/fil/fil.js';
	import type { Contexte } from '#lib/registre/types.js';
	import { source } from '#lib/sources.js';
	import { routes, type Restriction } from './donnees.svelte.js';
	import { ficheRestriction, ligneMemesTravaux, memesTravaux } from './fiche.js';
	import { coucheRoutes, ouvrirRestriction } from './index.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();

	const id = Number(untrack(() => ctx.ouvert?.element));
	const dgmr = source('dgmr-restrictions');

	let trouvee = $state.raw<Restriction | null>(null);
	let etat = $state<'chargement' | 'trouve' | 'absent' | 'erreur'>('chargement');
	let message = $state('');

	function charger() {
		etat = 'chargement';
		routes.restriction(id).then(
			(r) => {
				trouvee = r;
				etat = r ? 'trouve' : 'absent';
			},
			(e) => {
				etat = 'erreur';
				message =
					e instanceof ErreurApi && e.hors_ligne
						? 'Vous semblez hors ligne : les restrictions sont lues en direct auprès de la DGMR.'
						: `${e instanceof ErreurApi ? e.message : 'La restriction n’a pas pu être chargée.'} Réessayez dans un instant.`;
			}
		);
	}
	charger();

	// « Mêmes travaux » demande toutes les restrictions, en cours et à venir : celles de la carte, chargées une fois.
	$effect(() => {
		if (!routes.source.erreur) untrack(() => routes.rattachees().catch(() => {}));
	});
	const toutes = $derived(routes.chargee('en_cours') && routes.chargee('a_venir'));

	// Celle de la couche quand elle est chargée et rattachée : la même, à jour.
	const r = $derived(routes.restrictions.find((x) => x.id === id && x.communes) ?? trouvee);
	const f = $derived(r && ficheRestriction(r, { aujourdhui: jourDe(new Date()) }));
	const freres = $derived(r && toutes ? memesTravaux(r, routes.restrictions) : []);
</script>

{#if etat === 'trouve' && r && f}
	<p class="tete" style:--c={f.couleur}>
		<span class="trait" class:tirets={f.tirets}></span>
		<strong>{f.sorte}</strong>
		<span class="muted">{f.etat} · {f.echeance}</span>
	</p>
	{#if f.nom}<h3 class="nom">{f.nom}</h3>{/if}

	<p class="periode">{f.periode}</p>
	<p class="horaires">
		{f.horaires}{#if f.weekEnd}<span> · {f.weekEnd}</span>{/if}
	</p>

	<dl>
		{#if f.route}<dt>Route</dt><dd>{f.route}</dd>{/if}
		{#if f.travaux}<dt>Travaux</dt><dd>{f.travaux}</dd>{/if}
		{#if f.remarque}<dt>Remarque</dt><dd>{f.remarque}</dd>{/if}
		<dt>Longueur</dt>
		<dd>{f.longueur}</dd>
	</dl>

	<h4>Communes traversées</h4>
	{#if f.communes}
		<ol class="communes">
			{#each f.communes as c (c.slug)}
				<li>
					<button
						type="button"
						class="lien"
						onclick={() => ctx.ouvrir({ commune: c.slug, onglet: coucheRoutes.id })}>{c.nom}</button
					>
					<span class="muted">{c.longueur}</span>
				</li>
			{/each}
		</ol>
	{:else}
		<p class="muted">Rattachement aux communes…</p>
	{/if}

	{#if freres.length}
		<h4>Mêmes travaux</h4>
		<ul class="freres">
			{#each freres as x (x.id)}
				{@const l = ligneMemesTravaux(x)}
				<li style:--c={l.couleur}>
					<span class="trait" class:tirets={l.tirets}></span>
					<span class="frere">
						<button type="button" class="lien" onclick={() => ouvrirRestriction(ctx, x)}>{l.sorte}</button>
						<span class="muted">{l.detail}</span>
					</span>
				</li>
			{/each}
		</ul>
	{/if}

	<p class="badge"><BadgeFraicheur source={dgmr} /></p>
{:else if etat === 'chargement'}
	<div class="squelette" aria-busy="true">
		<p class="muted">Chargement de la restriction auprès de la DGMR…</p>
		<span style:width="35%"></span>
		<span style:width="70%" class="grand"></span>
		<span style:width="95%"></span>
		<span style:width="60%"></span>
	</div>
{:else if etat === 'absent'}
	<p>{coucheRoutes.introuvable?.(String(id))}</p>
{:else}
	<p class="erreur" role="alert">
		{message}
		<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
	</p>
{/if}

<p class="source">
	Restriction de circulation lue en direct auprès de la DGMR depuis votre navigateur ; ce site ne la conserve pas. La
	signalisation sur place fait foi.
</p>

<style>
	.tete {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 8px;
		margin: 0;
		font-size: 14px;
	}
	.trait {
		flex: none;
		width: 22px;
		height: 6px;
		border-radius: 3px;
		background: var(--c);
	}
	.trait.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 5px, transparent 5px 8px);
	}
	.nom {
		font-size: 20px;
		margin: 6px 0 10px;
	}
	.periode {
		margin: 0;
	}
	.horaires {
		margin: 2px 0 0;
		color: var(--muted);
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 4px 12px;
		margin: 14px 0;
		font-size: 14px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	h4 {
		margin: 18px 0 6px;
		font-size: 14.5px;
	}
	.communes {
		margin: 0;
		padding-left: 20px;
		font-size: 14px;
	}
	.communes li {
		margin: 2px 0;
	}
	.freres {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
		font-size: 14px;
	}
	.freres li {
		display: flex;
		align-items: baseline;
		gap: 8px;
	}
	.freres .trait {
		align-self: center;
	}
	.frere {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		column-gap: 8px;
		min-width: 0;
	}
	.lien {
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: var(--accent);
		text-decoration: underline;
		cursor: pointer;
	}
	@media (pointer: coarse) {
		.lien {
			min-height: 44px;
		}
	}
	.badge {
		margin: 18px 0 0;
	}
	.squelette {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.squelette span {
		display: block;
		height: 14px;
		border-radius: 7px;
		background: var(--line);
	}
	.squelette .grand {
		height: 24px;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin-top: 28px;
	}
</style>
