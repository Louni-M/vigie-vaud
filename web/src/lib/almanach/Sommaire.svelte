<script lang="ts" module>
	export interface Partie {
		id: string;
		titre: string;
		sous?: { id: string; titre: string }[];
	}
</script>

<script lang="ts">
	// Le sommaire d'une page Almanach (#165) : ses parties, numérotées, et leurs intertitres. Sur grand écran, il devient
	// un rail qui reste à côté du texte, avec un filet qui se remplit à mesure de la lecture.

	let { parties }: { parties: Partie[] } = $props();

	// Le sommaire suit la lecture : l'intertitre passé en dernier au tiers haut de l'écran est marqué, et annoncé comme
	// l'endroit où l'on est (aria-current) ; tout en bas de la page, le dernier, que la fin du texte ne laisse pas monter
	// jusque-là. Sans JavaScript, le sommaire reste une simple liste de liens.
	const ancres = $derived(parties.flatMap((p) => [p.id, ...(p.sous ?? []).map((s) => s.id)]));
	let actif = $state<string | null>(null);
	const partieActive = $derived(
		parties.find((p) => p.id === actif || p.sous?.some((s) => s.id === actif))?.id ?? null
	);

	function suitLaLecture(_: HTMLElement) {
		let image = 0;
		const lit = () => {
			image = 0;
			const seuil = innerHeight * 0.3;
			let dernier: string | null = null;
			for (const id of ancres) {
				const titre = document.getElementById(id);
				if (titre && titre.getBoundingClientRect().top <= seuil) dernier = id;
			}
			const enBas = scrollY + innerHeight >= document.documentElement.scrollHeight - 2;
			actif = enBas && dernier ? ancres[ancres.length - 1] : dernier;
		};
		const auDefilement = () => {
			if (!image) image = requestAnimationFrame(lit);
		};
		addEventListener('scroll', auDefilement, { passive: true });
		lit();
		return {
			destroy() {
				removeEventListener('scroll', auDefilement);
				cancelAnimationFrame(image);
			}
		};
	}
</script>

<nav class="sommaire" aria-label="Sommaire" use:suitLaLecture>
	{#each parties as partie, i (partie.id)}
		<div class="partie-sommaire" class:active={partieActive === partie.id}>
			<a
				class="partie-lien"
				class:actif={actif === partie.id}
				aria-current={actif === partie.id ? 'location' : undefined}
				href="#{partie.id}"><span class="numero">{i + 1}</span>{partie.titre}</a
			>
			{#if partie.sous?.length}
				<ul>
					{#each partie.sous as s (s.id)}
						<li>
							<a href="#{s.id}" class:actif={actif === s.id} aria-current={actif === s.id ? 'location' : undefined}
								>{s.titre}</a
							>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/each}
</nav>

<style>
	.sommaire {
		margin-top: var(--space-xl);
		padding-top: var(--space-md);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		font-family: var(--font-display);
		font-size: var(--text-sm);
		line-height: 1.35;
	}
	.partie-sommaire + .partie-sommaire {
		margin-top: var(--space-lg);
	}
	.partie-lien {
		display: flex;
		gap: var(--space-xs);
		font-weight: 600;
		color: var(--color-ink);
		text-decoration: none;
	}
	.sommaire ul {
		list-style: none;
		margin: var(--space-xs) 0 0;
		padding: 0 0 0 var(--space-md);
	}
	.sommaire li a {
		position: relative;
		display: block;
		padding: var(--space-2xs) 0 var(--space-2xs) var(--space-sm);
		color: var(--color-muted);
		text-decoration: none;
		transition:
			color var(--dur-short) var(--ease-out),
			transform var(--dur-short) var(--ease-out);
	}
	/* La marque de l'intertitre courant : un trait orange qui se dresse. */
	.sommaire li a::before {
		content: '';
		position: absolute;
		left: 0;
		top: var(--space-2xs);
		bottom: var(--space-2xs);
		border-left: var(--rule-bar) solid var(--color-accent);
		transform: scaleY(0);
		transition: transform var(--dur-short) var(--ease-out);
	}
	.sommaire li a:hover {
		color: var(--color-ink);
	}
	/* Au survol, l'intertitre avance d'un cran : un mouvement, que l'on garde pour qui ne l'a pas refusé. */
	@media (prefers-reduced-motion: no-preference) {
		.sommaire li a:hover {
			transform: translateX(var(--space-3xs));
		}
	}
	.sommaire li a.actif {
		color: var(--color-ink);
	}
	.sommaire li a.actif::before {
		transform: none;
	}
	.sommaire a:active {
		color: var(--color-accent);
	}

	/*
	 * Grand écran : le rail, à gauche, de la fin de l'en-tête au bas de la page. Plus haut que l'écran (fenêtre basse,
	 * texte agrandi), il défile pour lui-même, sans entraîner la page une fois au bout. Ses marges intérieures, haut,
	 * bas et à droite, laissent la place à l'anneau de focus et au pas de côté du survol, que le défilement rognerait ;
	 * la marge du haut est reprise sur la marge extérieure, et le filet ne la longe pas.
	 */
	@media (min-width: 60rem) {
		.sommaire {
			grid-column: 1;
			grid-row: 2 / span 2;
			align-self: start;
			position: sticky;
			top: calc(var(--header-h) + var(--space-lg));
			max-height: calc(100dvh - var(--header-h) - var(--space-lg));
			overflow-y: auto;
			overscroll-behavior: contain;
			margin-top: calc(var(--space-xl) - var(--space-2xs));
			padding: var(--space-2xs) var(--space-xs) var(--space-2xs) var(--space-md);
			border-top: 0;
		}
		/* Le filet de lecture, le long du rail. */
		.sommaire::before,
		.sommaire::after {
			content: '';
			position: absolute;
			left: 0;
			top: var(--space-2xs);
			bottom: var(--space-2xs);
			border-left: var(--rule-bar) solid var(--color-rule);
		}
		.sommaire::after {
			border-left-color: var(--color-accent);
			transform-origin: top;
			transform: scaleY(0);
		}
	}
	/*
	 * Une partie sans intertitres se marque elle-même : son titre se souligne d'un lavis orange, un calque sous le texte
	 * qui s'étire de la gauche (transform, sans repeindre le fond à chaque image). Le lien isole son empilement pour que
	 * le calque passe sous le texte sans passer sous le fond de la page.
	 */
	.partie-sommaire:not(:has(ul)) .partie-lien {
		position: relative;
		isolation: isolate;
		width: fit-content;
	}
	.partie-sommaire:not(:has(ul)) .partie-lien::after {
		content: '';
		position: absolute;
		z-index: -1;
		left: 0;
		right: 0;
		bottom: 0;
		height: 0.45em;
		background: var(--color-accent-wash);
		transform: scaleX(0);
		transform-origin: left;
		transition: transform var(--dur-short) var(--ease-out);
	}
	.partie-sommaire:not(:has(ul)) .partie-lien.actif::after {
		transform: none;
	}
	/* Sans mouvement, les marques changent d'un coup. */
	@media (prefers-reduced-motion: reduce) {
		.sommaire li a,
		.sommaire li a::before,
		.partie-sommaire .partie-lien::after {
			transition: none;
		}
	}
	@supports (animation-timeline: scroll()) {
		@media screen and (prefers-reduced-motion: no-preference) and (min-width: 60rem) {
			.sommaire::after {
				animation: remplit linear both;
				animation-timeline: scroll(root);
			}
		}
	}
	@keyframes remplit {
		from {
			transform: scaleY(0);
		}
		to {
			transform: none;
		}
	}
	@media print {
		.sommaire {
			display: none;
		}
	}
</style>
