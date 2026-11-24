<script lang="ts">
	/*
	 * Une rubrique ouverte dans le panneau, assemblée par le registre : en tête le lien de retour au sommaire et le nom
	 * de la rubrique, puis le `Volet` de sa couche (ses filtres et sa liste), et après la liste ses sources : badge de
	 * fraîcheur de chaque source et lien vers la page Couverture, attribution de chaque source tirée de sources.json. Les
	 * sites des communes y sont regroupés par plateforme : un badge et une attribution pour toutes ses communes
	 * couvertes, qui renvoie à sa fiche de la page Couverture ; une commune non couverte n'y figure pas.
	 */
	import { resolve } from '$app/paths';
	import BadgeFraicheur from '#lib/components/BadgeFraicheur.svelte';
	import BadgeSites from '#lib/components/BadgeSites.svelte';
	import { typographier } from '#lib/almanach/typographie.js';
	import type { Source } from '#lib/schema.js';
	import { nomDePlateforme, source } from '#lib/sources.js';
	import type { Registre } from './registre.svelte.js';
	import type { CoucheInscrite, Rubrique } from './types.js';
	import { SOMMAIRE } from './url.js';

	let {
		rubrique,
		couche,
		registre,
		onretour
	}: {
		rubrique: Rubrique;
		couche: CoucheInscrite;
		registre: Registre;
		/** Le lien de retour, d'un clic simple : le panneau revient au sommaire. */
		onretour: (e: MouseEvent) => void;
	} = $props();

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
	const titre = $derived(`volet-${couche.id}-titre`);
</script>

<section class="volet" id="volet-{couche.id}" aria-labelledby={titre}>
	<div class="tete">
		<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- l'adresse vient du registre, qui la construit avec resolve -->
		<a class="retour" href={registre.adressePanneau(SOMMAIRE)} onclick={onretour}
			><span aria-hidden="true">‹ </span>Tous les sujets</a
		>
		<h2 id={titre} tabindex="-1">{rubrique.nom}</h2>
	</div>

	{#await registre.composant(couche, 'Volet') then module}
		{#if module}
			<module.default ctx={registre.contexte(couche)} />
		{/if}
	{:catch}
		<p class="erreur">La liste n’a pas pu être chargée. Rechargez la page.</p>
	{/await}

	<footer class="sources">
		<p class="badges">
			{#each sources as s (s.id)}<BadgeFraicheur source={s} />{/each}
			{#each plateformes as p (p.id)}<BadgeSites plateforme={p.nom} sources={p.sites} />{/each}
			<a class="couverture" href={resolve('/couverture')}>Couverture</a>
		</p>

		<p class="attribution">
			{#each attributions as s, i (s.id)}
				{#if i > 0}<span aria-hidden="true"> · </span>{/if}
				<a href={s.attribution.lien} target="_blank" rel="noopener">{typographier(s.attribution.texte)}</a>
			{/each}
			{#each plateformes as p, i (p.id)}
				{#if attributions.length > 0 || i > 0}<span aria-hidden="true"> · </span>{/if}
				<a href="{resolve('/couverture')}#plateforme-{p.id}"
						>Sites de {p.sites.length}&nbsp;commune{p.sites.length > 1 ? 's' : ''} ({p.nom})</a
					>
			{/each}
		</p>
	</footer>
</section>

<style>
	/* Le volet : la feuille posée sur la carte, un filet d'encre en tête, rien d'autre. */
	.volet {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		padding: var(--space-md) var(--space-md) var(--space-lg);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		font-size: 14px;
	}
	.tete {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 4px;
	}
	.retour {
		font-size: 13px;
		color: var(--color-muted);
	}
	.retour:hover {
		color: var(--color-ink);
		text-decoration-thickness: var(--rule-bar);
	}
	.sources {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		margin-top: var(--space-xs);
		padding-top: var(--space-sm);
		border-top: 1px solid var(--color-rule);
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: var(--text-lg);
		font-weight: 600;
		letter-spacing: var(--tracking-display);
		color: var(--color-ink);
	}
	.badges {
		display: flex;
		flex-wrap: wrap;
		gap: 2px 12px;
		margin: 0;
		font-size: var(--text-xs);
	}
	.couverture {
		font-size: 12px;
		color: var(--color-muted);
	}
	.attribution {
		margin: 0;
		font-size: var(--text-xs);
		color: var(--color-muted);
	}
	.attribution a {
		color: inherit;
	}
	/* Au survol, le lien prend l'encre et son soulignement s'épaissit. */
	.couverture:hover,
	.attribution a:hover {
		color: var(--color-ink);
		text-decoration-thickness: var(--rule-bar);
	}
	.erreur {
		margin: 0;
	}
</style>
