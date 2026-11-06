<script lang="ts">
	/*
	 * Volet Routes : sous l'interrupteur, le badge et l'attribution du registre, l'échec de la DGMR s'il y en a un,
	 * avec « Réessayer » ; puis les puces par sorte (qui servent de légende) et En cours / À venir, qui filtrent la
	 * carte comme la liste : ce sont les réglages de la couche (`ctx.parametres`), dans l'adresse (`?sortes=`,
	 * `?etats=`) ; enfin le compte et la liste des restrictions de la zone visible, en cartes de restriction qui
	 * ouvrent la leur, masqués quand la couche est désactivée. La couche ne grise aucune commune.
	 */
	import EchecSource from '#lib/components/EchecSource.svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import { routes } from './donnees.svelte.js';
	import { ETATS, type EtatRestriction } from './etats.js';
	import { ouvrirRestriction, restrictionOuverte } from './index.js';
	import RestrictionCarte from './RestrictionCarte.svelte';
	import { enTirets, SORTES } from './sortes.js';
	import { basculer, sortesDesPuces, visibles as restrictionsVisibles, type Filtres } from './volet.js';

	let { ctx }: { ctx: Contexte<Filtres> } = $props();

	/** Restrictions listées au plus : au-delà, on invite à zoomer. */
	const LISTE_MAX = 150;
	const etats = Object.keys(ETATS) as EtatRestriction[];
	const nombre = new Intl.NumberFormat('fr-CH');

	const f = $derived(ctx.parametres);
	const sortes = $derived(sortesDesPuces(routes.restrictions));
	const visibles = $derived(ctx.active ? restrictionsVisibles(routes.restrictions, f, ctx.zone) : []);
	const ouverte = $derived(restrictionOuverte(ctx.ouvert));

	/** Les états demandés par les puces : chargés, en cours de chargement, ou manqués (la source est en erreur). */
	const charges = $derived(f.etats.filter((e) => routes.chargee(e)));
	const enAttente = $derived(f.etats.filter((e) => !routes.chargee(e)));

	// La carte charge déjà les restrictions ; le volet s'en assure (la promesse est partagée). Un échec est porté par
	// l'état de la source, que « Réessayer » recharge.
	$effect(() => {
		if (ctx.active) routes.charger().catch(() => {});
	});
</script>

<EchecSource source="dgmr-restrictions" message="Les restrictions de circulation n’ont pas pu être chargées" />

<div class="reglages">
	<div class="puces" role="group" aria-label="Sortes affichées (légende de la carte)">
		{#each sortes as s (s)}
			<button
				type="button"
				class="puce"
				class:off={!f.sortes.includes(s)}
				class:tirets={enTirets(s)}
				aria-pressed={f.sortes.includes(s)}
				style:--c={SORTES[s].couleur}
				onclick={() => ctx.regler({ sortes: basculer(f.sortes, s) })}
			>
				<span></span>{SORTES[s].nom}
			</button>
		{/each}
	</div>
	<div class="puces" role="group" aria-label="Restrictions affichées : en cours, à venir">
		{#each etats as e (e)}
			<button
				type="button"
				class="puce etat"
				class:off={!f.etats.includes(e)}
				class:pale={e === 'a_venir'}
				aria-pressed={f.etats.includes(e)}
				onclick={() => ctx.regler({ etats: basculer(f.etats, e) })}
			>
				<span></span>{ETATS[e].nom}
			</button>
		{/each}
	</div>
</div>

{#if ctx.active}
	<div class="zone">
		<p class="compte">
			{#if f.etats.length && !charges.length}
				{#if routes.source.erreur}
					Restrictions non chargées.
				{:else}
					Chargement des restrictions auprès de la DGMR…
				{/if}
			{:else}
				<strong>{nombre.format(visibles.length)}</strong>&nbsp;restriction{visibles.length > 1 ? 's' : ''} de circulation dans la zone affichée
				{#each enAttente as e (e)}
					{#if routes.source.erreur}
						<span class="erreur"> · les restrictions {ETATS[e].minuscules} n’ont pas pu être chargées</span>
					{:else}
						<span class="muted"> · chargement des restrictions {ETATS[e].minuscules}…</span>
					{/if}
				{/each}
			{/if}
		</p>
		{#if !visibles.length && (charges.length || !f.etats.length)}
			<p class="muted vide">
				{#if !f.sortes.length || !f.etats.length}
					Allumez au moins une sorte, et «&nbsp;En cours&nbsp;» ou «&nbsp;À venir&nbsp;», pour afficher la liste.
				{:else}
					Aucune restriction ne correspond à ces puces dans la zone affichée. Dézoomez la carte ou allumez d’autres puces.
				{/if}
			</p>
		{/if}
		<ul class="liste">
			{#each visibles.slice(0, LISTE_MAX) as r (r.id)}
				<li><RestrictionCarte {r} actif={r.id === ouverte} onclick={() => ouvrirRestriction(ctx, r)} /></li>
			{/each}
		</ul>
		{#if visibles.length > LISTE_MAX}
			<p class="muted">… et {nombre.format(visibles.length - LISTE_MAX)}&nbsp;autres&nbsp;: zoomez pour affiner.</p>
		{/if}
	</div>
{/if}

<p class="source">
	Restrictions de circulation lues en direct auprès de la DGMR depuis votre navigateur&nbsp;; ce site ne les conserve pas.
	Surtout les routes cantonales. La signalisation sur place fait foi.
</p>

<style>
	.reglages,
	.zone {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.puces {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.puce {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: 999px;
		border: 1px solid var(--c);
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
		cursor: pointer;
	}
	.puce:hover {
		background: color-mix(in oklab, var(--c), white 88%);
	}
	.puce.off:hover {
		border-color: var(--muted);
		color: var(--text);
	}
	/* Le trait de la légende : la couleur de la sorte, en tirets pour une déviation, comme sur la carte. */
	.puce span {
		width: 16px;
		height: 4px;
		border-radius: 2px;
		background: var(--c);
	}
	.puce.tirets span {
		background: repeating-linear-gradient(90deg, var(--c) 0 4px, transparent 4px 7px);
	}
	.puce.etat {
		--c: var(--accent);
	}
	/* L'à venir est plus pâle sur la carte. */
	.puce.pale span {
		opacity: 0.45;
	}
	.puce.off {
		border-color: var(--line);
		color: var(--muted);
	}
	.puce.off span {
		opacity: 0.25;
	}
	.zone {
		margin-top: 4px;
		padding-top: 10px;
		border-top: 1px solid var(--line);
	}
	.compte {
		margin: 0;
		font-size: 14px;
	}
	.vide {
		margin: 0;
		font-size: 14px;
		line-height: 1.45;
	}
	.liste {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	/*
	 * Jusqu'à 150 cartes : celles hors de l'écran ne sont pas mises en page. Sur la carte elle-même et non sur le
	 * `li`, dont le confinement couperait le contour de la carte active et l'anneau du focus.
	 */
	.liste > li > :global(.carte) {
		content-visibility: auto;
		contain-intrinsic-size: auto 92px;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin: 4px 0 0;
	}
	@media (pointer: coarse) {
		.puce {
			min-height: 44px;
		}
	}
</style>
