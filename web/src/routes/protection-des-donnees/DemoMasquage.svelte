<script lang="ts">
	import { MASQUE } from '#lib/masquage.js';
	import Diagramme from '#lib/almanach/Diagramme.svelte';
	import { CONSEIL, PERMIS, type Morceau } from './exemples.js';

	// Le masquage en direct (#165) : la phrase de la source, puis celle du site. Pour chaque exemple, où le masquage
	// a lieu : dans le navigateur pour les permis, au cron pour les conseils (ADR-0007).
	const exemples: { morceaux: Morceau[]; couche: string; lieu: string }[] = [
		{ morceaux: PERMIS, couche: 'Permis', lieu: 'masqué dans votre navigateur, avant affichage' },
		{ morceaux: CONSEIL, couche: 'Conseils', lieu: 'masqué par le cron, avant le dépôt de données public' }
	];

	/** Où tombe le milieu de chaque morceau dans la phrase, de 0 à 1 : le balayage l'atteint à ce moment-là. */
	const positions = (morceaux: Morceau[]): number[] => {
		const total = morceaux.reduce((n, m) => n + m.texte.length, 0);
		let debut = 0;
		return morceaux.map((m) => {
			const milieu = debut + m.texte.length / 2;
			debut += m.texte.length;
			return milieu / total;
		});
	};
</script>

<Diagramme legende="Noms inventés">
	<div class="exemples">
		{#each exemples as e, n (e.couche)}
			{@const t = positions(e.morceaux)}
			<div class="exemple" style:--n={n}>
				<p class="tete">
					<span class="couche">{e.couche}</span>
					<span class="lieu">
						<svg aria-hidden="true" viewBox="0 0 16 16" width="16" height="16">
							{#if e.couche === 'Permis'}
								<rect x="2" y="3" width="12" height="9" rx="1.5" />
								<path d="M5.5 14.5h5M8 12v2.5" />
							{:else}
								<circle cx="8" cy="8" r="6" />
								<path d="M8 4.5V8l2.5 1.5" />
							{/if}
						</svg>
						{e.lieu}
					</span>
				</p>
				<p class="phrase">
					<span class="balayage"></span>
					{#each e.morceaux as m, i (i)}
						{#if m.role === 'masque'}
							<span class="nom" style:--t={t[i]}
								><span class="avant">{m.texte}</span><span class="apres">{MASQUE}</span></span
							>
						{:else if m.role === 'elu'}
							<span class="elu" style:--t={t[i]}>
								{m.texte}
								<span class="badge">
									<svg aria-hidden="true" viewBox="0 0 12 12" width="11" height="11"><path d="M2.5 6.5 5 9l4.5-6" pathLength="1" /></svg>
									élue connue
								</span>
							</span>
						{:else}{m.texte}{/if}
					{/each}
				</p>
			</div>
		{/each}
	</div>
</Diagramme>

<style>
	.exemples {
		display: grid;
	}
	.exemple {
		/* Le second exemple attend que le premier ait fini. */
		--depart: calc(0.25s + var(--n) * 2.6s);
		--balayage: 1.3s;
		padding-block: var(--space-md);
	}
	.exemple + .exemple {
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.exemple:first-child {
		padding-top: 0;
	}
	.exemple:last-child {
		padding-bottom: 0;
	}
	.tete {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--space-2xs) var(--space-sm);
		margin: 0 0 var(--space-xs);
		font-size: var(--text-sm);
	}
	.couche {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}
	.lieu {
		display: inline-flex;
		align-items: flex-start;
		gap: var(--space-2xs);
		color: var(--color-muted);
	}
	.lieu svg {
		flex: none;
		align-self: center;
	}
	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 1.6;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.phrase {
		position: relative;
		isolation: isolate;
		margin: 0;
		font-size: var(--text-lead);
		line-height: 1.75;
		color: var(--color-ink);
	}

	/* Le balayage : un lavis orange mené par un trait, qui passe sur la phrase de gauche à droite. Hors animation,
	   il n'existe pas. */
	.balayage {
		display: none;
	}

	/* Le nom et « [particulier] » occupent la même case : l'un s'efface pendant que l'autre arrive, sans que la
	   phrase ne bouge ; le masque, un peu plus court, se centre sur la place du nom. Au repos, seul le masque est là. */
	.nom {
		display: inline-grid;
		justify-items: center;
		vertical-align: bottom;
	}
	.nom > span {
		grid-area: 1 / 1;
		white-space: nowrap;
	}
	.avant {
		display: none;
		position: relative;
	}
	.apres {
		padding: 0 var(--space-xs);
		background: var(--color-accent-wash);
		color: var(--color-accent);
		font-weight: 600;
	}
	.elu {
		font-weight: 600;
	}
	.badge {
		display: inline-flex;
		align-items: center;
		gap: var(--space-3xs);
		margin-left: var(--space-2xs);
		padding: 0 var(--space-xs);
		border: var(--rule-hair) solid var(--color-rule-2);
		border-radius: var(--radius-pill);
		font-family: var(--font-display);
		font-size: var(--text-xs);
		font-weight: 500;
		line-height: 1.6;
		color: var(--color-ink);
		vertical-align: 0.2em;
	}
	.badge svg {
		stroke-width: 2;
	}

	@media screen and (prefers-reduced-motion: no-preference) {
		.balayage {
			position: absolute;
			inset: 0;
			z-index: -1;
			overflow: clip;
		}
		.balayage::before {
			content: '';
			position: absolute;
			inset: 0;
			border-right: var(--rule-bar) solid var(--color-accent);
			background: linear-gradient(to right, transparent, var(--color-accent-wash));
			transform: translateX(-100%);
			opacity: 0;
		}
		:global([data-js-etat]) .balayage {
			display: block;
		}
		:global([data-js-etat]) .avant {
			display: inline-block;
		}
		/* Le trait qui raye le nom avant qu'il ne parte. */
		.avant::after {
			content: '';
			position: absolute;
			left: 0;
			right: 0;
			top: 55%;
			border-top: var(--rule-bar) solid var(--color-accent);
			transform: scaleX(0);
			transform-origin: left;
		}
		:global([data-js-etat='attente']) .apres,
		:global([data-js-etat='attente']) .badge {
			opacity: 0;
		}

		:global([data-js-etat='joue']) .balayage::before {
			animation: balaie var(--balayage) var(--ease-in-out) var(--depart) both;
		}
		:global([data-js-etat='joue']) .avant {
			--quand: calc(var(--depart) + var(--t) * var(--balayage));
			animation:
				repere 0.3s var(--ease-out) var(--quand) forwards,
				part 0.5s var(--ease-in) calc(var(--quand) + 0.55s) forwards;
		}
		:global([data-js-etat='joue']) .avant::after {
			animation: raye 0.35s var(--ease-out) calc(var(--depart) + var(--t) * var(--balayage) + 0.15s) both;
		}
		:global([data-js-etat='joue']) .apres {
			animation: arrive 0.6s var(--ease-out) calc(var(--depart) + var(--t) * var(--balayage) + 0.85s) both;
		}
		:global([data-js-etat='joue']) .badge {
			animation: arrive 0.55s var(--ease-out) calc(var(--depart) + var(--t) * var(--balayage) + 0.1s) both;
		}
		:global([data-js-etat='joue']) .badge path {
			stroke-dasharray: 1;
			animation: trace 0.4s var(--ease-out) calc(var(--depart) + var(--t) * var(--balayage) + 0.35s) both;
		}
	}
	@keyframes balaie {
		0% {
			transform: translateX(-100%);
			opacity: 1;
		}
		80% {
			transform: none;
			opacity: 1;
		}
		100% {
			transform: none;
			opacity: 0;
		}
	}
	@keyframes repere {
		to {
			color: var(--color-accent);
		}
	}
	@keyframes raye {
		to {
			transform: none;
		}
	}
	@keyframes part {
		from {
			color: var(--color-accent);
		}
		to {
			opacity: 0;
			transform: translateY(-0.5em);
			filter: blur(3px);
		}
	}
	@keyframes arrive {
		from {
			opacity: 0;
			transform: translateY(0.45em) scale(0.92);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes trace {
		from {
			stroke-dashoffset: 1;
		}
		to {
			stroke-dashoffset: 0;
		}
	}
</style>
