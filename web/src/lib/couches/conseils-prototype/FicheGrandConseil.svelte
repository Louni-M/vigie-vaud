<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51), variante A : la fiche du Grand Conseil, en colonne à droite comme une fiche commune.
	 * Dans la vraie couche : l'adresse /grand-conseil, et /grand-conseil?o=… pour un objet ou une séance. Tous les
	 * objets et séances du Grand Conseil s'y ouvrent, y compris ceux qui ne nomment aucune commune (qui, dans le fil,
	 * n'ont sinon que le dépliage sur place).
	 */
	import type { Commune } from '#lib/types.js';
	import { dateDe, element, jourLong, objetsDe, seancesDe } from './donnees.svelte.js';
	import FicheElement from './FicheElement.svelte';
	import Ligne from './Ligne.svelte';
	import { fermerGrandConseil, proto } from './proto.svelte.js';

	let { communes, onfermer, telephone = false }: { communes: readonly Commune[]; onfermer: () => void; telephone?: boolean } = $props();
	const nom = (s: string) => communes.find((c) => c.slug === s)?.nom ?? s;

	const seances = $derived(seancesDe(null));
	const objets = $derived(objetsDe(null));
	let filtre = $state<'tous' | 'sans' | 'avec'>('tous');
	const liste = $derived(objets.filter((x) => filtre === 'tous' || (filtre === 'sans') === !x.communes.length));
	let nb = $state(15);
	const x = $derived(proto.gcElement ? element(proto.gcElement) : null);
	const ouvrir = (id: string) => (proto.gcElement = id);
</script>

<section class="fiche" aria-labelledby="gc-titre">
	<div class="entete">
		<h2 id="gc-titre" tabindex="-1">Grand Conseil</h2>
		<button class="fermer" type="button" aria-label="Fermer la fiche du Grand Conseil" onclick={() => { fermerGrandConseil(); onfermer(); }}>×</button>
	</div>
	<div class="infos">
		<p>Parlement vaudois · place du Château 6, Lausanne</p>
		<p class="adresse">adresse : /grand-conseil{proto.gcElement ? `?o=${proto.gcElement}` : ''}</p>
	</div>
	<div class="onglets" role="tablist">
		<button type="button" role="tab" aria-selected="true">Conseil <span class="badge">OpenParlData</span></button>
	</div>

	<div class="corps">
		{#if x}
			<nav class="fil" aria-label="Fil d’Ariane">
				<button type="button" class="lien" onclick={() => (proto.gcElement = null)}>Conseil</button>
				<span aria-hidden="true">›</span>
				<span aria-current="page">{x.numero ?? x.type}</span>
			</nav>
			{#key x.id}<FicheElement {x} {nom} {ouvrir} />{/key}
		{:else}
			<div class="prochaine">
				<p class="etiquette">Prochaine séance</p>
				{#if seances.avenir.length}
					<button type="button" class="date" onclick={() => ouvrir(seances.avenir.at(-1)!.id)}>{jourLong.format(dateDe(seances.avenir.at(-1)!))} ›</button>
				{:else}
					<p class="vide">Pas encore annoncée.{#if seances.passees[0]}{" "}Dernière : {jourLong.format(dateDe(seances.passees[0]))}.{/if}</p>
				{/if}
			</div>

			<h4>Objets récents</h4>
			<div class="puces" role="radiogroup" aria-label="Communes">
				<button type="button" aria-pressed={filtre === 'tous'} onclick={() => (filtre = 'tous')}>Tous ({objets.length})</button>
				<button type="button" aria-pressed={filtre === 'avec'} onclick={() => (filtre = 'avec')}>Nomment une commune</button>
				<button type="button" aria-pressed={filtre === 'sans'} onclick={() => (filtre = 'sans')}>Sans commune</button>
			</div>
			<ul>{#each liste.slice(0, nb) as y (y.id)}<Ligne x={y} onclick={() => ouvrir(y.id)} communes={nom} />{/each}</ul>
			{#if liste.length > nb}<button class="plus" type="button" onclick={() => (nb += 30)}>Plus ({liste.length - nb})</button>{/if}

			<h4>Séances passées</h4>
			<ul>{#each seances.passees.slice(0, 6) as y (y.id)}<Ligne x={y} onclick={() => ouvrir(y.id)} />{/each}</ul>
		{/if}
		{#if telephone}<p class="note">Sur téléphone : la vue Fiche, comme une commune.</p>{/if}
	</div>
</section>

<style>
	.fiche { display: flex; flex-direction: column; height: 100%; min-width: 0; background: var(--bg); border-left: 1px solid var(--line); }
	.entete { display: flex; align-items: center; gap: 10px; padding: 12px 14px 6px; }
	h2 { flex: 1; margin: 0; font-size: 22px; color: #7a3e9d; }
	h2:focus { outline: none; }
	.fermer { width: 36px; height: 36px; border: 0; border-radius: 50%; background: var(--surface); font-size: 22px; line-height: 1; color: var(--muted); cursor: pointer; }
	.infos { padding: 0 14px 8px; font-size: 13px; color: var(--muted); }
	.infos p { margin: 2px 0 0; }
	.adresse { font-family: ui-monospace, monospace; font-size: 11px; }
	.onglets { display: flex; padding: 0 10px; border-bottom: 1px solid var(--line); }
	.onglets button { padding: 8px 10px 6px; border: 0; border-bottom: 3px solid var(--enquete); background: none; font: inherit; font-size: 14px; font-weight: 600; display: flex; flex-direction: column; align-items: flex-start; }
	.badge { font-size: 11px; font-weight: 400; color: var(--muted); }
	.corps { flex: 1; overflow-y: auto; padding: 12px 14px 32px; font-size: 14px; }
	.prochaine { padding: 8px 10px; border-radius: 8px; background: #f3ecf7; }
	.etiquette { margin: 0; font-size: 12px; font-weight: 600; color: #7a3e9d; }
	.date { padding: 0; border: 0; background: none; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; }
	.vide, .note { margin: 2px 0 0; font-size: 13px; color: var(--muted); }
	h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 14px 0 4px; }
	ul { margin: 0; padding: 0; }
	.puces { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
	.puces button { border: 1px solid #7a3e9d; color: #7a3e9d; background: var(--surface); border-radius: 999px; padding: 3px 9px; font: inherit; font-size: 12px; cursor: pointer; }
	.puces button[aria-pressed='true'] { background: #7a3e9d; color: #fff; }
	.plus { margin-top: 6px; padding: 0; border: 0; background: none; font: inherit; font-size: 13px; color: var(--accent); cursor: pointer; }
	.fil { display: flex; align-items: baseline; gap: 6px; margin: 0 0 12px; color: var(--muted); }
	.lien { padding: 0; border: 0; background: none; font: inherit; color: var(--accent); text-decoration: underline; cursor: pointer; }
</style>
