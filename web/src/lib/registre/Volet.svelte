<script lang="ts">
	/*
	 * Volet d'une couche, assemblé par le registre : interrupteur (ou « permanente »), badge de fraîcheur de chaque
	 * source et lien vers la page Couverture, attribution de chaque source tirée de sources.json, puis le `Volet` de
	 * la couche. Les sites des communes y sont regroupés par plateforme : un badge et une attribution pour toutes ses
	 * communes couvertes, qui renvoie à sa fiche de la page Couverture ; une commune non couverte n'y figure pas.
	 * Sans `onfermer` (vue Couches du téléphone), le volet n'a pas de croix. Avec `onvoir` (téléphone, couche qui
	 * grise au moins une commune), il a en tête un bouton « Voir sur la carte », qui montre ce grisage.
	 */
	import { resolve } from '$app/paths';
	import BadgeFraicheur from '#lib/components/BadgeFraicheur.svelte';
	import BadgeSites from '#lib/components/BadgeSites.svelte';
	import type { Source } from '#lib/schema.js';
	import { nomDePlateforme, source } from '#lib/sources.js';
	import type { Registre } from './registre.svelte.js';
	import type { CoucheInscrite } from './types.js';

	let {
		couche,
		registre,
		onfermer,
		onvoir
	}: { couche: CoucheInscrite; registre: Registre; onfermer?: () => void; onvoir?: () => void } = $props();

	const active = $derived(registre.active(couche.id));
	const toutes = $derived(couche.sources.map(source));
	const sources = $derived(toutes.filter((s) => !s.site));
	// Les sites couverts, par plateforme, dans l'ordre de leur première apparition.
	const plateformes = $derived.by(() => {
		const parId = new Map<string, Source[]>();
		for (const s of toutes) {
			if (!s.site || s.couverture?.mode === 'non_couvert') continue;
			parId.set(s.site.plateforme, [...(parId.get(s.site.plateforme) ?? []), s]);
		}
		return [...parId].map(([id, sites]) => ({ id, nom: nomDePlateforme(id), sites }));
	});
	// Une même attribution (« Source: OpenParlData.ch », pour les trois conseils) n'est citée qu'une fois.
	const attributions = $derived(
		sources.filter((s, i) => sources.findIndex((t) => t.attribution.texte === s.attribution.texte) === i)
	);
	const titre = $derived(`volet-${couche.id}`);
</script>

<section class="volet" id="volet-{couche.id}" aria-labelledby={titre}>
	<div class="tete">
		<h2 id={titre}>{couche.nom}</h2>
		{#if couche.permanente}
			<span class="permanente">permanente</span>
		{:else}
			<label class="interrupteur">
				<input
					type="checkbox"
					role="switch"
					checked={active}
					onchange={(e) => registre.activer(couche.id, e.currentTarget.checked)}
				/>
				Affichée
			</label>
		{/if}
		{#if onfermer}
			<button class="fermer" type="button" aria-label="Fermer le volet {couche.nom}" onclick={onfermer}>×</button>
		{/if}
	</div>

	{#if onvoir}
		<button class="bouton secondaire voir" type="button" onclick={onvoir}>Voir sur la carte</button>
	{/if}

	<p class="badges">
		{#each sources as s (s.id)}<BadgeFraicheur source={s} />{/each}
		{#each plateformes as p (p.id)}<BadgeSites plateforme={p.nom} sources={p.sites} />{/each}
		<a class="couverture" href={resolve('/couverture')}>Couverture</a>
	</p>

	<p class="attribution">
		{#each attributions as s, i (s.id)}
			{#if i > 0}<span aria-hidden="true"> · </span>{/if}
			<a href={s.attribution.lien} target="_blank" rel="noopener">{s.attribution.texte}</a>
		{/each}
		{#each plateformes as p, i (p.id)}
			{#if attributions.length > 0 || i > 0}<span aria-hidden="true"> · </span>{/if}
			<a href="{resolve('/couverture')}#plateforme-{p.id}">Sites de {p.sites.length} communes ({p.nom})</a>
		{/each}
	</p>

	{#await registre.composant(couche, 'Volet') then module}
		{#if module}
			<module.default ctx={registre.contexte(couche)} />
		{/if}
	{:catch}
		<p class="erreur">Le volet n’a pas pu être chargé. Rechargez la page.</p>
	{/await}
</section>

<style>
	.volet {
		display: flex;
		flex-direction: column;
		gap: 10px;
		padding: 12px 14px 14px;
		background: var(--surface);
		border-radius: 10px;
		box-shadow: 0 4px 16px rgb(0 0 0 / 0.2);
		font-size: 14px;
	}
	.tete {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: 16px;
	}
	.interrupteur,
	.permanente {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		color: var(--muted);
	}
	.interrupteur {
		cursor: pointer;
	}
	.interrupteur input {
		width: 18px;
		height: 18px;
		margin: 0;
		accent-color: var(--accent);
	}
	.fermer {
		width: 32px;
		height: 32px;
		margin: -4px -6px -4px 0;
		border: 0;
		border-radius: 50%;
		background: none;
		font-size: 22px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
	.fermer:hover {
		background: var(--bg);
	}
	.voir {
		align-self: flex-start;
		min-height: 44px;
		margin-top: -2px;
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 12px;
		margin: -6px 0 0;
	}
	.couverture {
		font-size: 12px;
		color: var(--muted);
	}
	.attribution {
		margin: -8px 0 0;
		font-size: 12px;
		color: var(--muted);
	}
	.attribution a {
		color: inherit;
	}
	.erreur {
		margin: 0;
		color: var(--erreur);
	}
</style>
