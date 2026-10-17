<script lang="ts">
	/* PROTOTYPE, variante B : la carte d'un groupe (fermeture et sa déviation), sous le nom de la route. */
	import { communesTexte, echeance, periode, rhrcTexte, routes, SORTES, type Groupe } from './donnees.svelte.js';

	let { g, actif = false, onclick }: { g: Groupe; actif?: boolean; onclick?: () => void } = $props();
</script>

<button
	type="button"
	class="carte"
	class:actif
	{onclick}
	onmouseenter={() => (routes.survol = g.cle)}
	onmouseleave={() => (routes.survol = null)}
>
	<span class="route">{rhrcTexte(g.rhrc)}</span>
	<span class="nom">{g.nom}</span>
	<span class="sortes">
		{#each g.restrictions as r (r.id)}
			<span class="sorte" style:--c={SORTES[r.sorte].couleur} class:tirets={r.sorte === 'deviation'}>{SORTES[r.sorte].nom}</span>
		{/each}
	</span>
	<span class="bas">
		<span class:avenir={g.quand === 'a-venir'}>{g.quand === 'a-venir' ? 'À venir' : 'En cours'}</span>
		<span class="muted">· {periode(g)} · {echeance(g)}</span>
	</span>
	<span class="muted petit">{communesTexte(g.communes)}</span>
</button>

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 100%;
		text-align: left;
		padding: 12px;
		border: 1px solid var(--line);
		border-radius: 12px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		font-size: 14px;
		cursor: pointer;
	}
	.carte:hover,
	.actif {
		border-color: var(--accent);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.route {
		font-size: 12px;
		color: var(--muted);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.nom {
		font-size: 15px;
		font-weight: 650;
	}
	.sortes {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}
	.sorte {
		padding: 2px 8px;
		border-radius: 999px;
		background: color-mix(in srgb, var(--c) 14%, transparent);
		border: 1.5px solid var(--c);
		font-size: 12px;
	}
	.sorte.tirets {
		border-style: dashed;
	}
	.bas {
		font-size: 13px;
	}
	.avenir {
		font-weight: 600;
		color: #5f3dc4;
	}
	.muted {
		color: var(--muted);
	}
	.petit {
		font-size: 12.5px;
	}
</style>
