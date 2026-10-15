<script lang="ts">
	/*
	 * Fiche commune, rendue par le registre en colonne à droite de la carte : en-tête (nom de la commune), puis un
	 * onglet par couche inscrite qui a un `Onglet`, activée ou non. La barre d'onglets est affichée même s'il n'y
	 * a qu'un onglet ; sous le nom de chaque onglet, le badge de fraîcheur de chacune des sources de la couche.
	 * Changer de commune remplace le contenu sur place : l'onglet choisi reste, son contenu est
	 * remonté pour la nouvelle commune.
	 */
	import BadgeFraicheur from '#lib/components/BadgeFraicheur.svelte';
	import { source } from '#lib/sources.js';
	import type { Commune } from '#lib/types.js';
	import type { Registre } from './registre.svelte.js';

	let { registre, commune }: { registre: Registre; commune: Commune } = $props();

	const onglets = $derived(registre.couches.filter((c) => c.composants.Onglet));
	let choisi = $state<string | null>(null);
	const courant = $derived(onglets.find((c) => c.id === choisi) ?? onglets[0]);

	/** Flèches gauche et droite : d'un onglet à l'autre, comme le veut le motif « tabs » de l'ARIA. */
	function clavier(e: KeyboardEvent) {
		const pas = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
		if (!pas || !courant) return;
		e.preventDefault();
		const i = (onglets.indexOf(courant) + pas + onglets.length) % onglets.length;
		choisi = onglets[i].id;
		document.getElementById(`onglet-${choisi}`)?.focus();
	}
</script>

<section class="fiche" aria-labelledby="fiche-titre">
	<div class="entete">
		<h2 id="fiche-titre" tabindex="-1">{commune.nom}</h2>
		<button class="fermer" type="button" aria-label="Fermer la fiche de {commune.nom}" onclick={registre.fermerCommune}>
			×
		</button>
	</div>

	<!-- svelte-ignore a11y_interactive_supports_focus -->
	<div class="onglets" role="tablist" aria-label="Couches de la fiche" tabindex="-1" onkeydown={clavier}>
		{#each onglets as c (c.id)}
			<button
				type="button"
				role="tab"
				id="onglet-{c.id}"
				aria-selected={c === courant}
				aria-controls="panneau-{c.id}"
				tabindex={c === courant ? 0 : -1}
				onclick={() => (choisi = c.id)}
			>
				{c.nom}
				{#each c.sources.map(source) as s (s.id)}<BadgeFraicheur source={s} />{/each}
			</button>
		{/each}
	</div>

	{#if courant}
		<div class="corps" role="tabpanel" id="panneau-{courant.id}" aria-labelledby="onglet-{courant.id}">
			{#key `${courant.id}:${commune.slug}`}
				{#await registre.composant(courant, 'Onglet') then module}
					{#if module}<module.default ctx={registre.contexte(courant)} />{/if}
				{:catch}
					<p class="erreur">L’onglet n’a pas pu être chargé. Rechargez la page.</p>
				{/await}
			{/key}
		</div>
	{/if}
</section>

<style>
	.fiche {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-width: 0;
		background: var(--bg);
		border-left: 1px solid var(--line);
	}
	.entete {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 12px 14px 6px;
	}
	h2 {
		flex: 1;
		margin: 0;
		font-size: 22px;
	}
	h2:focus {
		outline: none;
	}
	.fermer {
		width: 36px;
		height: 36px;
		border: 0;
		border-radius: 50%;
		background: var(--surface);
		font-size: 22px;
		line-height: 1;
		color: var(--muted);
		cursor: pointer;
	}
	.fermer:hover {
		color: var(--text);
	}
	.onglets {
		display: flex;
		padding: 0 10px;
		border-bottom: 1px solid var(--line);
		overflow-x: auto;
	}
	.onglets button {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 1px;
		padding: 8px 10px 6px;
		border: 0;
		border-bottom: 3px solid transparent;
		background: none;
		font: inherit;
		font-size: 14px;
		font-weight: 600;
		color: var(--muted);
		cursor: pointer;
		white-space: nowrap;
	}
	.onglets button[aria-selected='true'] {
		color: var(--text);
		border-bottom-color: var(--enquete);
	}
	.corps {
		flex: 1;
		overflow-y: auto;
		padding: 12px 14px 32px;
		font-size: 14px;
	}
	.erreur {
		color: var(--erreur);
	}
</style>
