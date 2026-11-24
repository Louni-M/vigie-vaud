<script lang="ts">
	/*
	 * Le sommaire, ce que montre le panneau à l'arrivée : une ligne par rubrique que déclarent les couches, dans l'ordre
	 * de leur rang, avec son nom, sa phrase et son nombre. Chaque ligne est un lien : celle d'une rubrique à volet
	 * l'ouvre dans le panneau, celle d'une rubrique à fiche propre ouvre sa fiche à droite, et reste marquée tant que
	 * cette fiche est ouverte. Un clic simple passe par le registre ; Cmd/Ctrl-clic ou le clic du milieu ouvrent le lien
	 * dans un nouvel onglet. Un nombre qui se charge garde la hauteur de sa ligne ; une ligne à zéro reste un lien.
	 */
	import type { Commune } from '#lib/types.js';
	import { cheminFiche, clicSimple } from './liens.js';
	import type { Registre } from './registre.svelte.js';
	import { etatDuCompte, phraseCompte, rubriquesDuSommaire } from './rubriques.js';
	import type { Rubrique } from './types.js';

	let {
		registre,
		communes,
		onouvrir
	}: {
		registre: Registre;
		communes: readonly Commune[];
		/** Une rubrique à volet est choisie (son identifiant) : le panneau l'ouvre. */
		onouvrir: (id: string) => void;
	} = $props();

	const rubriques = $derived(rubriquesDuSommaire(registre.couches));

	const lien = (r: Rubrique) =>
		r.fiche ? cheminFiche(registre.couches, { fiche: r.fiche }) : registre.adressePanneau(r.id);

	/** La fiche propre de la rubrique est celle qui est ouverte à droite. */
	const ouverte = (r: Rubrique) =>
		r.fiche !== undefined && registre.fiche !== null && 'fiche' in registre.fiche && registre.fiche.fiche === r.fiche;

	function ouvrirAuClic(e: MouseEvent, r: Rubrique) {
		if (!clicSimple(e)) return;
		e.preventDefault();
		if (r.fiche) registre.ouvrir({ fiche: r.fiche });
		else onouvrir(r.id);
	}
</script>

<section class="sommaire" aria-labelledby="sommaire-titre">
	<h2 id="sommaire-titre" tabindex="-1">Ce que montre Vigie Vaud</h2>
	<ul>
		{#each rubriques as { rubrique: r } (r.id)}
			<li>
				<!-- eslint-disable svelte/no-navigation-without-resolve -- l'adresse vient du registre (adressePanneau, cheminFiche), qui la construit avec resolve -->
				<a
					class="ligne"
					data-rubrique={r.id}
					href={lien(r)}
					aria-current={ouverte(r) ? 'page' : undefined}
					onclick={(e) => ouvrirAuClic(e, r)}
				>
					<span class="nom">{r.nom}</span>
					<span class="phrase">{r.phrase}</span>
					<span class="compte">
						{#await registre.compteur(r)}
							<span class="attente">Chargement du nombre…</span>
						{:then compter}
							{@const e = etatDuCompte(r, compter, registre.zone, communes)}
							{#if e.etat === 'nombre'}
								{@const p = phraseCompte(r, e.nombre)}
								{#if p.nombre}<strong>{p.nombre}</strong>{/if}{p.texte}
							{:else if e.etat === 'chargement'}
								<span class="attente">Chargement du nombre…</span>
							{:else}
								<span class="indisponible">Nombre indisponible pour le moment</span>
							{/if}
						{:catch}
							<span class="indisponible">Nombre indisponible pour le moment</span>
						{/await}
					</span>
				</a>
				<!-- eslint-enable svelte/no-navigation-without-resolve -->
			</li>
		{/each}
	</ul>
</section>

<style>
	.sommaire {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		padding: var(--space-md) var(--space-md) var(--space-sm);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		font-size: 14px;
	}
	h2 {
		margin: 0;
		font-size: var(--text-lg);
		font-weight: 600;
		letter-spacing: var(--tracking-display);
		color: var(--color-ink);
	}
	ul {
		display: flex;
		flex-direction: column;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li + li {
		border-top: 1px solid var(--color-rule);
	}
	.ligne {
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 10px 6px;
		margin: 0 -6px;
		color: var(--color-ink-2);
		text-decoration: none;
	}
	.ligne:hover {
		background: var(--color-paper);
	}
	.ligne[aria-current] {
		box-shadow: inset var(--rule-bar) 0 0 var(--color-accent);
	}
	.nom {
		font-size: 16px;
		font-weight: 600;
		color: var(--color-ink);
	}
	.ligne:hover .nom {
		text-decoration: underline;
		text-decoration-color: var(--color-accent);
		text-decoration-thickness: var(--rule-bar);
	}
	.phrase {
		line-height: 1.35;
	}
	/* Une ligne garde sa hauteur pendant que son nombre se charge. */
	.compte {
		min-height: 1.4em;
		font-size: 13px;
		color: var(--color-muted);
	}
	.compte strong {
		color: var(--color-ink);
	}
</style>
