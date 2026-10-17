<script lang="ts">
	/*
	 * PROTOTYPE : une restriction ouverte, dans l'onglet Routes de sa commune. A : la restriction seule, ses champs,
	 * ses communes, et les autres restrictions de la même intervention en liens. B : toute l'intervention (fermeture et
	 * déviation) sur une seule fiche. C : les dates d'abord, en grand (début, fin, nuits, week-end), puis le reste.
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import {
		echeance,
		heure,
		jourLong,
		longueurTexte,
		periode,
		plageTexte,
		PORTEE,
		rhrcTexte,
		routes,
		SORTES,
		type Restriction
	} from './donnees.svelte.js';
	import type { Parametres } from './index.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();
	const id = Number(untrack(() => ctx.ouvert?.element));
	routes.charger(untrack(() => ctx.communes)).catch(() => {});

	const v = $derived(ctx.parametres.variant);
	const r = $derived(routes.restriction(id));
	const groupe = $derived(r ? routes.groupeDe(r) : null);
	const ouvrir = (x: Restriction) => ctx.ouvrir({ couche: 'routes', element: String(x.id), position: x.milieu });
	const weekEnd = (x: Restriction) =>
		x.weekEnd === true ? 'Week-end compris' : x.weekEnd === false ? 'Pas le week-end' : 'Week-end : non précisé';
</script>

{#snippet communes(x: Restriction)}
	<ol class="communes">
		{#each x.communes as p (p.commune.bfs)}
			<li>
				<button type="button" class="lien" onclick={() => ctx.ouvrir({ commune: p.commune.slug, onglet: 'routes' })}>{p.commune.nom}</button>
				<span class="muted">{longueurTexte(p.metres)}</span>
			</li>
		{/each}
	</ol>
{/snippet}

{#snippet details(x: Restriction)}
	<dl>
		<dt>Route</dt>
		<dd>{rhrcTexte(x.rhrc) ?? '—'}</dd>
		{#if x.travaux}<dt>Travaux</dt><dd>{x.travaux}</dd>{/if}
		{#if x.remarque}<dt>Remarque</dt><dd>{x.remarque}</dd>{/if}
		<dt>Longueur</dt>
		<dd>{longueurTexte(x.longueur)}</dd>
		<dt>N°</dt>
		<dd class="muted">{x.id} (OBJECTID de la DGMR)</dd>
	</dl>
{/snippet}

{#if !r}
	<p class="muted">{routes.charge ? `Aucune restriction n° ${id}.` : 'Chargement auprès du canton…'}</p>
{:else if v === 'A'}
	<p class="tete" style:--c={SORTES[r.sorte].couleur}>
		<span class="pastille" class:tirets={r.sorte === 'deviation'}></span>
		{SORTES[r.sorte].nom}
		<span class="etat">{r.quand === 'a-venir' ? 'À venir' : 'En cours'} · {echeance(r)}</span>
	</p>
	<h3 class="titre">{r.nom}</h3>
	<p>{periode(r, true)}</p>
	<p class="muted">
		{weekEnd(r)}{#if r.plage} · chaque nuit {plageTexte(r.plage)}{/if}
	</p>
	{@render details(r)}
	<h4>Communes traversées</h4>
	{@render communes(r)}
	{#if groupe && groupe.restrictions.length > 1}
		<h4>Sur la même intervention</h4>
		<ul class="freres">
			{#each groupe.restrictions.filter((x) => x.id !== r.id) as x (x.id)}
				<li style:--c={SORTES[x.sorte].couleur}>
					<span class="pastille" class:tirets={x.sorte === 'deviation'}></span>
					<button type="button" class="lien" onclick={() => ouvrir(x)}>{SORTES[x.sorte].nom}</button>
					<span class="muted">{longueurTexte(x.longueur)}</span>
				</li>
			{/each}
		</ul>
	{/if}
{:else if v === 'B' && groupe}
	<p class="surtitre">{rhrcTexte(groupe.rhrc)}</p>
	<h3 class="titre">{groupe.nom}</h3>
	<p>{groupe.quand === 'a-venir' ? 'À venir' : 'En cours'} · {periode(groupe, true)} · {echeance(groupe)}</p>
	{#each groupe.restrictions as x (x.id)}
		<section class="membre" class:courant={x.id === r.id} style:--c={SORTES[x.sorte].couleur}>
			<h4>
				<span class="pastille" class:tirets={x.sorte === 'deviation'}></span>{SORTES[x.sorte].nom}
				<span class="muted">· {longueurTexte(x.longueur)}</span>
			</h4>
			{#if x.debut.jour !== groupe.debut.jour || x.fin.jour !== groupe.fin.jour}<p>{periode(x)}</p>{/if}
			{#if x.plage}<p>Chaque nuit {plageTexte(x.plage)}</p>{/if}
			{#if x.remarque}<p>{x.remarque}</p>{/if}
			<p class="muted">{x.communes.map((p) => `${p.commune.nom} (${longueurTexte(p.metres)})`).join(' · ')}</p>
		</section>
	{/each}
	<p class="muted">{weekEnd(r)}{r.travaux ? ` · ${r.travaux}` : ''}</p>
{:else}
	<p class="tete" style:--c={SORTES[r.sorte].couleur}>
		<span class="pastille" class:tirets={r.sorte === 'deviation'}></span>{SORTES[r.sorte].nom} · {r.nom}
	</p>
	<div class="tuiles">
		<div class:passe={r.quand === 'en-cours'}>
			<small>{r.quand === 'en-cours' ? 'Depuis le' : 'Commence le'}</small>
			<strong>{jourLong(r.debut.jour)}</strong>
			{#if heure(r.debut)}<span>à {heure(r.debut)}</span>{/if}
		</div>
		<div>
			<small>Jusqu’au</small>
			<strong>{jourLong(r.fin.jour)}</strong>
			{#if heure(r.fin)}<span>à {heure(r.fin)}</span>{/if}
		</div>
	</div>
	<p class="compte-a-rebours">{echeance(r)}</p>
	<ul class="horaires">
		<li>{r.plage ? `La nuit seulement, ${plageTexte(r.plage)}` : r.debut.heure || r.fin.heure ? 'En continu entre ces heures' : 'Jour et nuit'}</li>
		<li>{weekEnd(r)}</li>
	</ul>
	{@render details(r)}
	<h4>Communes</h4>
	{@render communes(r)}
{/if}

<p class="source">Source : Géodonnées Etat de Vaud (DGMR), consultées en direct. {PORTEE}</p>

<style>
	.tete {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0;
		font-weight: 600;
	}
	.etat {
		font-weight: 400;
		color: var(--muted);
	}
	.pastille {
		flex: none;
		width: 22px;
		height: 6px;
		border-radius: 3px;
		background: var(--c);
	}
	.pastille.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 5px, transparent 5px 8px);
	}
	.titre {
		font-size: 20px;
		margin: 6px 0;
	}
	.surtitre {
		margin: 0;
		font-size: 12px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
		color: var(--muted);
	}
	h4 {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 18px 0 6px;
		font-size: 14.5px;
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 4px 12px;
		margin: 12px 0;
		font-size: 14px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	.communes {
		margin: 0;
		padding-left: 20px;
		font-size: 14px;
	}
	.communes li {
		margin: 2px 0;
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
	.freres {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 4px;
	}
	.freres li {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.membre {
		margin: 12px 0;
		padding: 2px 12px 6px;
		border-left: 4px solid var(--c);
		background: var(--surface);
		border-radius: 0 8px 8px 0;
	}
	.membre.courant {
		box-shadow: 0 0 0 1px var(--accent);
	}
	.membre h4 {
		margin-top: 8px;
	}
	.membre p {
		margin: 4px 0;
		font-size: 14px;
	}
	.tuiles {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin: 12px 0 4px;
	}
	.tuiles div {
		display: flex;
		flex-direction: column;
		padding: 10px;
		border-radius: 10px;
		border: 1px solid var(--line);
		background: var(--surface);
	}
	.tuiles .passe {
		opacity: 0.7;
	}
	.tuiles small {
		color: var(--muted);
		font-size: 12px;
	}
	.tuiles strong {
		font-size: 15px;
	}
	.compte-a-rebours {
		margin: 6px 0;
		font-size: 18px;
		font-weight: 650;
	}
	.horaires {
		margin: 0;
		padding-left: 18px;
	}
	.muted {
		color: var(--muted);
	}
	.source {
		margin-top: 28px;
		font-size: 12.5px;
		color: var(--muted);
	}
</style>
