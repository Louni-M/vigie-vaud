<script lang="ts">
	import Diagramme from '#lib/almanach/Diagramme.svelte';

	// Une journée de vérification (#165), telle que la décrit l'introduction de la page : les sources sondées
	// plusieurs fois par jour, les conseils importés une fois par jour, et le site d'une commune sondé une seule fois,
	// juste avant son import. Un schéma, pas un horaire : le calendrier du cron est tenu dans le dépôt de données.

	type Marque = { t: number; sorte: 'sonde' | 'import' };

	/** Les sondes de la journée, à intervalles réguliers ; `t` va de 0 (début du jour) à 1 (fin). */
	const sondes: Marque[] = [1, 3, 5, 7, 9, 11].map((h) => ({ t: h / 12, sorte: 'sonde' }));

	const lignes: { titre: string; rythme: string; marques: Marque[] }[] = [
		{ titre: 'Une source', rythme: 'sondée plusieurs fois par jour', marques: sondes },
		{
			titre: 'Un conseil',
			rythme: 'importé une fois par jour, sondé plusieurs fois',
			marques: [...sondes, { t: 0.33, sorte: 'import' as const }].sort((a, b) => a.t - b.t)
		},
		{
			titre: 'Le site d’une commune',
			rythme: 'sondé une seule fois, juste avant son import',
			marques: [
				{ t: 0.5, sorte: 'sonde' },
				{ t: 0.545, sorte: 'import' }
			]
		}
	];
</script>

<Diagramme legende="Schéma d’une journée, sans ses heures">
	<div class="journee">
		<ol class="lignes">
			{#each lignes as l, n (l.titre)}
				<li style:--n={n}>
					<span class="titre">
						<strong>{l.titre}</strong>
						<small>{l.rythme}</small>
					</span>
					<span class="piste">
						<span class="trait"></span>
						<span class="parcouru"></span>
						{#each l.marques as m, i (i)}
							<span class="marque {m.sorte}" style:--t={m.t}></span>
						{/each}
					</span>
				</li>
			{/each}
		</ol>
		<p class="cles">
			<span><span class="marque sonde"></span>une sonde vérifie que la source répond</span>
			<span><span class="marque import"></span>un import relève ses données</span>
		</p>
	</div>
</Diagramme>

<style>
	.journee {
		container-type: inline-size;
		/* Le temps que met la journée à défiler ; chaque marque s'allume quand le trait l'atteint. */
		--course: 2.6s;
	}
	.lignes {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		display: grid;
		grid-template-columns: 13rem minmax(0, 1fr);
		align-items: center;
		gap: var(--space-lg);
		padding-block: var(--space-sm);
	}
	li + li {
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.titre {
		display: flex;
		flex-direction: column;
		line-height: 1.3;
	}
	.titre strong {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: var(--text-sm);
		color: var(--color-ink);
	}
	.titre small {
		font-size: var(--text-xs);
		color: var(--color-muted);
	}

	/* La piste d'une journée : un trait pâle, que le passage du jour recouvre d'encre. */
	.piste {
		position: relative;
		height: 1.5rem;
		/* Les marques débordent d'une demi-largeur de chaque côté : la piste leur laisse cette place. */
		margin-inline: 0.5rem;
	}
	.trait,
	.parcouru {
		position: absolute;
		left: 0;
		right: 0;
		top: calc(50% - 1px);
		height: 2px;
		background: var(--color-rule);
	}
	.parcouru {
		background: var(--color-rule-2);
		transform-origin: left;
	}
	.marque {
		display: inline-block;
		width: 0.75rem;
		height: 0.75rem;
		box-sizing: border-box;
	}
	.piste .marque {
		position: absolute;
		left: calc(var(--t) * 100% - 0.375rem);
		top: calc(50% - 0.375rem);
	}
	/* La sonde, un anneau ; l'import, un carré plein orange, le seul signal du diagramme. */
	.sonde {
		border: var(--rule-bar) solid var(--color-rule-2);
		border-radius: 50%;
		background: var(--color-sheet);
	}
	.import {
		background: var(--color-accent);
	}

	.cles {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2xs) var(--space-lg);
		margin: var(--space-md) 0 0;
		padding-top: var(--space-sm);
		border-top: var(--rule-hair) solid var(--color-rule);
		font-size: var(--text-xs);
		color: var(--color-muted);
	}
	.cles > span {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
	}
	.cles .marque {
		flex: none;
	}

	/* Étroit : le titre passe au-dessus de sa piste. */
	@container (max-width: 34rem) {
		li {
			grid-template-columns: minmax(0, 1fr);
			gap: var(--space-xs);
		}
	}

	@media screen and (prefers-reduced-motion: no-preference) {
		:global([data-js-etat='attente']) .parcouru {
			transform: scaleX(0);
		}
		:global([data-js-etat='attente']) .piste .marque,
		:global([data-js-etat='attente']) .cles {
			opacity: 0;
		}

		/* Les trois journées défilent ensemble, d'une même main ; la suivante démarre à peine plus tard. */
		:global([data-js-etat='joue']) .parcouru {
			animation: parcourt var(--course) linear calc(0.2s + var(--n) * 0.12s) both;
		}
		:global([data-js-etat='joue']) .piste .marque {
			animation: allume 0.45s var(--ease-out) calc(0.2s + var(--n) * 0.12s + var(--t) * var(--course)) both;
		}
		:global([data-js-etat='joue']) .cles {
			animation: monte 0.5s var(--ease-out) calc(0.6s + var(--course)) both;
		}
	}
	@keyframes parcourt {
		from {
			transform: scaleX(0);
		}
		to {
			transform: none;
		}
	}
	@keyframes allume {
		0% {
			opacity: 0;
			transform: scale(0.3);
		}
		60% {
			opacity: 1;
			transform: scale(1.35);
		}
		100% {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes monte {
		from {
			opacity: 0;
			transform: translateY(0.5rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
</style>
