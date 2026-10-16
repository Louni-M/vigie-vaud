<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51), variante C : l'onglet suit les séances. La prochaine séance (ou la dernière) en tête, avec
	 * son ordre du jour déplié ; puis chaque séance passée, avec les objets déposés depuis la précédente. « Au Grand
	 * Conseil » suit, en liste compacte.
	 */
	import type { Commune } from '#lib/types.js';
	import { CONSEILS, auGrandConseil, dateDe, detailsDe, jourLong, objetsDe, seancesDe, type ElementConseil } from './donnees.svelte.js';
	import Ligne from './Ligne.svelte';

	let { commune, ouvrir, nom }: { commune: Commune; ouvrir: (id: string) => void; nom: (s: string) => string } = $props();

	const conseil = CONSEILS.find((c) => c.commune === commune.slug);
	const seances = $derived(seancesDe(commune.slug));
	const objets = $derived(objetsDe(commune.slug));
	const gc = $derived(auGrandConseil(commune.slug));
	const tete = $derived(seances.avenir.at(-1) ?? seances.passees[0]);

	/** Chaque séance passée, avec les objets déposés entre la précédente et elle. */
	const blocs = $derived.by(() => {
		const ps = seances.passees;
		const bs: { s: ElementConseil | null; xs: ElementConseil[] }[] = [];
		const avant = objets.filter((x) => !ps[0] || x.date > ps[0].date);
		if (avant.length) bs.push({ s: null, xs: avant });
		ps.forEach((s, i) => {
			const prec = ps[i + 1];
			bs.push({ s, xs: objets.filter((x) => x.date <= s.date && (!prec || x.date > prec.date)) });
		});
		return bs;
	});
	let nb = $state(4);
	let toutGc = $state(false);
</script>

{#if conseil}
	<h3>{conseil.nom}</h3>
	{#if tete}
		<div class="tete">
			<p class="etiquette">{tete.age < 0 ? 'Prochaine séance' : 'Dernière séance'}</p>
			<button type="button" class="date" onclick={() => ouvrir(tete.id)}>{jourLong.format(dateDe(tete))} ›</button>
			{#await detailsDe(tete)}
				<p class="note">Ordre du jour…</p>
			{:then d}
				{#if d.ordreDuJour.length}
					<ol>
						{#each d.ordreDuJour.slice(0, 8) as p (p.numero + p.titre)}
							<li>{#if p.objet}<button type="button" class="point" onclick={() => ouvrir(p.objet!)}>{p.titre}</button>{:else}{p.titre}{/if}</li>
						{/each}
					</ol>
					{#if d.ordreDuJour.length > 8}<button type="button" class="plus" onclick={() => ouvrir(tete.id)}>Les {d.ordreDuJour.length} points ›</button>{/if}
				{:else}
					<p class="note">Ordre du jour pas encore publié.</p>
				{/if}
			{:catch}
				<p class="note">Ordre du jour indisponible.</p>
			{/await}
		</div>
	{/if}

	{#each blocs.slice(0, nb) as b (b.s?.id ?? 'depuis')}
		<section class="bloc">
			{#if b.s}
				<button type="button" class="seance" onclick={() => ouvrir(b.s!.id)}><span class="pastille">◷</span> Séance du {jourLong.format(dateDe(b.s))}</button>
				{#if b.xs.length}<p class="note">Déposés avant cette séance :</p>{/if}
			{:else}
				<p class="seance-0">Déposés depuis la dernière séance</p>
			{/if}
			<ul>{#each b.xs as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} />{/each}</ul>
		</section>
	{/each}
	{#if blocs.length > nb}<button type="button" class="plus" onclick={() => (nb += 6)}>Séances précédentes</button>{/if}
{/if}

<h3 class="gc">Au Grand Conseil</h3>
<p class="note">Objets dont le titre nomme {commune.nom}, rattachés automatiquement.</p>
{#if gc.length}
	<ul>{#each toutGc ? gc : gc.slice(0, 10) as x (x.id)}<Ligne {x} onclick={() => ouvrir(x.id)} communes={nom} />{/each}</ul>
	{#if gc.length > 10}<button class="plus" type="button" onclick={() => (toutGc = !toutGc)}>{toutGc ? 'Moins' : `Tous (${gc.length})`}</button>{/if}
{:else}
	<p class="note">Aucun objet récent du Grand Conseil ne nomme {commune.nom}.</p>
{/if}

<style>
	h3 { font-size: 15px; margin: 4px 0 6px; }
	h3.gc { margin-top: 22px; padding-top: 12px; border-top: 2px solid var(--line); }
	ul { margin: 0; padding: 0; }
	.tete { padding: 10px 12px; border-radius: 8px; background: #f3ecf7; border-left: 4px solid #7a3e9d; }
	.etiquette { margin: 0; font-size: 12px; font-weight: 600; color: #7a3e9d; }
	.date { padding: 0; border: 0; background: none; font: inherit; font-size: 15px; font-weight: 700; cursor: pointer; text-align: left; }
	ol { margin: 6px 0 0; padding-left: 20px; font-size: 13px; }
	ol li { margin: 2px 0; }
	.point { padding: 0; border: 0; background: none; font: inherit; color: var(--accent); text-align: left; cursor: pointer; text-decoration: underline; }
	.bloc { margin-top: 12px; }
	.seance { display: flex; gap: 6px; align-items: center; width: 100%; padding: 6px 4px; border: 0; border-bottom: 2px solid #2f6f8f; background: none; font: inherit; font-size: 13px; font-weight: 700; color: #2f6f8f; cursor: pointer; text-align: left; }
	.seance-0 { margin: 0; padding: 6px 4px; font-size: 13px; font-weight: 700; color: var(--muted); border-bottom: 2px dashed var(--line); }
	.pastille { display: inline-grid; place-items: center; width: 16px; height: 16px; border-radius: 4px; background: #2f6f8f; color: #fff; font-size: 10px; }
	.note { font-size: 12px; color: var(--muted); margin: 4px 0; }
	.plus { margin-top: 6px; padding: 0; border: 0; background: none; font: inherit; font-size: 13px; color: var(--accent); cursor: pointer; }
</style>
