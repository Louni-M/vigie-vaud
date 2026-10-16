<script lang="ts">
	// PROTOTYPE (ticket #51) : une ligne d'objet ou de séance dans un onglet, un volet ou une fiche.
	import { dateDe, jourCourt, jourSemaine, nomConseil, type ElementConseil } from './donnees.svelte.js';

	let {
		x,
		onclick,
		conseil = false,
		communes,
		actif = false
	}: {
		x: ElementConseil;
		onclick: () => void;
		/** Afficher le conseil (« Grand Conseil »). */
		conseil?: boolean;
		/** Pour un objet du Grand Conseil : nom des communes citées. */
		communes?: (slug: string) => string;
		actif?: boolean;
	} = $props();
</script>

<li class:actif>
	<button type="button" {onclick}>
		<span class="meta">
			{#if x.sorte === 'seance'}
				<span class="pastille seance">◷</span>{x.age < 0 ? 'À venir · ' : ''}{jourSemaine.format(dateDe(x))}
			{:else}
				<span class="pastille">§</span>{x.type}{x.numero ? ` ${x.numero}` : ''} · {jourCourt.format(dateDe(x))}
			{/if}
			{#if conseil}· {nomConseil(x)}{/if}
		</span>
		<span class="titre">{x.titre}</span>
		{#if x.sorte === 'objet' && (x.statut || x.auteurs.length)}
			<span class="sous">
				{x.auteurs.slice(0, 2).map((a) => a.nom + (a.parti ? ` (${a.parti})` : '')).join(', ')}{x.auteurs.length > 2 ? ' et al.' : ''}
				{#if x.statut}{x.auteurs.length ? ' · ' : ''}<em>{x.statut}</em>{/if}
			</span>
		{/if}
		{#if communes && x.conseil === null && x.communes.length}
			<span class="sous">→ {x.communes.map(communes).join(', ')}</span>
		{/if}
	</button>
</li>

<style>
	li { list-style: none; border-bottom: 1px solid var(--line); }
	li.actif { background: #fff6d6; }
	button { display: grid; gap: 2px; width: 100%; padding: 7px 4px; border: 0; background: none; font: inherit; text-align: left; cursor: pointer; }
	button:hover { background: var(--bg); }
	.meta { font-size: 12px; color: #7a3e9d; font-weight: 600; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
	.pastille { display: inline-grid; place-items: center; width: 16px; height: 16px; border-radius: 4px; background: #7a3e9d; color: #fff; font-size: 10px; }
	.pastille.seance { background: #2f6f8f; }
	.titre { font-size: 14px; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
	.sous { font-size: 12px; color: var(--muted); }
</style>
