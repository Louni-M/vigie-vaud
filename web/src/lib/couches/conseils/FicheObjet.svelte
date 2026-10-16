<script lang="ts">
	/*
	 * Fiche d'un Objet : en tête, son type, son numéro et son conseil, puis son titre ; un tableau (déposé le,
	 * auteur·e·s avec leur parti, statut et sa date) ; ses étapes datées et ses documents ; « Voir sur lausanne.ch › »
	 * et la source. Le type et le statut sont ceux que le conseil leur donne. Une pétition n'a aucun·e auteur·e.
	 * Pour un Objet du Grand Conseil, après le tableau, les communes nommées (même aucune : une commune peut
	 * manquer), avec « rattachement automatique · signaler une erreur », un courriel pré-rempli.
	 */
	import type { Objet } from '#lib/schema.js';
	import type { Commune } from '#lib/types.js';
	import { CLE_GRAND_CONSEIL, lireCle, nomConseil } from './cles.js';
	import { COULEUR_CONSEILS } from './index.js';
	import { dateCourte, dateLongue, siteDuLien } from './lignes.js';
	import { communesNommees, signalement } from './rattachements.js';
	import Source from './SourceElement.svelte';

	let { cle, objet, communes = [] }: { cle: string; objet: Objet; communes?: readonly Commune[] } = $props();

	const conseil = $derived(nomConseil(lireCle(cle)?.conseil ?? ''));
	const duGrandConseil = $derived(lireCle(cle)?.conseil === CLE_GRAND_CONSEIL);
	const nommees = $derived(communesNommees(objet.communes, communes));
	const auteurs = $derived(objet.contributeurs.map((a) => (a.parti ? `${a.nom} (${a.parti})` : a.nom)));
</script>

<article class="fiche" style:--c={COULEUR_CONSEILS}>
	<p class="type"><span class="pastille" aria-hidden="true"></span>{objet.type} {objet.numero}{conseil ? ` · ${conseil}` : ''}</p>
	<h3>{objet.titre}</h3>
	<dl>
		{#if objet.depose}
			<dt>Déposé le</dt>
			<dd>{dateLongue(objet.depose)}</dd>
		{/if}
		{#if auteurs.length}
			<dt>{auteurs.length > 1 ? 'Auteur·e·s' : 'Auteur·e'}</dt>
			<dd>{auteurs.join(', ')}</dd>
		{/if}
		{#if objet.statut}
			<dt>Statut</dt>
			<dd>{objet.statut.libelle}{objet.statut.date ? `, ${dateLongue(objet.statut.date)}` : ''}</dd>
		{/if}
	</dl>

	{#if duGrandConseil}
		<div class="communes">
			<p><span class="etiquette">Communes nommées</span> {nommees.length ? nommees.join(', ') : 'aucune'}</p>
			<p class="aide">
				rattachement automatique · <a href={signalement(cle, nommees)}>signaler une erreur</a>
			</p>
		</div>
	{/if}

	{#if objet.etapes.length}
		<h4>Étapes</h4>
		<ol class="etapes">
			{#each objet.etapes as e, i (i)}
				<li><span class="date">{dateCourte(e.date)}</span> {e.libelle}</li>
			{/each}
		</ol>
	{/if}

	{#if objet.documents.length}
		<h4>Documents</h4>
		<ul class="documents">
			{#each objet.documents as d, i (i)}
				<li>
					<a href={d.lien} target="_blank" rel="noopener">{d.titre ?? 'Document'}</a>
					{#if d.date}<span class="date"> · {dateCourte(d.date)}</span>{/if}
				</li>
			{/each}
		</ul>
	{/if}

	{#if objet.lien}
		<p class="externe"><a href={objet.lien} target="_blank" rel="noopener">Voir sur {siteDuLien(objet.lien)} ›</a></p>
	{/if}
	<Source />
</article>

<style>
	.fiche {
		display: grid;
		gap: 8px;
	}
	.type {
		display: flex;
		align-items: center;
		gap: 6px;
		margin: 0;
		font-size: 13px;
		font-weight: 600;
		color: var(--c);
	}
	.pastille {
		flex: none;
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--c);
	}
	h3 {
		margin: 0;
		font-size: 18px;
		line-height: 1.3;
	}
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 4px 14px;
		margin: 0;
		font-size: 14px;
	}
	dt {
		color: var(--muted);
	}
	dd {
		margin: 0;
	}
	.communes {
		display: grid;
		gap: 2px;
		padding: 8px 10px;
		border-radius: 8px;
		background: #e3f2f4;
		font-size: 14px;
	}
	.communes p {
		margin: 0;
	}
	.etiquette {
		margin-right: 6px;
		color: var(--muted);
	}
	.aide {
		font-size: 12px;
		color: var(--muted);
	}
	h4 {
		margin: 8px 0 0;
		font-size: 12px;
		letter-spacing: 0.04em;
		text-transform: uppercase;
		color: var(--muted);
	}
	.etapes {
		margin: 0;
		padding: 0 0 0 12px;
		list-style: none;
		border-left: 2px solid #b9dde2;
		font-size: 13px;
	}
	.etapes li,
	.documents li {
		margin: 3px 0;
	}
	.documents {
		margin: 0;
		padding-left: 18px;
		font-size: 13px;
	}
	.date {
		font-size: 12px;
		color: var(--muted);
	}
	.externe {
		margin: 8px 0 0;
		font-size: 14px;
	}
</style>
