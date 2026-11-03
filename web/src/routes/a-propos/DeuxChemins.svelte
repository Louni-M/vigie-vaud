<script lang="ts">
	import Diagramme from '#lib/almanach/Diagramme.svelte';

	// Deux chemins pour les données (#165), tels que les décrit la partie Les couches : les permis et les routes sont
	// lus en direct par le navigateur, à chaque visite, sans copie ; les conseils sont importés une fois par jour dans
	// le dépôt de données public, qui les garde. Trois passages de l'import, trois feuilles dans le dépôt.
	const jours = [0, 1, 2];
</script>

<Diagramme>
	<div class="chemins">
		<div class="chemin direct">
			<p class="titre"><strong>Permis, Routes</strong> lus en direct</p>
			<div class="trace">
				<span class="noeud"><strong>L’État de Vaud</strong><small>ogc.vd.ch</small></span>
				<span class="segment long">
					<small class="dessus">à chaque visite</small>
					<span class="ligne"></span>
					<span class="paquet"></span>
					<small class="dessous">aucune copie gardée</small>
				</span>
				<span class="noeud"><strong>Votre navigateur</strong></span>
			</div>
		</div>
		<div class="chemin import">
			<p class="titre"><strong>Conseils</strong> importés une fois par jour</p>
			<div class="trace">
				<span class="noeud"><strong>OpenParlData</strong><small>ou le site de la commune</small></span>
				<span class="segment">
					<small class="dessus">une fois par jour</small>
					<span class="ligne"></span>
					<span class="paquet"></span>
				</span>
				<span class="noeud depot">
					<span class="pile">
						{#each jours as k (k)}<span class="feuille" style:--k={k}></span>{/each}
					</span>
					<strong>Dépôt de données public</strong>
					<small>reste, même si la source l’efface</small>
				</span>
				<span class="segment">
					<small class="dessus">à chaque visite</small>
					<span class="ligne"></span>
					<span class="paquet"></span>
				</span>
				<span class="noeud"><strong>Votre navigateur</strong></span>
			</div>
		</div>
	</div>
</Diagramme>

<style>
	.chemins {
		container: chemins / inline-size;
		/* La durée d'un passage de paquet sur un segment. */
		--passe: 0.9s;
		--point: 0.625rem;
	}
	.chemin {
		padding-block: var(--space-md);
	}
	.chemin:first-child {
		padding-top: 0;
	}
	.chemin:last-child {
		padding-bottom: 0;
	}
	.chemin + .chemin {
		border-top: var(--rule-hair) solid var(--color-rule);
	}
	.titre {
		margin: 0 0 var(--space-sm);
		font-size: var(--text-sm);
		color: var(--color-muted);
	}
	.titre strong {
		margin-right: var(--space-2xs);
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}

	/* Le tracé, sur cinq colonnes : source, segment, dépôt, segment, navigateur. Le chemin direct saute le dépôt. */
	.trace {
		display: grid;
		grid-template-columns:
			minmax(0, 7.5rem) minmax(3rem, 1fr) minmax(0, 7.5rem) minmax(3rem, 1fr)
			minmax(0, 7.5rem);
		align-items: center;
	}
	.long {
		grid-column: 2 / 5;
	}
	.noeud {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-3xs);
		min-height: 4.5rem;
		padding: var(--space-xs);
		border: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		text-align: center;
		line-height: 1.25;
	}
	.noeud strong {
		font-family: var(--font-display);
		font-size: var(--text-sm);
		font-weight: 600;
		color: var(--color-ink);
	}
	.noeud small,
	.segment small {
		font-size: var(--text-xs);
		color: var(--color-muted);
	}
	/* Le dépôt garde : la pile de ses feuilles, une par import, le seul orange au repos. */
	.pile {
		display: flex;
		flex-direction: column-reverse;
		gap: 2px;
		margin-bottom: var(--space-2xs);
	}
	.feuille {
		width: 1.75rem;
		height: 0.3rem;
		background: var(--color-accent);
		transform: translateX(calc((var(--k) - 1) * 2px));
	}

	/* Un segment : son étiquette au-dessus, son trait, le paquet qui le parcourt. Le segment est son propre conteneur :
	   le paquet le traverse d'une largeur, `100cqw`, sans jamais en sortir. */
	.segment {
		container-type: inline-size;
		display: grid;
		grid-template-rows: 1fr auto 1fr;
		align-self: stretch;
		text-align: center;
		line-height: 1.25;
	}
	.dessus {
		align-self: end;
		padding: 0 var(--space-2xs) var(--space-2xs);
	}
	.dessous {
		grid-row: 3;
		padding: var(--space-2xs) var(--space-2xs) 0;
	}
	.ligne {
		grid-row: 2;
		grid-column: 1;
		height: 2px;
		background: var(--color-rule-2);
	}
	/* Hors animation, le paquet n'existe pas. */
	.paquet {
		display: none;
	}

	/* Étroit : le tracé se dresse, de haut en bas, les segments en courts traits verticaux. */
	@container chemins (max-width: 30rem) {
		.trace {
			grid-template-columns: minmax(0, 1fr);
			justify-items: center;
		}
		.long {
			grid-column: auto;
		}
		.noeud {
			width: min(100%, 14rem);
			min-height: 0;
		}
		.segment {
			grid-template-rows: none;
			grid-template-columns: 1fr 2px 1fr;
			column-gap: var(--space-sm);
			width: 100%;
			min-height: 2.75rem;
			text-align: left;
		}
		.dessus {
			grid-column: 3;
			grid-row: 1;
			align-self: center;
			padding: 0;
		}
		.dessous {
			grid-column: 1;
			grid-row: 1;
			align-self: center;
			padding: 0;
			text-align: right;
		}
		.ligne {
			grid-column: 2;
			grid-row: 1;
			width: 2px;
			height: auto;
		}
	}

	@media screen and (prefers-reduced-motion: no-preference) {
		:global([data-js-etat]) .paquet {
			display: block;
			/* Dans la case du trait, posé dessus. */
			grid-row: 2;
			grid-column: 1;
			justify-self: start;
			align-self: center;
			width: var(--point);
			height: var(--point);
			border-radius: 50%;
			background: var(--color-accent);
			opacity: 0;
		}
		@container chemins (max-width: 30rem) {
			:global([data-js-etat]) .paquet {
				display: none;
			}
		}
		:global([data-js-etat='attente']) .feuille {
			opacity: 0;
			transform: translate(calc((var(--k) - 1) * 2px), -0.6rem);
		}

		/* Le direct : un aller-retour, du navigateur au canton et retour ; rien ne reste en route. */
		:global([data-js-etat='joue']) .direct .paquet {
			animation: aller-retour calc(var(--passe) * 2.4) var(--ease-in-out) 0.3s both;
		}
		/* L'import : trois passages, un par jour, et chaque fois une feuille de plus dans le dépôt ; puis la visite. */
		:global([data-js-etat='joue']) .import .segment:nth-child(2) .paquet {
			animation: passe var(--passe) var(--ease-in-out) 0.3s 3 both;
		}
		:global([data-js-etat='joue']) .feuille {
			animation: depose 0.45s var(--ease-out) calc(0.3s + (var(--k) + 1) * var(--passe) - 0.1s) both;
		}
		:global([data-js-etat='joue']) .import .segment:nth-child(4) .paquet {
			animation: passe var(--passe) var(--ease-in-out) calc(0.6s + 3 * var(--passe)) both;
		}
	}
	@keyframes passe {
		0% {
			opacity: 0;
			transform: none;
		}
		15% {
			opacity: 1;
		}
		85% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translateX(calc(100cqw - var(--point)));
		}
	}
	@keyframes aller-retour {
		0% {
			opacity: 0;
			transform: translateX(calc(100cqw - var(--point)));
		}
		8% {
			opacity: 1;
		}
		45%,
		55% {
			transform: none;
		}
		92% {
			opacity: 1;
		}
		100% {
			opacity: 0;
			transform: translateX(calc(100cqw - var(--point)));
		}
	}
	@keyframes depose {
		from {
			opacity: 0;
			transform: translate(calc((var(--k) - 1) * 2px), -0.6rem);
		}
		to {
			opacity: 1;
			transform: translateX(calc((var(--k) - 1) * 2px));
		}
	}
</style>
