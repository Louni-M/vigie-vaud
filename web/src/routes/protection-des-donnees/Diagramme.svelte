<script lang="ts">
	import type { Snippet } from 'svelte';

	// Un diagramme de la page (#165). Il dit en image ce que le texte dit déjà : il est caché aux lecteurs d'écran,
	// et la page se lit sans lui. Rendu à la construction dans son état final, qui sert aussi sans JavaScript, à
	// l'impression et quand le mouvement est réduit. Sinon, il revient à son état de départ (`attente`) et joue une
	// seule fois (`joue`) quand il entre à l'écran. L'état est porté par `data-js-etat`, que seul le script pose : sans
	// lui, rien n'est caché. Les états ne s'appliquent qu'à l'écran : chaque diagramme écrit ses règles d'animation
	// sous `@media screen and (prefers-reduced-motion: no-preference)`.
	let { children, legende }: { children: Snippet; legende?: string } = $props();

	function anime(n: HTMLDivElement) {
		if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		n.dataset.jsEtat = 'attente';
		const observateur = new IntersectionObserver(
			(entrees) => {
				if (!entrees.some((e) => e.isIntersecting)) return;
				n.dataset.jsEtat = 'joue';
				observateur.disconnect();
			},
			// Le diagramme joue quand il est bien entré, pas dès que son bord affleure en bas de l'écran.
			{ threshold: 0.4, rootMargin: '0px 0px -12% 0px' }
		);
		observateur.observe(n);
		return { destroy: () => observateur.disconnect() };
	}
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
