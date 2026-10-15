<script lang="ts">
	/*
	 * Onglet Permis de la fiche commune : chiffres par statut, dossiers à l'enquête et en attente de décision,
	 * histogramme par année et historique (« tout charger »). Le registre a déjà rendu l'en-tête et la barre
	 * d'onglets ; il remonte l'onglet quand on change de commune. Tout est lu en direct sur le service du canton.
	 */
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import DossierCarte from '#lib/components/DossierCarte.svelte';
	import EchecSource from '#lib/components/EchecSource.svelte';
	import { STATUTS, STATUTS_ORDRE } from '#lib/labels.js';
	import type { Contexte } from '#lib/registre/types.js';
	import type { Commune, Dossier } from '#lib/types.js';
	import { permis, SOURCE, type ChiffresCommune, type Parametres } from './donnees.svelte.js';

	let { ctx }: { ctx: Contexte<Parametres> } = $props();

	/** Dossiers d'historique chargés d'emblée ; les autres, sur demande. */
	const RECENTS = 60;

	// Le registre ne monte l'onglet que pour une commune ouverte, et le remonte pour une autre.
	const commune = untrack(() => ctx.commune) as Commune;

	let actifs = $state<Dossier[] | null>(null);
	let chiffres = $state<ChiffresCommune | null>(null);
	let recents = $state<Dossier[] | null>(null);
	/** Les fiches de l'historique récent n'ont pas pu être chargées (la source, elle, a répondu). */
	let echecRecents = $state(false);

	const enquetes = $derived(actifs?.filter((d) => d.statut === 'enquete') ?? []);
	const attente = $derived(actifs?.filter((d) => d.statut === 'procedure') ?? []);

	/** Un échec des dossiers en cours ou des chiffres est porté par l'état de la source (message et « Réessayer »). */
	function charger() {
		echecRecents = false;
		permis.chargerActifs().then(
			(ds) => (actifs = ds.filter((d) => d.slug === commune.slug)),
			() => {}
		);
		permis.chiffres(commune).then(
			(r) => {
				chiffres = r;
				permis.fiches(r.historique.slice(0, RECENTS).map((d) => d.id)).then(
					(ds) => (recents = ds),
					() => (echecRecents = true)
				);
			},
			() => {}
		);
	}
	// Au montage, et de nouveau quand l'erreur de la source est levée (« Réessayer », ici ou dans le volet).
	$effect(() => {
		if (!permis.source.erreur) untrack(charger);
	});

	let tout = $state<Dossier[] | null>(null);
	let chargement = $state(false);
	let echecTout = $state(false);

	async function chargerTout() {
		chargement = true;
		echecTout = false;
		try {
			tout = await permis.fiches(chiffres?.historique.map((d) => d.id) ?? []);
		} catch {
			echecTout = true;
		} finally {
			chargement = false;
		}
	}

	const annees = $derived(Object.entries(chiffres?.parAnnee ?? {}).sort().slice(-12));
	const maxAnnee = $derived(Math.max(1, ...annees.map(([, n]) => n)));
	const resumeAnnees = $derived(annees.map(([a, n]) => `${a} : ${n}`).join(', '));
	const totalHisto = $derived(chiffres?.historique.length ?? 0);

	/** Un dossier choisi s'ouvre par le registre, ici même sous le fil ; la carte vole vers lui. */
	function ouvrir(d: Dossier) {
		ctx.ouvrir({ couche: 'permis', element: String(d.id), position: [d.lon, d.lat] });
	}
</script>

<EchecSource message="Les permis n’ont pas pu être chargés" etat={permis.source} />

<div class="chiffres" aria-busy={!chiffres || !actifs}>
	{#each STATUTS_ORDRE as s (s)}
		<div style:--c={STATUTS[s].couleur}>
			<strong>
				<!-- En cours : comptés sur les listes ci-dessous (dossiers rattachés à la commune, procédures récentes). -->
				{#if s === 'enquete'}{actifs ? enquetes.length : '…'}
				{:else if s === 'procedure'}{actifs ? attente.length : '…'}
				{:else}{chiffres ? chiffres.statuts[s] : '…'}{/if}
			</strong>
			<span>{STATUTS[s].court}</span>
		</div>
	{/each}
</div>

<h3>À l’enquête en ce moment{actifs ? ` (${enquetes.length})` : ''}</h3>
{#if !actifs}
	<ul class="grille" aria-busy="true"><li class="attente"></li><li class="attente"></li></ul>
{:else if enquetes.length}
	<ul class="grille">
		{#each enquetes as d (d.id)}<li><DossierCarte {d} onclick={() => ouvrir(d)} /></li>{/each}
	</ul>
{:else}
	<p class="muted">Aucune demande de permis à l’enquête publique actuellement.</p>
{/if}

{#if attente.length}
	<h3>Enquête terminée, décision attendue ({attente.length})</h3>
	<ul class="grille">
		{#each attente as d (d.id)}<li><DossierCarte {d} onclick={() => ouvrir(d)} /></li>{/each}
	</ul>
{/if}

<h3>Demandes par année</h3>
{#if chiffres}
	<div class="barres" role="img" aria-label="Demandes de permis par année – {resumeAnnees}">
		{#each annees as [annee, n] (annee)}
			<div class="barre" title="{n} demandes en {annee}">
				<span style:height="{(n / maxAnnee) * 100}%"></span>
				<small>{annee.slice(2)}</small>
			</div>
		{/each}
	</div>
{:else}
	<div class="barres attente" aria-busy="true"></div>
{/if}

<h3>Historique</h3>
{#if tout}
	<p class="muted">{tout.length} dossier{tout.length > 1 ? 's' : ''} depuis 1999, hors dossiers en cours listés plus haut.</p>
	<ul class="grille">
		{#each tout as d (d.id)}<li><DossierCarte {d} onclick={() => ouvrir(d)} /></li>{/each}
	</ul>
{:else if echecRecents}
	<p class="erreur" role="alert">
		L’historique n’a pas pu être chargé.
		<button class="bouton secondaire petit" type="button" onclick={charger}>Réessayer</button>
	</p>
{:else if !recents || !actifs}
	<ul class="grille" aria-busy="true"><li class="attente"></li><li class="attente"></li><li class="attente"></li></ul>
{:else}
	<ul class="grille">
		{#each recents as d (d.id)}<li><DossierCarte {d} onclick={() => ouvrir(d)} /></li>{/each}
	</ul>
	{#if totalHisto > recents.length}
		<p>
			<button class="bouton secondaire" type="button" onclick={chargerTout} disabled={chargement}>
				{chargement ? 'Chargement…' : `Tout charger (${totalHisto} dossiers depuis 1999)`}
			</button>
		</p>
		{#if echecTout}
			<p class="erreur" role="alert">L’historique n’a pas pu être chargé. Réessayez dans un instant.</p>
		{/if}
	{/if}
{/if}

<p class="source">
	{SOURCE} depuis votre navigateur ; ce site ne les stocke pas. Sans foi publique : seule la FAO fait foi.
	Rattachement aux communes actuelles (limites swisstopo).
	<a href={resolve('/enquete-publique')}>L’enquête publique : ce que prévoit la loi</a>
</p>

<style>
	h3 {
		font-size: 16px;
		margin: 22px 0 8px;
	}
	.chiffres {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
		gap: 6px;
	}
	.chiffres div {
		background: var(--surface);
		border: 1px solid var(--line);
		border-top: 3px solid var(--c);
		border-radius: 8px;
		padding: 6px 10px;
		display: grid;
	}
	.chiffres strong {
		font-size: 19px;
	}
	.chiffres span {
		font-size: 12.5px;
		color: var(--muted);
	}
	.grille {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 8px;
	}
	.barres {
		display: flex;
		align-items: flex-end;
		gap: 5px;
		height: 110px;
	}
	.barre {
		flex: 1;
		height: 100%;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		align-items: center;
		gap: 4px;
	}
	.barre span {
		width: 100%;
		background: var(--accent);
		border-radius: 3px 3px 0 0;
		min-height: 2px;
	}
	.barre small {
		font-size: 11px;
		color: var(--muted);
	}
	.muted {
		color: var(--muted);
	}
	.erreur {
		margin: 0 0 10px;
		color: var(--erreur);
	}
	.source {
		margin-top: 28px;
	}
	.attente {
		min-height: 92px;
		border-radius: 10px;
		background: var(--line);
		opacity: 0.6;
	}
	.barres.attente {
		min-height: 0;
	}
</style>
