<script lang="ts">
	import Diagramme from './Diagramme.svelte';

	// Le retrait d'un nom en trois étapes (#165), tel que le décrit le texte de l'encadré : une frise de sept jours,
	// du courriel au retrait.
	const etapes = [
		{ titre: 'Vous écrivez', detail: 'un courriel, jamais une issue' },
		{ titre: 'Une correction est enregistrée', detail: 'le texte de l’élément, sans le nom' },
		{ titre: 'Le nom est retiré', detail: 'historique du dépôt compris' }
	];
	const jours = Array.from({ length: 8 }, (_, j) => j);
</script>

<Diagramme>
	<div class="frise">
		<div class="corps">
			<div class="regle">
				<span class="remplissage"></span>
				<span class="graduations">
					{#each jours as j (j)}<span class="jour"></span>{/each}
				</span>
			</div>
			<ol class="etapes">
				{#each etapes as e, i (e.titre)}
					<li style:--i={i} class:fin={i === etapes.length - 1}>
						<span class="pastille">
							<svg aria-hidden="true" viewBox="0 0 24 24" width="22" height="22">
								{#if i === 0}
									<rect x="3" y="5" width="18" height="14" rx="2" pathLength="1" />
									<path d="m3.5 6 8.5 7 8.5-7" pathLength="1" />
								{:else if i === 1}
									<path d="M6 3h9l4 4v14H6z" pathLength="1" />
									<path d="M15 3v4h4M9 14l2 2 4-4.5" pathLength="1" />
								{:else}
									<path d="M4 12.5 9.5 18 20 6.5" pathLength="1" />
								{/if}
							</svg>
						</span>
						<span class="texte">
							<strong>{e.titre}</strong>
							<small>{e.detail}</small>
						</span>
					</li>
				{/each}
			</ol>
		</div>
		<p class="delai"><span class="duree">7 jours</span> au plus, du courriel au retrait</p>
	</div>
</Diagramme>

<style>
	.frise {
		container-type: inline-size;
		/* Le temps que met le remplissage à parcourir la frise ; chaque étape s'allume quand il l'atteint. */
		--course: 2.4s;
		--pastille: 2.75rem;
	}
	.corps {
		position: relative;
	}
	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.etapes {
		position: relative;
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--space-sm);
	}
	li {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-xs);
		text-align: center;
	}
	.pastille {
		flex: none;
		display: grid;
		place-items: center;
		width: var(--pastille);
		height: var(--pastille);
		border-radius: 50%;
		background: var(--color-rule-2);
		color: var(--color-accent-ink);
	}
	.fin .pastille {
		background: var(--color-accent);
	}
	.texte {
		display: flex;
		flex-direction: column;
		line-height: 1.3;
	}
	.texte strong {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}
	.texte small {
		font-size: var(--text-xs);
		color: var(--color-muted);
	}

	/* La règle des sept jours, un trait par jour, passe sous les pastilles, du centre de la première à celui de la dernière. */
	.regle {
		position: absolute;
		left: calc(100% / 6);
		right: calc(100% / 6);
		top: calc(var(--pastille) / 2 - 1px);
		height: 2px;
		background: var(--color-rule);
	}
	.remplissage {
		position: absolute;
		inset: 0;
		background: var(--color-accent);
		transform-origin: left;
	}
	.graduations {
		position: absolute;
		inset: 0;
		display: flex;
		justify-content: space-between;
	}
	.jour {
		position: relative;
		width: 1px;
		height: var(--space-xs);
		margin-top: var(--space-xs);
		background: var(--color-rule-2);
	}

	.delai {
		margin: var(--space-lg) 0 0;
		padding-top: var(--space-sm);
		border-top: var(--rule-hair) solid var(--color-rule);
		text-align: center;
		font-size: var(--text-sm);
		color: var(--color-muted);
	}
	.duree {
		font-family: var(--font-outlier);
		font-weight: 500;
		font-size: var(--text-lg);
		font-variant-numeric: tabular-nums;
		color: var(--color-accent);
	}

	/* Étroit : la frise se dresse, la règle descend le long des pastilles. */
	@container (max-width: 32rem) {
		.etapes {
			grid-template-columns: minmax(0, 1fr);
			gap: var(--space-lg);
		}
		li {
			flex-direction: row;
			text-align: left;
			gap: var(--space-sm);
		}
		.regle {
			left: calc(var(--pastille) / 2 - 1px);
			right: auto;
			top: calc(var(--pastille) / 2);
			bottom: calc(var(--pastille) / 2);
			width: 2px;
			height: auto;
		}
		.remplissage {
			transform-origin: top;
		}
		.graduations {
			display: none;
		}
		.delai {
			text-align: left;
		}
	}

	@media screen and (prefers-reduced-motion: no-preference) {
		:global([data-js-etat='attente']) .remplissage {
			transform: scale(0);
		}
		:global([data-js-etat='attente']) .pastille {
			transform: scale(0.6);
			opacity: 0;
		}
		:global([data-js-etat='attente']) .texte,
		:global([data-js-etat='attente']) .delai {
			opacity: 0;
		}
		:global([data-js-etat='attente']) .pastille * {
			stroke-dasharray: 1;
			stroke-dashoffset: 1;
		}

		:global([data-js-etat='joue']) .remplissage {
			animation: remplit var(--course) var(--ease-in-out) 0.3s both;
		}
		@container (max-width: 32rem) {
			:global([data-js-etat='joue']) .remplissage {
				animation-name: remplit-haut;
			}
		}
		:global([data-js-etat='joue']) .pastille {
			animation: allume 0.5s var(--ease-out) calc(0.15s + var(--i) * var(--course) / 2) both;
		}
		:global([data-js-etat='joue']) .pastille * {
			stroke-dasharray: 1;
			animation: trace 0.55s var(--ease-out) calc(0.4s + var(--i) * var(--course) / 2) both;
		}
		:global([data-js-etat='joue']) .texte {
			animation: monte 0.5s var(--ease-out) calc(0.3s + var(--i) * var(--course) / 2) both;
		}
		:global([data-js-etat='joue']) .delai {
			animation: monte 0.5s var(--ease-out) calc(0.6s + var(--course)) both;
		}
	}
	@keyframes remplit {
		from {
			transform: scale(0, 1);
		}
		to {
			transform: none;
		}
	}
	@keyframes remplit-haut {
		from {
			transform: scale(1, 0);
		}
		to {
			transform: none;
		}
	}
	@keyframes allume {
		from {
			opacity: 0;
			transform: scale(0.6);
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
