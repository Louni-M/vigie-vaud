<script lang="ts">
	/* PROTOTYPE, variante A : la carte d'une restriction, seule. */
	import { communesTexte, echeance, periode, plageTexte, SORTES, type Restriction } from './donnees.svelte.js';

	let {
		r,
		actif = false,
		onclick,
		commune
	}: { r: Restriction; actif?: boolean; onclick?: () => void; commune?: string } = $props();
	const ici = $derived(commune ? r.communes.find((p) => p.commune.slug === commune) : undefined);
</script>

<button type="button" class="carte" class:actif class:avenir={r.quand === 'a-venir'} {onclick} style:--c={SORTES[r.sorte].couleur}>
	<span class="haut">
		<span class="trait" class:tirets={r.sorte === 'deviation'}></span>
		<strong>{SORTES[r.sorte].nom}</strong>
		{#if r.quand === 'a-venir'}<span class="etiquette">À venir</span>{/if}
		<span class="communes">{communesTexte(r.communes, 2)}</span>
	</span>
	<span class="nom">{r.nom}</span>
	<span class="bas">
		<span>{periode(r)}</span>
		<span class="muted">· {echeance(r)}</span>
		{#if r.plage}<span class="nuit">· chaque nuit {plageTexte(r.plage)}</span>{/if}
	</span>
	{#if ici && r.communes.length > 1}
		<span class="muted petit">{Math.round(ici.metres) >= 1000 ? `${(ici.metres / 1000).toFixed(1)} km` : `${Math.round(ici.metres)} m`} dans la commune, sur {r.communes.length} communes</span>
	{/if}
</button>

<style>
	.carte {
		display: flex;
		flex-direction: column;
		gap: 3px;
		width: 100%;
		text-align: left;
		padding: 10px 12px;
		border: 1px solid var(--line);
		border-left: 4px solid var(--c);
		border-radius: 10px;
		background: var(--surface);
		color: inherit;
		font: inherit;
		font-size: 14px;
		cursor: pointer;
	}
	.carte:hover,
	.actif {
		border-color: var(--accent);
		border-left-color: var(--c);
		box-shadow: 0 0 0 1px var(--accent);
	}
	.avenir {
		border-left-style: dashed;
	}
	.haut {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
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
	.etiquette {
		padding: 1px 6px;
		border-radius: 4px;
		background: var(--bg);
		border: 1px solid var(--line);
		font-size: 11.5px;
	}
	.communes {
		margin-left: auto;
		color: var(--muted);
	}
	.nom {
		font-weight: 600;
	}
	.bas {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		font-size: 13px;
	}
	.nuit {
		color: #5f3dc4;
	}
	.muted {
		color: var(--muted);
	}
	.petit {
		font-size: 12.5px;
	}
</style>
