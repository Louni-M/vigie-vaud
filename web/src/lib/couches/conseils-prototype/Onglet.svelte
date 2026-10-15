<script lang="ts">
	// PROTOTYPE (ticket #45) : onglet Conseil factice. Le conseil communal, puis « Au Grand Conseil ».
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Commune } from '#lib/types.js';
	import { ELEMENTS, dateDe, type ElementConseil } from './donnees.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	const commune = untrack(() => ctx.commune) as Commune;
	const jour = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'long' });

	const tri = (a: ElementConseil, b: ElementConseil) => a.age - b.age;
	const communal = ELEMENTS.filter((x) => x.conseil === commune.slug).sort(tri);
	const grandConseil = ELEMENTS.filter((x) => x.conseil === null && x.communes.includes(commune.slug)).sort(tri);
	const ouvrir = (x: ElementConseil) => ctx.ouvrir({ couche: 'conseils', element: x.id });
</script>

{#snippet liste(xs: ElementConseil[])}
	<ul>
		{#each xs as x (x.id)}
			<li>
				<button type="button" onclick={() => ouvrir(x)}>
					<span class="type">{x.type} · {jour.format(dateDe(x))}</span>
					<span class="titre">{x.sorte === 'seance' ? x.titre : x.titre}</span>
				</button>
			</li>
		{/each}
	</ul>
{/snippet}

<h3>Conseil communal</h3>
{#if communal.length}{@render liste(communal)}{:else}<p class="vide">Rien de nouveau.</p>{/if}
<h3>Au Grand Conseil</h3>
{#if grandConseil.length}{@render liste(grandConseil)}{:else}<p class="vide">{commune.nom} n’est citée dans aucun objet récent.</p>{/if}

<style>
	h3 { font-size: 14px; margin: 14px 0 6px; }
	ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
	button { display: grid; gap: 2px; width: 100%; text-align: left; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); font: inherit; cursor: pointer; }
	button:hover { border-color: #7a3e9d; }
	.type { font-size: 12px; color: #7a3e9d; font-weight: 600; }
	.titre { font-size: 14px; }
	.vide { font-size: 13px; color: var(--muted); }
</style>
