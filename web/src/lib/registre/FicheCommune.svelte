<script lang="ts">
	/*
	 * Fiche commune, rendue par le registre en colonne à droite de la carte : en-tête (nom de la commune, adresse de
	 * son hôtel de ville ou « position approximative », anciennes communes et anciens noms), puis un
	 * onglet par couche inscrite qui a un `Onglet`, activée ou non. La barre d'onglets est affichée même s'il n'y
	 * a qu'un onglet ; sous le nom de chaque onglet, le badge de fraîcheur de chacune des sources de la couche.
	 * Changer de commune remplace le contenu sur place : l'onglet choisi reste, son contenu est
	 * remonté pour la nouvelle commune.
	 *
	 * L'élément ouvert s'affiche dans l'onglet de sa couche, sous le fil « Permis › n° 248845 » : l'`Onglet` reste
	 * monté, caché, pour retrouver sa place quand on ferme l'élément ; le focus revient alors sur l'onglet.
	 */
	import { tick } from 'svelte';
	import BadgeFraicheur from '#lib/components/BadgeFraicheur.svelte';
	import { source } from '#lib/sources.js';
	import type { Commune } from '#lib/types.js';
	import { enteteFiche } from './entete.js';
	import type { Registre } from './registre.svelte.js';

	let { registre, commune }: { registre: Registre; commune: Commune } = $props();

	const entete = $derived(enteteFiche(commune));

	const onglets = $derived(registre.couches.filter((c) => c.composants.Onglet));
	let choisi = $state<string | null>(null);
	/** Couche de l'élément ouvert, quand elle a un onglet et une `Fiche` pour l'y afficher. */
	const avecFiche = $derived(
		onglets.find((c) => c.id === registre.ouvert?.couche && c.composants.Fiche) ?? null
	);
	const courant = $derived(avecFiche ?? onglets.find((c) => c.id === choisi) ?? onglets[0]);
	const element = $derived(avecFiche === courant ? registre.ouvert : null);

	/** Défilement de l'onglet quand l'élément s'ouvre, rétabli quand il se ferme. */
	let corps: HTMLElement | undefined = $state();
	let defilement = 0;
	let precedent: string | null = null;
	$effect.pre(() => {
		const cle = element ? `${element.couche}:${element.element}` : null;
		if (cle && !precedent && corps) defilement = corps.scrollTop;
		const ferme = precedent !== null && cle === null;
		precedent = cle;
		if (!ferme || !courant) return;
		const id = courant.id;
		// Fermer l'élément : retour à sa place dans l'onglet, focus sur le titre de l'onglet.
		tick().then(() => {
			if (corps) corps.scrollTop = defilement;
			document.getElementById(`onglet-${id}`)?.focus();
		});
	});

	/** Flèches gauche et droite : d'un onglet à l'autre, comme le veut le motif « tabs » de l'ARIA. */
	function clavier(e: KeyboardEvent) {
		const pas = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
		if (!pas || !courant) return;
		e.preventDefault();
		const i = (onglets.indexOf(courant) + pas + onglets.length) % onglets.length;
		choisi = onglets[i].id;
		document.getElementById(`onglet-${choisi}`)?.focus();
	}

	/** Choisir un autre onglet ferme l'élément ouvert ; le sien ramène à son contenu. */
	function choisir(id: string) {
		choisi = id;
		if (element) registre.fermer();
	}
</script>

<section class="fiche" aria-labelledby="fiche-titre">
	<div class="entete">
		<h2 id="fiche-titre" tabindex="-1">{commune.nom}</h2>
		<button class="fermer" type="button" aria-label="Fermer la fiche de {commune.nom}" onclick={registre.fermerCommune}>
			×
		</button>
	</div>
	<div class="infos">
		{#if entete.siege}
			<p>Hôtel de ville : {entete.siege}</p>
		{:else}
			<p class="approximative">Hôtel de ville : position approximative</p>
		{/if}
		{#each entete.anciens as ligne (ligne)}<p>{ligne}</p>{/each}
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
				onclick={() => choisir(c.id)}
			>
				{c.nom}
				{#each c.sources.map(source) as s (s.id)}<BadgeFraicheur source={s} />{/each}
			</button>
		{/each}
	</div>

	{#if courant}
		<div class="corps" role="tabpanel" id="panneau-{courant.id}" aria-labelledby="onglet-{courant.id}" bind:this={corps}>
			{#key `${courant.id}:${commune.slug}`}
				<div hidden={element !== null}>
					{#await registre.composant(courant, 'Onglet') then module}
						{#if module}<module.default ctx={registre.contexte(courant)} />{/if}
					{:catch}
						<p class="erreur">L’onglet n’a pas pu être chargé. Rechargez la page.</p>
					{/await}
				</div>
			{/key}
			{#if element}
				<nav class="fil" aria-label="Fil d’Ariane">
					<button type="button" class="lien" onclick={registre.fermer}>{courant.nom}</button>
					<span aria-hidden="true">›</span>
					<span aria-current="page">n° {element.element}</span>
				</nav>
				{#key `${element.couche}:${element.element}`}
					{#await registre.composant(courant, 'Fiche') then module}
						{#if module}<module.default ctx={registre.contexte(courant)} />{/if}
					{:catch}
						<p class="erreur">La fiche n’a pas pu être chargée. Rechargez la page.</p>
					{/await}
				{/key}
			{/if}
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
	.infos {
		padding: 0 14px 8px;
		font-size: 13px;
		color: var(--muted);
	}
	.infos p {
		margin: 2px 0 0;
	}
	/* Mention discrète : le marqueur n'est pas sur le siège de l'administration. */
	.approximative {
		font-style: italic;
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
	.fil {
		display: flex;
		align-items: baseline;
		gap: 6px;
		margin: 0 0 12px;
		font-size: 14px;
		color: var(--muted);
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
	.erreur {
		color: var(--erreur);
	}
</style>
