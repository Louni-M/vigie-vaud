<script lang="ts">
	/*
	 * PROTOTYPE : volet Routes, un par variante. A : légende par sorte (puces qui filtrent), en cours / à venir,
	 * liste des restrictions de la zone. B : légende en deux traits, liste des groupes de la zone. C : horizon
	 * (aujourd'hui, 7 j, 30 j, tout), légende par échéance, agenda de la zone par jour de début.
	 */
	import type { Contexte } from '#lib/registre/types.js';
	import ElementA from './ElementA.svelte';
	import ElementB from './ElementB.svelte';
	import ElementC from './ElementC.svelte';
	import {
		jourCourt,
		parDebut,
		retenue,
		routes,
		SORTES,
		SORTES_ORDRE,
		visible,
		type Quand,
		type Restriction,
		type Sorte
	} from './donnees.svelte.js';
	import type { Parametres } from './index.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	const v = $derived(ctx.parametres.variant);
	const dansZone = $derived(routes.restrictions.filter((r) => visible(r, ctx.zone) && retenue(r, v)));
	const ouvert = $derived(ctx.ouvert?.couche === 'routes' ? Number(ctx.ouvert.element) : null);

	const ouvrir = (r: Restriction) => ctx.ouvrir({ couche: 'routes', element: String(r.id), position: r.milieu });

	const presentes = $derived(SORTES_ORDRE.filter((s) => routes.restrictions.some((r) => r.sorte === s)));
	const basculer = <T,>(liste: T[], x: T) => (liste.includes(x) ? liste.filter((y) => y !== x) : [...liste, x]);

	// B : un groupe est dans la zone dès qu'une de ses restrictions l'est.
	const groupes = $derived(
		routes.groupes
			.filter((g) => routes.quand.includes(g.quand) && g.restrictions.some((r) => dansZone.includes(r)))
			.sort((a, b) => (a.quand === b.quand ? parDebut(a, b) : a.quand === 'en-cours' ? -1 : 1))
	);

	// C : en cours d'abord (fin la plus proche), puis à venir par jour de début.
	const enCours = $derived(dansZone.filter((r) => r.quand === 'en-cours').sort((a, b) => a.fin.jour.localeCompare(b.fin.jour)));
	const parJour = $derived(
		Object.entries(
			Object.groupBy(
				dansZone.filter((r) => r.quand === 'a-venir').sort(parDebut),
				(r) => r.debut.jour
			) as Record<string, Restriction[]>
		)
	);
	const HORIZONS: [number | null, string][] = [
		[0, 'Aujourd’hui'],
		[7, '7 jours'],
		[30, '30 jours'],
		[null, 'Tout']
	];
	const QUAND: [Quand, string][] = [
		['en-cours', 'En cours'],
		['a-venir', 'À venir']
	];
</script>

{#if routes.erreur}
	<p class="erreur">Les restrictions n’ont pas pu être chargées ({routes.erreur}).</p>
{/if}

{#if v === 'A'}
	<div class="puces" role="group" aria-label="Sortes affichées (légende de la carte)">
		{#each presentes as s (s)}
			<button
				type="button"
				class="puce"
				class:off={!routes.sortes.includes(s)}
				class:tirets={s === 'deviation'}
				style:--c={SORTES[s].couleur}
				aria-pressed={routes.sortes.includes(s)}
				onclick={() => (routes.sortes = basculer(routes.sortes, s as Sorte))}
			>
				<span></span>{SORTES[s].nom}
			</button>
		{/each}
	</div>
	<div class="puces" role="group" aria-label="Quand">
		{#each QUAND as [q, nom] (q)}
			<button type="button" class="puce neutre" class:off={!routes.quand.includes(q)} aria-pressed={routes.quand.includes(q)} onclick={() => (routes.quand = basculer(routes.quand, q))}>
				{nom}{q === 'a-venir' ? ' (pâle)' : ''}
			</button>
		{/each}
	</div>
	{#if ctx.active}
		<div class="zone">
			<p class="compte">
				{#if !routes.charge}Chargement des restrictions auprès du canton…
				{:else}<strong>{dansZone.length}</strong> restriction{dansZone.length > 1 ? 's' : ''} de circulation dans la zone affichée{/if}
			</p>
			<ul class="liste">
				{#each dansZone.toSorted((a, b) => (a.quand === b.quand ? parDebut(a, b) : a.quand === 'en-cours' ? -1 : 1)) as r (r.id)}
					<li><ElementA {r} actif={r.id === ouvert} onclick={() => ouvrir(r)} /></li>
				{/each}
			</ul>
		</div>
	{/if}
{:else if v === 'B'}
	<div class="legende">
		<p><span class="trait" style:--c={SORTES.fermeture.couleur}></span> La route touchée : fermeture, feux ou restriction, en couleur.</p>
		<p><span class="trait tirets" style:--c={SORTES.deviation.couleur}></span> Sa déviation, au survol ou à l’ouverture.</p>
		<p class="muted">Au petit zoom, un point par intervention ; zoomez pour voir les routes.</p>
	</div>
	<div class="puces" role="group" aria-label="Quand">
		{#each QUAND as [q, nom] (q)}
			<button type="button" class="puce neutre" class:off={!routes.quand.includes(q)} aria-pressed={routes.quand.includes(q)} onclick={() => (routes.quand = basculer(routes.quand, q))}>{nom}</button>
		{/each}
	</div>
	{#if ctx.active}
		<div class="zone">
			<p class="compte">
				{#if !routes.charge}Chargement…
				{:else}<strong>{groupes.length}</strong> intervention{groupes.length > 1 ? 's' : ''} sur les routes de la zone affichée{/if}
			</p>
			<ul class="liste">
				{#each groupes as g (g.cle)}
					<li>
						<ElementB {g} actif={g.restrictions.some((r) => r.id === ouvert)} onclick={() => ouvrir(g.principale)} />
					</li>
				{/each}
			</ul>
		</div>
	{/if}
{:else}
	<div class="segments" role="radiogroup" aria-label="Horizon">
		{#each HORIZONS as [h, nom] (nom)}
			<button type="button" role="radio" aria-checked={routes.horizon === h} class:choisi={routes.horizon === h} onclick={() => (routes.horizon = h)}>{nom}</button>
		{/each}
	</div>
	<p class="echeances">
		<span style:--c="#c92a2a">En cours</span>
		<span style:--c="#f08c00">Commence d’ici 7 jours</span>
		<span style:--c="#868e96">Plus tard</span>
		<span class="muted">· tirets : déviation</span>
	</p>
	{#if ctx.active}
		<div class="zone agenda">
			{#if !routes.charge}<p class="compte">Chargement…</p>{/if}
			{#if enCours.length}
				<h3>En cours ({enCours.length})</h3>
				{#each enCours as r (r.id)}<ElementC {r} actif={r.id === ouvert} onclick={() => ouvrir(r)} />{/each}
			{/if}
			{#each parJour as [jour, rs] (jour)}
				<h3 class="jour">{jourCourt(jour)}</h3>
				{#each rs as r (r.id)}<ElementC {r} actif={r.id === ouvert} onclick={() => ouvrir(r)} />{/each}
			{/each}
			{#if routes.charge && !dansZone.length}<p class="muted">Rien dans la zone affichée pour cet horizon.</p>{/if}
		</div>
	{/if}
{/if}

<p class="source">Restrictions publiées par la DGMR, consultées en direct depuis votre navigateur ; ce site ne les stocke pas. Surtout les routes cantonales.</p>

<style>
	.puces {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.puce {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		border-radius: 999px;
		border: 1px solid var(--c, var(--line));
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
		cursor: pointer;
	}
	.puce span {
		width: 16px;
		height: 4px;
		border-radius: 2px;
		background: var(--c);
	}
	.puce.tirets span {
		background: repeating-linear-gradient(90deg, var(--c) 0 4px, transparent 4px 7px);
	}
	.puce.neutre {
		--c: var(--accent);
	}
	.puce.off {
		border-color: var(--line);
		color: var(--muted);
	}
	.puce.off span {
		opacity: 0.3;
	}
	.legende p {
		margin: 0 0 4px;
		font-size: 13.5px;
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.trait {
		flex: none;
		width: 22px;
		height: 5px;
		border-radius: 3px;
		background: var(--c);
	}
	.trait.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 5px, transparent 5px 8px);
	}
	.segments {
		display: flex;
		border: 1px solid var(--line);
		border-radius: 10px;
		overflow: hidden;
	}
	.segments button {
		flex: 1;
		padding: 8px 4px;
		border: 0;
		border-right: 1px solid var(--line);
		background: var(--surface);
		font: inherit;
		font-size: 13px;
		color: inherit;
		cursor: pointer;
	}
	.segments button:last-child {
		border-right: 0;
	}
	.segments .choisi {
		background: var(--accent);
		color: #fff;
	}
	.echeances {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		margin: 0;
		font-size: 12.5px;
	}
	.echeances span[style] {
		display: inline-flex;
		align-items: center;
		gap: 5px;
	}
	.echeances span[style]::before {
		content: '';
		width: 14px;
		height: 4px;
		border-radius: 2px;
		background: var(--c);
	}
	.zone {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding-top: 10px;
		border-top: 1px solid var(--line);
	}
	.agenda {
		gap: 0;
	}
	.agenda h3 {
		margin: 12px 0 2px;
		font-size: 13px;
		color: var(--muted);
	}
	.agenda h3.jour {
		text-transform: capitalize;
	}
	.compte {
		margin: 0;
		font-size: 14px;
	}
	.liste {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		color: var(--erreur);
	}
	.source {
		margin: 4px 0 0;
		font-size: 12.5px;
		color: var(--muted);
	}
</style>
