<script lang="ts">
	import type { Snippet } from 'svelte';
	import { anime } from './anime.js';

	// Un diagramme d'une page Almanach (#165). Il dit en image ce que le texte dit déjà : il est caché aux lecteurs
	// d'écran, et la page se lit sans lui. Il joue une seule fois, à son entrée à l'écran (`anime`).
	let { children, legende }: { children: Snippet; legende?: string } = $props();
</script>

<div class="diagramme" use:anime>
	<div aria-hidden="true">{@render children()}</div>
	{#if legende}<p class="legende" aria-hidden="true">{legende}</p>{/if}
</div>

<style>
	/* La planche : une feuille pâle posée sur le papier, un filet d'encre en tête, aucun cadre. */
	.diagramme {
		margin: var(--space-xl) 0;
		padding: var(--space-lg);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
	}
	.legende {
		margin: var(--space-md) 0 0;
		padding-top: var(--space-xs);
		border-top: var(--rule-hair) solid var(--color-rule);
		font-size: var(--text-xs);
		color: var(--color-muted);
	}
	@media (max-width: 40rem) {
		.diagramme {
			margin-inline: calc(-1 * var(--space-xs));
			padding: var(--space-md) var(--space-sm);
		}
	}
	@media print {
		.diagramme {
			break-inside: avoid;
			background: none;
		}
	}
</style>
