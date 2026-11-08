<script lang="ts">
	import { AUDIENCE } from '#lib/audience.js';
	import Diagramme from '#lib/almanach/Diagramme.svelte';

	// Le trajet de votre visite (#165) : ce que l'appareil du visiteur envoie à chaque destinataire. Il reprend le
	// tableau des destinataires de la page, à revoir avec lui ; GoatCounter n'y est que si la mesure d'audience est
	// activée. La position « Autour de moi » ne part nulle part : elle reste dans l'appareil.
	const destinataires = [
		{ nom: 'GitHub Pages', pays: 'États-Unis', role: 'héberge le site', envoi: ['adresse IP'] },
		{
			nom: 'swisstopo',
			pays: 'Suisse',
			role: 'fond de carte, adresses',
			envoi: ['adresse IP', 'zone affichée', 'recherche']
		},
		{ nom: 'État de Vaud', pays: 'Suisse', role: 'permis, routes', envoi: ['adresse IP', 'zone affichée'] },
		...(AUDIENCE
			? [{ nom: 'GoatCounter', pays: 'Irlande', role: 'mesure d’audience', envoi: ['adresse IP', 'chemin de la page', 'navigateur'] }]
			: [])
	];
</script>

<Diagramme>
	<div class="trajet" style:--n={destinataires.length}>
		<div class="plan">
			<div class="appareil">
				<svg aria-hidden="true" class="ecran" viewBox="0 0 48 40" width="48" height="40">
					<rect x="4" y="3" width="40" height="26" rx="2" />
					<path d="M1 34h46M17 29l-2 5M31 29l2 5" />
				</svg>
				<strong>Votre appareil</strong>
				<span class="position">
					<svg aria-hidden="true" class="repere" viewBox="0 0 20 20" width="20" height="20">
						<g class="anneau"><circle cx="10" cy="10" r="8" /></g>
						<circle class="point" cx="10" cy="10" r="3.5" />
					</svg>
					Votre position «&nbsp;Autour de moi&nbsp;» reste ici
				</span>
			</div>
			<ol class="liens">
				{#each destinataires as d, i (d.nom)}
					<li style:--i={i}>
						<span class="fil">
							<span class="cable"></span>
							<span class="paquet"></span>
							<span class="envoi">
								{#each d.envoi as e, j (e)}<span class="puce" style:--j={j}>{e}</span>{/each}
							</span>
						</span>
						<span class="destinataire">
							<strong>{d.nom}</strong>
							<span class="role">{d.role}</span>
							<span class="pays">{d.pays}</span>
						</span>
					</li>
				{/each}
			</ol>
		</div>
	</div>
</Diagramme>

<style>
	.trajet {
		container-type: inline-size;
	}
	.plan {
		display: grid;
		grid-template-columns: 10.5rem minmax(0, 1fr);
		align-items: center;
	}
	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.appareil {
		position: relative;
		z-index: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-xs);
		padding: var(--space-md) var(--space-sm);
		border: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		color: var(--color-ink);
		font-family: var(--font-display);
		text-align: center;
	}
	.position {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		font-family: var(--font-body);
		font-size: var(--text-xs);
		line-height: 1.35;
		color: var(--color-muted);
		text-align: left;
	}
	.repere {
		flex: none;
		/* L'anneau qui se referme part de plus loin que le dessin. */
		overflow: visible;
		color: var(--color-ink);
	}
	.anneau {
		stroke-width: 1.5;
		transform-box: fill-box;
		transform-origin: center;
	}
	.point {
		fill: var(--color-ink);
		stroke: none;
		transform-box: fill-box;
		transform-origin: center;
	}
	.liens {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--space-sm);
	}
	.liens li {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 12rem;
		align-items: center;
	}
	.fil {
		position: relative;
		min-height: 3.25rem;
		display: flex;
		/* Les données reçues sont posées sur le câble, comme des perles sur un fil. */
		align-items: center;
		justify-content: center;
		padding-inline: var(--space-sm);
	}
	/* Le câble, de l'appareil au destinataire, et le paquet qui le parcourt. Le paquet est une bande aussi large que
	   le câble, son point au bord droit : la faire glisser d'une largeur promène le point d'un bout à l'autre. */
	.cable,
	.paquet {
		position: absolute;
		left: 0;
		right: 0;
		top: 50%;
	}
	.cable {
		border-top: var(--rule-hair) dashed var(--color-rule-2);
		transform-origin: left;
	}
	.paquet {
		display: none;
	}
	.envoi {
		position: relative;
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: var(--space-2xs);
	}
	.puce {
		padding: 0 var(--space-xs);
		border: var(--rule-hair) solid var(--color-rule);
		border-radius: var(--radius-pill);
		background: var(--color-sheet);
		color: var(--color-ink);
		font-size: var(--text-xs);
		line-height: 1.5;
		white-space: nowrap;
	}
	.destinataire {
		position: relative;
		isolation: isolate;
		display: grid;
		padding: var(--space-xs) 0 var(--space-xs) var(--space-sm);
		border-left: var(--rule-bar) solid var(--color-rule-2);
		line-height: 1.3;
	}
	.destinataire strong {
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}
	.role,
	.pays {
		font-size: var(--text-xs);
		color: var(--color-muted);
	}
	/* Le reflet qui dit « reçu » quand le paquet arrive. */
	.destinataire::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: -1;
		background: var(--color-accent-wash);
		opacity: 0;
	}

	/* Étroit : l'appareil passe au-dessus, un tronc à gauche relie les fils. */
	@container (max-width: 34rem) {
		.plan {
			grid-template-columns: minmax(0, 1fr);
		}
		.appareil {
			flex-direction: row;
			flex-wrap: wrap;
			justify-content: center;
			gap: var(--space-xs) var(--space-sm);
			padding: var(--space-sm);
		}
		.ecran {
			width: 36px;
			height: 30px;
		}
		.liens {
			position: relative;
			margin-left: var(--space-md);
			padding-top: var(--space-md);
		}
		.liens::before {
			content: '';
			position: absolute;
			top: 0;
			bottom: 1.6rem;
			left: 0;
			border-left: var(--rule-hair) dashed var(--color-rule-2);
			transform-origin: top;
		}
		.liens li {
			grid-template-columns: minmax(0, 1fr);
			gap: var(--space-2xs);
			padding-left: var(--space-lg);
		}
		.fil {
			order: 2;
			position: static;
			min-height: 0;
			justify-content: flex-start;
			padding-inline: 0;
		}
		.cable {
			left: 0;
			right: auto;
			top: 1.6rem;
			width: var(--space-md);
		}
		.liens li {
			position: relative;
		}
		.envoi {
			justify-content: flex-start;
		}
		.destinataire {
			padding-block: var(--space-2xs);
		}
	}

	@media screen and (prefers-reduced-motion: no-preference) {
		.trajet {
			--pas: 0.5s;
		}
		:global([data-js-etat]) .paquet {
			display: block;
			transform: translateX(-100%);
			opacity: 0;
		}
		.paquet::after {
			content: '';
			position: absolute;
			right: calc(-1 * var(--space-2xs));
			top: calc(-1 * var(--space-2xs));
			width: var(--space-xs);
			height: var(--space-xs);
			border-radius: 50%;
			background: var(--color-accent);
		}
		@container (max-width: 34rem) {
			.paquet {
				display: none !important;
			}
		}

		:global([data-js-etat='attente']) .cable,
		:global([data-js-etat='attente']) .liens::before {
			transform: scale(0);
		}
		:global([data-js-etat='attente']) .puce,
		:global([data-js-etat='attente']) .destinataire {
			opacity: 0;
		}
		:global([data-js-etat='attente']) .ecran,
		:global([data-js-etat='attente']) .anneau {
			opacity: 0;
		}

		:global([data-js-etat='joue']) .ecran {
			animation: allume 0.9s var(--ease-out) 0.1s both;
		}
		:global([data-js-etat='joue']) .liens::before {
			animation: deploie 0.6s var(--ease-out) 0.3s both;
		}
		:global([data-js-etat='joue']) .cable {
			animation: deploie 0.5s var(--ease-out) calc(0.35s + var(--i) * var(--pas)) both;
		}
		:global([data-js-etat='joue']) .paquet {
			animation: voyage 0.75s var(--ease-in-out) calc(0.5s + var(--i) * var(--pas)) both;
		}
		:global([data-js-etat='joue']) .puce {
			animation: arrive 0.45s var(--ease-out) calc(0.75s + var(--i) * var(--pas) + var(--j) * 0.07s) both;
		}
		:global([data-js-etat='joue']) .destinataire {
			animation: arrive-cote 0.5s var(--ease-out) calc(1s + var(--i) * var(--pas)) both;
		}
		:global([data-js-etat='joue']) .destinataire::before {
			animation: recu 1.1s var(--ease-out) calc(1.15s + var(--i) * var(--pas)) both;
		}
		/* Une fois tous les paquets partis, l'anneau se referme autour de la position : elle, ne bouge pas. */
		:global([data-js-etat='joue']) .anneau {
			animation: referme 0.8s var(--ease-in-out) calc(1.2s + var(--n) * var(--pas)) both;
		}
		:global([data-js-etat='joue']) .point {
			animation: pose 0.5s var(--ease-out) calc(1.2s + var(--n) * var(--pas)) both;
		}
	}
	@keyframes allume {
		from {
			opacity: 0;
			transform: scale(0.85);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes referme {
		from {
			opacity: 0;
			transform: scale(1.6);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes deploie {
		from {
			transform: scale(0, 1);
		}
		to {
			transform: none;
		}
	}
	@keyframes voyage {
		0% {
			transform: translateX(-100%);
			opacity: 0;
		}
		12% {
			opacity: 1;
		}
		88% {
			opacity: 1;
		}
		100% {
			transform: none;
			opacity: 0;
		}
	}
	@keyframes arrive {
		from {
			opacity: 0;
			transform: translateY(0.4em) scale(0.94);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes arrive-cote {
		from {
			opacity: 0;
			transform: translateX(-0.5rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes recu {
		0% {
			opacity: 0;
		}
		25% {
			opacity: 1;
		}
		100% {
			opacity: 0;
		}
	}
	@keyframes pose {
		0% {
			transform: scale(1);
		}
		40% {
			transform: scale(1.35);
		}
		100% {
			transform: scale(1);
		}
	}
</style>
