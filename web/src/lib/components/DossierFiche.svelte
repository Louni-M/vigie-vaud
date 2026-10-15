<script lang="ts">
	import { resolve } from '$app/paths';
	import { STATUTS, natureLabel } from '#lib/labels.js';
	import { dateLongue } from '#lib/dates.js';
	import { lienCommune, lienVue } from '#lib/registre/liens.js';
	import type { Dossier } from '#lib/types.js';
	import Compte from './Compte.svelte';
	import Consultation from './Consultation.svelte';

	let {
		d,
		lienFiche = false,
		lienCarte = false
	}: { d: Dossier; lienFiche?: boolean; lienCarte?: boolean } = $props();
</script>

<article class="fiche">
	<p class="statut" style:--c={STATUTS[d.statut].couleur}>
		<span class="pastille"></span>{STATUTS[d.statut].label}
	</p>
	<h2>{natureLabel(d.nature)} · <a href={lienCommune(d.slug)}>{d.commune}</a></h2>
	<p class="desc">{d.description ?? 'Sans description'}</p>

	{#if d.statut === 'enquete'}
		<p><Compte fin={d.fin} /></p>
	{/if}

	<dl>
		<dt>Enquête publique</dt>
		<dd>du {dateLongue(d.debut)} au {dateLongue(d.fin)}</dd>
		{#if d.decision}
			<dt>Décision communale</dt>
			<dd>{d.decision}{d.date_decision ? ` le ${dateLongue(d.date_decision)}` : ''}</dd>
		{/if}
		<dt>N° CAMAC</dt>
		<dd>{d.id}</dd>
		{#if d.fao}
			<dt>N° FAO</dt>
			<dd>{d.fao}</dd>
		{/if}
	</dl>

	{#if d.historique?.length}
		<h3>Évolution suivie</h3>
		<ul class="histo">
			{#each d.historique as e (e.date)}
				<li>{dateLongue(e.date)} : {e.statut ? STATUTS[e.statut].court : ''}{e.decision ? ` (${e.decision})` : ''}</li>
			{/each}
		</ul>
	{/if}

	<p class="actions">
		{#if d.url}
			<a class="bouton" href={d.url} target="_blank" rel="noopener">Voir l’avis d’enquête officiel ↗</a>
		{/if}
		{#if lienFiche}
			<a class="bouton secondaire" href={resolve('/dossier/[id]', { id: String(d.id) })}>Fiche et lien à partager</a>
		{/if}
		{#if lienCarte}
			<a class="bouton secondaire" href={lienVue({ lon: d.lon, lat: d.lat, zoom: 17 })}>Voir sur la carte</a>
		{/if}
	</p>

	{#if d.statut === 'enquete'}
		<Consultation commune={d.commune} />
	{:else if d.statut === 'procedure'}
		<p class="note">
			L’enquête publique est terminée : la Municipalité statue sur la demande.
			<a href={resolve('/infos-legales')}>Comment se déroule la procédure</a>
		</p>
	{/if}
	{#if d.statut === 'enquete' || d.statut === 'procedure'}
		<p class="note">
			L’État de Vaud propose un abonnement gratuit par courriel aux avis d’enquête publiés dans la FAO, autour
			d’une adresse ou pour une commune :
			<a href="https://www.vd.ch/prestation/sabonner-aux-avis-denquete" target="_blank" rel="noopener">InfoCamac ↗</a>
		</p>
	{/if}
</article>

<style>
	.fiche {
		display: grid;
		gap: 10px;
	}
	.statut {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 600;
	}
	.pastille {
		flex: none;
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: var(--c);
	}
	h2 {
		margin: 0;
		font-size: 20px;
		line-height: 1.25;
	}
	h2 a {
		color: inherit;
	}
	h3 {
		margin: 4px 0 0;
		font-size: 15px;
	}
	.desc {
		margin: 0;
		font-size: 16px;
		line-height: 1.45;
	}
	p {
		margin: 0;
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
	.histo {
		margin: 0;
		padding-left: 18px;
		font-size: 14px;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.actions:empty {
		display: none;
	}
	.note {
		font-size: 14px;
		line-height: 1.45;
		color: var(--muted);
	}
</style>
