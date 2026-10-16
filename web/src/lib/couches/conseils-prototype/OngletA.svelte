<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51), variante A : l'onglet en sections empilées. Le conseil communal (prochaine séance,
	 * objets récents, séances passées), puis « Au Grand Conseil » (les 10 derniers objets qui nomment la commune).
	 * Pour une commune non couverte, le registre met « Non couvert » en tête et seule la section du Grand Conseil suit.
	 */
	import type { Commune } from '#lib/types.js';
	import { CONSEILS, auGrandConseil, dateDe, jourLong, objetsDe, seancesDe } from './donnees.svelte.js';
	import Ligne from './Ligne.svelte';
	import TeteSeance from './TeteSeance.svelte';

	let { commune, ouvrir, nom }: { commune: Commune; ouvrir: (id: string) => void; nom: (s: string) => string } = $props();

	const conseil = CONSEILS.find((c) => c.commune === commune.slug);
	const seances = $derived(seancesDe(commune.slug));
	const objets = $derived(objetsDe(commune.slug));
	const gc = $derived(auGrandConseil(commune.slug));
	let tousObjets = $state(false);
	let toutesSeances = $state(false);
	let toutGc = $state(false);
</script>

{#if conseil}
	<h3>{conseil.nom}</h3>
	{#if conseil.donne === 'séances seulement'}<p class="note">OpenParlData ne donne que ses séances, pas ses objets.</p>{/if}

	<TeteSeance conseil={commune.slug} {ouvrir} />

	{#if objets.length}
		<h4>Objets récents</h4>
		<ul>{#each tousObjets ? objets : objets.slice(0, 8) as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} />{/each}</ul>
		{#if objets.length > 8}<button class="plus" type="button" onclick={() => (tousObjets = !tousObjets)}>{tousObjets ? 'Moins' : `Tous les objets (${objets.length})`}</button>{/if}
	{/if}

	<h4>Séances passées</h4>
	<ul>{#each toutesSeances ? seances.passees : seances.passees.slice(0, 4) as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} />{/each}</ul>
	{#if seances.passees.length > 4}<button class="plus" type="button" onclick={() => (toutesSeances = !toutesSeances)}>{toutesSeances ? 'Moins' : `Toutes les séances (${seances.passees.length})`}</button>{/if}
{/if}

<h3 class="gc">Au Grand Conseil</h3>
<p class="note">Objets dont le titre nomme {commune.nom}, rattachés automatiquement.</p>
{#if gc.length}
	<ul>{#each toutGc ? gc : gc.slice(0, 10) as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} communes={nom} />{/each}</ul>
	{#if gc.length > 10}<button class="plus" type="button" onclick={() => (toutGc = !toutGc)}>{toutGc ? 'Moins' : `Tous (${gc.length})`}</button>{/if}
{:else}
	<p class="vide">Aucun objet récent du Grand Conseil ne nomme {commune.nom}.</p>
{/if}

<style>
	h3 { font-size: 15px; margin: 4px 0 6px; }
	h3.gc { margin-top: 22px; padding-top: 12px; border-top: 2px solid var(--line); }
	h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 14px 0 2px; }
	ul { margin: 0; padding: 0; }
	.prochaine { padding: 8px 10px; border-radius: 8px; background: #e3f2f4; }
	.etiquette { margin: 0; font-size: 12px; font-weight: 600; color: #0b7285; }
	.lien-carte { padding: 0; border: 0; background: none; font: inherit; font-size: 15px; font-weight: 600; cursor: pointer; text-align: left; }
	.note, .vide { font-size: 12px; color: var(--muted); margin: 2px 0 6px; }
	.prochaine .vide { margin: 2px 0 0; font-size: 13px; }
	.plus { margin-top: 4px; padding: 0; border: 0; background: none; font: inherit; font-size: 13px; color: var(--accent); cursor: pointer; }
</style>
