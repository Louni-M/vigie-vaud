<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51), variante B : l'onglet est partagé en deux, « Conseil communal | Au Grand Conseil », avec
	 * un compteur chacun ; dans le conseil communal, une liste unique par mois où objets et séances se mêlent, et des
	 * puces Objets · Séances. Pour une commune non couverte, on arrive sur « Au Grand Conseil ».
	 */
	import type { Commune } from '#lib/types.js';
	import { CONSEILS, auGrandConseil, dateDe, duConseil, type ElementConseil } from './donnees.svelte.js';
	import Ligne from './Ligne.svelte';

	let { commune, ouvrir, nom }: { commune: Commune; ouvrir: (id: string) => void; nom: (s: string) => string } = $props();

	const conseil = CONSEILS.find((c) => c.commune === commune.slug);
	let partie = $state<'communal' | 'gc'>(conseil ? 'communal' : 'gc');
	let types = $state<('objet' | 'seance')[]>(['objet', 'seance']);
	const communal = $derived(duConseil(commune.slug).sort((a, b) => a.age - b.age));
	const gc = $derived(auGrandConseil(commune.slug));
	const liste = $derived(partie === 'gc' ? gc : communal.filter((x) => types.includes(x.sorte)));

	const mois = new Intl.DateTimeFormat('fr-CH', { month: 'long', year: 'numeric' });
	function parMois(xs: ElementConseil[]) {
		const g: { mois: string; xs: ElementConseil[] }[] = [];
		for (const x of xs) {
			const m = x.age < 0 ? 'À venir' : mois.format(dateDe(x));
			if (g.at(-1)?.mois === m) g.at(-1)!.xs.push(x);
			else g.push({ mois: m, xs: [x] });
		}
		return g;
	}
	const basculer = (t: 'objet' | 'seance') => (types = types.includes(t) ? types.filter((x) => x !== t) : [...types, t]);
</script>

<div class="parties" role="radiogroup" aria-label="Conseil">
	<button type="button" role="radio" aria-checked={partie === 'communal'} disabled={!conseil} onclick={() => (partie = 'communal')}>
		Conseil communal <span class="n">{conseil ? communal.length : '–'}</span>
	</button>
	<button type="button" role="radio" aria-checked={partie === 'gc'} onclick={() => (partie = 'gc')}>
		Au Grand Conseil <span class="n">{gc.length}</span>
	</button>
</div>

{#if partie === 'communal' && conseil}
	<div class="puces">
		<button type="button" aria-pressed={types.includes('objet')} onclick={() => basculer('objet')}>§ Objets</button>
		<button type="button" aria-pressed={types.includes('seance')} onclick={() => basculer('seance')}>◷ Séances</button>
		{#if conseil.donne === 'séances seulement'}<span class="note">séances seulement</span>{/if}
	</div>
{:else if partie === 'gc'}
	<p class="note">Objets du Grand Conseil dont le titre nomme {commune.nom}, rattachés automatiquement.</p>
{/if}

{#each parMois(liste) as g (g.mois)}
	<h4>{g.mois}</h4>
	<ul>{#each g.xs as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} communes={partie === 'gc' ? nom : undefined} />{/each}</ul>
{:else}
	<p class="note">Rien ces derniers mois.</p>
{/each}

<style>
	.parties { display: flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; margin-bottom: 8px; }
	.parties button { flex: 1; padding: 8px 6px; border: 0; background: var(--surface); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; color: var(--muted); }
	.parties button[aria-checked='true'] { background: #7a3e9d; color: #fff; }
	.parties button:disabled { cursor: default; opacity: 0.5; }
	.n { display: inline-block; min-width: 18px; padding: 0 5px; margin-left: 4px; border-radius: 999px; background: rgb(0 0 0 / 0.12); font-size: 11px; }
	.puces { display: flex; gap: 6px; align-items: center; margin-bottom: 4px; }
	.puces button { border: 1px solid #7a3e9d; color: #7a3e9d; background: var(--surface); border-radius: 999px; padding: 3px 10px; font: inherit; font-size: 12px; cursor: pointer; }
	.puces button[aria-pressed='true'] { background: #7a3e9d; color: #fff; }
	h4 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 12px 0 2px; }
	ul { margin: 0; padding: 0; }
	.note { font-size: 12px; color: var(--muted); margin: 2px 0 6px; }
</style>
