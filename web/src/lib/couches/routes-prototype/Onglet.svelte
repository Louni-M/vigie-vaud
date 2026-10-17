<script lang="ts">
	/*
	 * PROTOTYPE : onglet Routes de la fiche commune, un par variante. A : la portée en tête, puis En cours et À venir,
	 * cartes de restriction. B : les interventions qui touchent la commune, leurs restrictions dedans, la portée au
	 * pied. C : une frise des 6 semaines à venir, une barre par restriction, la portée en note.
	 */
	import { untrack } from 'svelte';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Commune } from '#lib/types.js';
	import ElementA from './ElementA.svelte';
	import ElementB from './ElementB.svelte';
	import {
		aujourdhui,
		joursEntre,
		longueurTexte,
		metresDans,
		parDebut,
		periode,
		plusJours,
		PORTEE,
		routes,
		SORTES,
		type Restriction
	} from './donnees.svelte.js';
	import type { Parametres } from './index.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();
	const commune = untrack(() => ctx.commune) as Commune;
	routes.charger(untrack(() => ctx.communes)).catch(() => {});

	const v = $derived(ctx.parametres.variant);
	const ici = $derived(
		routes.restrictions.filter((r) => r.communes.some((p) => p.commune.slug === commune.slug)).sort(parDebut)
	);
	const enCours = $derived(ici.filter((r) => r.quand === 'en-cours'));
	const aVenir = $derived(ici.filter((r) => r.quand === 'a-venir'));
	const groupes = $derived(
		routes.groupes
			.filter((g) => g.restrictions.some((r) => ici.includes(r)))
			.sort((a, b) => (a.quand === b.quand ? parDebut(a, b) : a.quand === 'en-cours' ? -1 : 1))
	);
	const ouvrir = (r: Restriction) => ctx.ouvrir({ couche: 'routes', element: String(r.id), position: r.milieu });

	// C : frise de 42 jours à partir d'aujourd'hui.
	const JOURS = 42;
	const debutFrise = aujourdhui();
	const pos = (jour: string) => Math.min(100, Math.max(0, (joursEntre(debutFrise, jour) / JOURS) * 100));
	const semaines = Array.from({ length: JOURS / 7 }, (_, i) => plusJours(debutFrise, i * 7));
	const fmtSem = (j: string) => new Date(`${j}T12:00:00Z`).toLocaleDateString('fr-CH', { day: 'numeric', month: 'short', timeZone: 'UTC' });
</script>

{#if !routes.charge}
	<p class="muted">Chargement des restrictions de circulation auprès du canton…</p>
{:else if v === 'A'}
	<p class="portee">{PORTEE}</p>
	<h3>En cours ({enCours.length})</h3>
	{#if enCours.length}
		<ul class="grille">{#each enCours as r (r.id)}<li><ElementA {r} commune={commune.slug} onclick={() => ouvrir(r)} /></li>{/each}</ul>
	{:else}
		<p class="muted">Aucune restriction de circulation en cours sur les routes de {commune.nom} que publie la DGMR.</p>
	{/if}
	<h3>À venir ({aVenir.length})</h3>
	{#if aVenir.length}
		<ul class="grille">{#each aVenir as r (r.id)}<li><ElementA {r} commune={commune.slug} onclick={() => ouvrir(r)} /></li>{/each}</ul>
	{:else}
		<p class="muted">Aucune annoncée.</p>
	{/if}
{:else if v === 'B'}
	<h3>{groupes.length ? `${groupes.length} intervention${groupes.length > 1 ? 's' : ''} sur les routes de ${commune.nom}` : `Rien sur les routes de ${commune.nom}`}</h3>
	{#if !groupes.length}<p class="muted">Aucune restriction de circulation en cours ou annoncée par la DGMR.</p>{/if}
	<ul class="grille">
		{#each groupes as g (g.cle)}
			<li class="groupe">
				<ElementB {g} onclick={() => ouvrir(g.principale)} />
				<ul class="membres">
					{#each g.restrictions as r (r.id)}
						{@const m = metresDans(r, commune.slug)}
						<li style:--c={SORTES[r.sorte].couleur}>
							<button type="button" onclick={() => ouvrir(r)}>
								<span class="trait" class:tirets={r.sorte === 'deviation'}></span>
								{SORTES[r.sorte].nom}
								<span class="muted">
									{m ? `${longueurTexte(m)} ici` : 'hors de la commune'}{r.communes.length > 1 ? ` · ${r.communes.length} communes` : ''}
								</span>
							</button>
						</li>
					{/each}
				</ul>
			</li>
		{/each}
	</ul>
	<p class="portee bas">{PORTEE}</p>
{:else}
	<h3>Les 6 prochaines semaines</h3>
	{#if !ici.length}
		<p class="muted">Aucune restriction de circulation en cours ou annoncée sur les routes de {commune.nom}.<sup>*</sup></p>
	{:else}
		<div class="frise">
			<div class="graduation">
				{#each semaines as s (s)}<span style:left="{pos(s)}%">{fmtSem(s)}</span>{/each}
			</div>
			{#each ici as r (r.id)}
				{@const a = pos(r.debut.jour)}
				{@const b = pos(plusJours(r.fin.jour, 1))}
				<button type="button" class="rang" onclick={() => ouvrir(r)} title={periode(r, true)}>
					<span class="etiquette">
						<strong>{SORTES[r.sorte].nom}</strong> · {r.nom}
					</span>
					<span class="piste">
						<span
							class="barre"
							class:tirets={r.sorte === 'deviation'}
							class:nuit={!!r.plage}
							class:avant={r.debut.jour < debutFrise}
							style:left="{a}%"
							style:width="{Math.max(1.5, b - a)}%"
							style:--c={r.quand === 'en-cours' ? '#c92a2a' : joursEntre(debutFrise, r.debut.jour) <= 7 ? '#f08c00' : '#868e96'}
						></span>
						<span class="aujourdhui"></span>
					</span>
				</button>
			{/each}
		</div>
		<p class="muted petit">Barre hachurée : la nuit seulement. Trait à gauche : aujourd’hui. Survolez une barre pour ses dates.</p>
	{/if}
	<p class="portee note"><sup>*</sup> {PORTEE}</p>
{/if}

<style>
	h3 {
		font-size: 16px;
		margin: 22px 0 8px;
	}
	.portee {
		margin: 0 0 4px;
		padding: 8px 10px;
		border-radius: 8px;
		background: var(--bg);
		border: 1px solid var(--line);
		font-size: 13px;
		line-height: 1.45;
	}
	.portee.bas {
		margin-top: 24px;
	}
	.portee.note {
		margin-top: 24px;
		background: none;
		border: 0;
		padding: 0;
		color: var(--muted);
	}
	.grille {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 10px;
	}
	.membres {
		list-style: none;
		margin: 4px 0 0 12px;
		padding: 0 0 0 10px;
		border-left: 2px solid var(--line);
		display: grid;
		gap: 2px;
	}
	.membres button {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		padding: 4px 2px;
		border: 0;
		background: none;
		font: inherit;
		font-size: 13.5px;
		color: inherit;
		cursor: pointer;
		text-align: left;
	}
	.membres button:hover {
		text-decoration: underline;
	}
	.trait {
		width: 18px;
		height: 4px;
		border-radius: 2px;
		background: var(--c);
	}
	.trait.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 5px, transparent 5px 8px);
	}
	.frise {
		display: grid;
		gap: 6px;
	}
	.graduation {
		position: relative;
		height: 16px;
		margin-left: 0;
		font-size: 11px;
		color: var(--muted);
	}
	.graduation span {
		position: absolute;
		top: 0;
		white-space: nowrap;
	}
	.rang {
		display: grid;
		gap: 3px;
		padding: 0;
		border: 0;
		background: none;
		font: inherit;
		color: inherit;
		text-align: left;
		cursor: pointer;
	}
	.etiquette {
		font-size: 13px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.piste {
		position: relative;
		height: 12px;
		border-radius: 6px;
		background: var(--bg);
		border: 1px solid var(--line);
	}
	.rang:hover .piste {
		border-color: var(--accent);
	}
	.barre {
		position: absolute;
		top: 1px;
		bottom: 1px;
		border-radius: 5px;
		background: var(--c);
	}
	.barre.avant {
		border-top-left-radius: 0;
		border-bottom-left-radius: 0;
	}
	.barre.tirets {
		background: repeating-linear-gradient(90deg, var(--c) 0 6px, transparent 6px 9px);
	}
	.barre.nuit {
		background: repeating-linear-gradient(135deg, var(--c) 0 3px, transparent 3px 6px);
	}
	.aujourdhui {
		position: absolute;
		left: 0;
		top: -3px;
		bottom: -3px;
		width: 2px;
		background: var(--text);
	}
	.muted {
		color: var(--muted);
	}
	.petit {
		font-size: 12.5px;
	}
</style>
