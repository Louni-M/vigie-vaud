<script lang="ts">
	/*
	 * PROTOTYPE (ticket #51) : ce que la couche Conseils ajoute à son volet, sous l'interrupteur, les badges et
	 * l'attribution du registre. A : légende et conseils couverts. B : légende des pastilles et communes les plus
	 * actives. C : un agenda des séances de tous les conseils. Toutes : « Voir sur la carte » sur téléphone (#44).
	 */
	import { untrack } from 'svelte';
	import { MediaQuery } from 'svelte/reactivity';
	import type { Contexte } from '#lib/registre/types.js';
	import { CONSEILS, activite, charger, conseils, dateDe, detailsDe, jourSemaine, nomConseil, objetsDe, seancesDe, type ElementConseil } from './donnees.svelte.js';
	import { ouvrirGrandConseil, proto } from './proto.svelte.js';

	let { ctx }: { ctx: Contexte<undefined> } = $props();
	charger(untrack(() => ctx.communes));
	const telephone = new MediaQuery('(max-width: 760px) and (min-height: 521px)', false);
	const nom = (s: string) => ctx.communes.find((c) => c.slug === s)?.nom ?? s;

	function ouvrirConseil(c: (typeof CONSEILS)[number]) {
		if (!c.commune) {
			if (proto.variante === 'A') return ouvrirGrandConseil();
			if (proto.variante === 'C') return void (proto.agendaConseil = 'VD');
			proto.filQui = 'Grand Conseil';
			proto.vue = 'fil';
			return;
		}
		proto.onglet = 'conseils';
		ctx.ouvrir({ commune: c.commune });
	}

	const actives = $derived(
		[...activite(30)].map(([slug, n]) => ({ slug, ...n, total: n.communal + n.gc })).filter((x) => x.total).sort((a, b) => b.total - a.total)
	);

	/* C : l'agenda */
	const agenda = $derived.by(() => {
		const xs = conseils.elements.filter((x) => x.sorte === 'seance' && (!proto.agendaConseil || CONSEILS.find((c) => c.cle === proto.agendaConseil)?.commune === x.conseil));
		return {
			avenir: xs.filter((x) => x.age < 0).sort((a, b) => b.age - a.age),
			passees: xs.filter((x) => x.age >= 0).sort((a, b) => a.age - b.age).slice(0, 10)
		};
	});
	let deplie = $state<string | null>(null);
	function clicSeance(x: ElementConseil) {
		if (x.conseil) ctx.ouvrir({ couche: 'conseils', element: x.id });
		else deplie = deplie === x.id ? null : x.id;
	}

	function voirSurLaCarte() {
		proto.grisageMobile = true;
		proto.vue = 'carte';
	}
</script>

{#snippet conseilsCouverts()}
	<h3>Conseils couverts</h3>
	<ul class="conseils">
		{#each CONSEILS as c (c.cle)}
			{@const s = seancesDe(c.commune)}
			<li>
				<button type="button" onclick={() => ouvrirConseil(c)}>
					<strong>{c.nom}</strong>
					<span>{c.donne}{#if c.commune}{` · ${objetsDe(c.commune).length} objets récents`}{/if}</span>
					{#if s.avenir.length}<span>Prochaine séance : {jourSemaine.format(dateDe(s.avenir.at(-1)!))}</span>{:else if s.passees[0]}<span>Dernière séance : {jourSemaine.format(dateDe(s.passees[0]))}</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
	<p class="note">Les 297 autres communes : pas de conseil couvert, grisées tant que ce volet est ouvert. Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.</p>
{/snippet}

{#if telephone.current}
	<button type="button" class="voir" onclick={voirSurLaCarte}>Voir sur la carte</button>
{/if}

{#if !conseils.charge}
	<p class="note">Lecture d’OpenParlData…</p>
{:else if proto.variante === 'A'}
	<ul class="legende">
		<li><span class="gc" aria-hidden="true">GC</span> Le Grand Conseil, au Parlement : un clic ouvre sa fiche.</li>
		<li><span class="hdv" aria-hidden="true"></span> Les conseils communaux sont dans la fiche de leur commune, onglet Conseil.</li>
	</ul>
	{@render conseilsCouverts()}
{:else if proto.variante === 'B'}
	<ul class="legende">
		<li><span class="pt fonce" aria-hidden="true">7</span> Objets des 30 derniers jours : conseil communal et Grand Conseil.</li>
		<li><span class="pt clair" aria-hidden="true">2</span> Seulement le Grand Conseil, qui nomme la commune.</li>
		<li><span class="gc" aria-hidden="true">GC</span> Le Grand Conseil : un clic ouvre le fil sur ses objets.</li>
	</ul>
	<h3>Les plus actives (30 jours)</h3>
	<ol class="actives">
		{#each actives.slice(0, 8) as a (a.slug)}
			<li><button type="button" onclick={() => { proto.onglet = 'conseils'; ctx.ouvrir({ commune: a.slug }); }}>{nom(a.slug)}</button> <span>{a.communal ? `${a.communal} au conseil communal, ` : ''}{a.gc} au Grand Conseil</span></li>
		{/each}
	</ol>
	{@render conseilsCouverts()}
{:else}
	<div class="filtre" role="group" aria-label="Conseil">
		<button type="button" aria-pressed={!proto.agendaConseil} onclick={() => (proto.agendaConseil = undefined)}>Tous</button>
		{#each CONSEILS as c (c.cle)}
			<button type="button" aria-pressed={proto.agendaConseil === c.cle} onclick={() => (proto.agendaConseil = c.cle)}>{c.commune ? nom(c.commune) : 'Grand Conseil'}</button>
		{/each}
	</div>
	<h3>À venir</h3>
	{#each agenda.avenir as x (x.id)}
		{@render seance(x)}
	{:else}
		<p class="note">Aucune séance annoncée. Lausanne publie les siennes une semaine avant environ ; le Grand Conseil, après coup.</p>
	{/each}
	<h3>Dernières séances</h3>
	{#each agenda.passees as x (x.id)}{@render seance(x)}{/each}
	<p class="note">Une séance d’un conseil communal s’ouvre dans la fiche de sa commune ; une séance du Grand Conseil se déplie ici.</p>
{/if}

{#snippet seance(x: ElementConseil)}
	<div class="seance">
		<button type="button" onclick={() => clicSeance(x)} aria-expanded={x.conseil ? undefined : deplie === x.id}>
			<span class="jour">{jourSemaine.format(dateDe(x))}</span>
			<span>{nomConseil(x)}</span>
			<span class="fl" aria-hidden="true">{x.conseil ? '›' : deplie === x.id ? '▾' : '▸'}</span>
		</button>
		{#if deplie === x.id}
			{#await detailsDe(x)}
				<p class="note">Ordre du jour…</p>
			{:then d}
				<ol>{#each d.ordreDuJour.slice(0, 15) as p, i (i)}<li>{p.titre}</li>{/each}</ol>
				{#if x.url}<a href={x.url} target="_blank" rel="noopener">Sur vd.ch ›</a>{/if}
			{/await}
		{/if}
	</div>
{/snippet}

<style>
	h3 { font-size: 13px; margin: 14px 0 4px; }
	.note { font-size: 12px; color: var(--muted); }
	.voir { width: 100%; min-height: 40px; margin: 4px 0 8px; border: 1px solid #0b7285; border-radius: 8px; background: #e3f2f4; color: #0b7285; font: inherit; font-weight: 600; cursor: pointer; }
	.legende { list-style: none; margin: 4px 0; padding: 0; font-size: 13px; display: grid; gap: 6px; }
	.legende li { display: flex; gap: 8px; align-items: center; }
	.gc { flex: none; display: grid; place-items: center; width: 26px; height: 22px; background: #0b7285; color: #fff; font-size: 10px; font-weight: 700; clip-path: polygon(50% 0, 100% 28%, 100% 100%, 0 100%, 0 28%); padding-top: 4px; }
	.hdv { flex: none; width: 14px; height: 14px; border-radius: 50%; background: #1f3a5f; border: 2px solid #fff; box-shadow: 0 0 0 1px #1f3a5f; }
	.pt { flex: none; display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; font-size: 11px; font-weight: 700; }
	.pt.fonce { background: #0b7285; }
	.pt.clair { background: #66a9b5; }
	.conseils { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
	.conseils button { display: grid; gap: 1px; width: 100%; padding: 8px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); font: inherit; font-size: 12px; color: var(--muted); text-align: left; cursor: pointer; }
	.conseils button:hover { border-color: #0b7285; }
	.conseils strong { font-size: 14px; color: var(--text); }
	.actives { margin: 0; padding-left: 20px; font-size: 13px; }
	.actives button { padding: 0; border: 0; background: none; font: inherit; font-weight: 600; color: var(--accent); cursor: pointer; }
	.actives span { color: var(--muted); font-size: 12px; }
	.filtre { display: flex; flex-wrap: wrap; gap: 4px; margin: 6px 0; }
	.filtre button { border: 1px solid #0b7285; color: #0b7285; background: var(--surface); border-radius: 999px; padding: 3px 9px; font: inherit; font-size: 12px; cursor: pointer; }
	.filtre button[aria-pressed='true'] { background: #0b7285; color: #fff; }
	.seance { border-bottom: 1px solid var(--line); }
	.seance > button { display: flex; gap: 8px; width: 100%; padding: 6px 2px; border: 0; background: none; font: inherit; font-size: 13px; text-align: left; cursor: pointer; }
	.seance > button:hover { background: var(--bg); }
	.jour { flex: none; width: 92px; font-weight: 600; color: #0b7285; }
	.fl { margin-left: auto; color: var(--muted); }
	.seance ol { margin: 0 0 6px; padding-left: 22px; font-size: 12px; }
	.seance a { font-size: 12px; }
</style>
