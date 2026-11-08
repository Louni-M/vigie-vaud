<script lang="ts">
	import Diagramme from '#lib/almanach/Diagramme.svelte';

	// Le rattachement en direct (#165) : le titre d'un Objet du Grand Conseil, lu nom après nom, comme le décrivent
	// les règles de la section. Le titre est inventé ; passé par `rattacher` (pipeline/rattachement.py), il ne
	// rattache que Yverdon-les-Bains : Gressy y mène, Chavannes et l'avenue de Morges sont écartés.
	// Les espaces insécables devant « : » et « ? » sont écrites `\u00a0` : un caractère littéral ne se voit pas
	// à la relecture.

	type Morceau = { texte: string; verdict?: { retenu: boolean; detail: string } };

	const morceaux: Morceau[] = [
		{ texte: 'Interpellation\u00a0: où en sont les pistes cyclables à ' },
		{ texte: 'Gressy', verdict: { retenu: true, detail: 'ancienne commune, mène à Yverdon-les-Bains' } },
		{ texte: ', à ' },
		{ texte: 'Chavannes', verdict: { retenu: false, detail: 'écarté, plusieurs communes portent ce nom' } },
		{ texte: ' et le long de l’' },
		{ texte: 'avenue de Morges', verdict: { retenu: false, detail: 'écarté, c’est une rue' } },
		{ texte: '\u00a0?' }
	];

	/** Où tombe le milieu de chaque morceau dans le titre, de 0 à 1 : la lecture l'atteint à ce moment-là. */
	const total = morceaux.reduce((n, m) => n + m.texte.length, 0);
	const positions = morceaux.map((_, i) => {
		const debut = morceaux.slice(0, i).reduce((n, m) => n + m.texte.length, 0);
		return (debut + morceaux[i].texte.length / 2) / total;
	});
	const noms = morceaux.flatMap((m, i) => (m.verdict ? [{ ...m, verdict: m.verdict, t: positions[i] }] : []));
</script>

<Diagramme legende="Titre inventé">
	<div class="demo">
		<p class="tete"><span class="conseil">Grand Conseil</span> le titre d’un Objet</p>
		<p class="phrase">
			<span class="lecture"></span>
			{#each morceaux as m, i (i)}
				{#if m.verdict}
					<span class="nom" class:retenu={m.verdict.retenu} style:--t={positions[i]} data-texte={m.texte}
						><span class="verdict">{m.texte}</span></span
					>
				{:else}{m.texte}{/if}
			{/each}
		</p>
		<ul class="verdicts">
			{#each noms as n (n.texte)}
				<li class:retenu={n.verdict.retenu} style:--t={n.t}>
					<svg viewBox="0 0 16 16" width="16" height="16">
						{#if n.verdict.retenu}
							<path d="M3 8.5 6.5 12 13 4.5" />
						{:else}
							<path d="M4 4l8 8M12 4l-8 8" />
						{/if}
					</svg>
					<strong>{n.texte}</strong>
					<span>{n.verdict.detail}</span>
				</li>
			{/each}
		</ul>
		<p class="resultat">Rattaché à <strong>Yverdon-les-Bains</strong></p>
	</div>
</Diagramme>

<style>
	.demo {
		container-type: inline-size;
		--depart: 0.25s;
		--lecture: 2.4s;
	}
	.tete {
		margin: 0 0 var(--space-xs);
		font-size: var(--text-sm);
		color: var(--color-muted);
	}
	.conseil {
		margin-right: var(--space-2xs);
		font-family: var(--font-display);
		font-weight: 600;
		color: var(--color-ink);
	}
	.phrase {
		position: relative;
		isolation: isolate;
		margin: 0;
		font-size: var(--text-lead);
		line-height: 1.75;
		color: var(--color-ink);
	}
	/* Un nom retenu est souligné d'encre ; un nom écarté est barré, en gris. */
	.verdict {
		text-decoration-line: line-through;
		text-decoration-thickness: var(--rule-bar);
		text-decoration-color: var(--color-muted);
		color: var(--color-muted);
	}
	.retenu .verdict {
		text-decoration-line: underline;
		text-decoration-color: var(--color-accent);
		text-underline-offset: 0.2em;
		color: var(--color-ink);
	}
	/* La lecture : un lavis orange mené par un trait, qui passe sur le titre. Hors animation, il n'existe pas. */
	.lecture {
		display: none;
	}

	.verdicts {
		list-style: none;
		margin: var(--space-md) 0 0;
		padding: 0;
		font-size: var(--text-sm);
		line-height: 1.4;
	}
	.verdicts li {
		display: grid;
		grid-template-columns: 1rem 9rem minmax(0, 1fr);
		align-items: baseline;
		gap: var(--space-xs);
		padding-block: var(--space-2xs);
		border-top: var(--rule-hair) solid var(--color-rule);
		color: var(--color-muted);
	}
	.verdicts svg {
		align-self: center;
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	.verdicts strong {
		font-family: var(--font-display);
		font-weight: 600;
	}
	.verdicts .retenu {
		color: var(--color-ink);
	}
	.verdicts .retenu svg {
		color: var(--color-accent);
	}
	.resultat {
		margin: var(--space-sm) 0 0;
		padding-top: var(--space-sm);
		border-top: var(--rule-bar) solid var(--color-rule-2);
		font-family: var(--font-display);
		font-size: var(--text-md);
		color: var(--color-muted);
	}
	.resultat strong {
		margin-left: var(--space-2xs);
		font-weight: 600;
		color: var(--color-ink);
	}
	.resultat strong::before {
		content: '';
		display: inline-block;
		width: 0.55rem;
		height: 0.55rem;
		margin-right: var(--space-xs);
		border-radius: 50%;
		background: var(--color-accent);
		vertical-align: 0.08em;
	}

	@container (max-width: 30rem) {
		.verdicts li {
			grid-template-columns: 1rem minmax(0, 1fr);
		}
		.verdicts li span {
			grid-column: 2;
		}
	}
	@media screen and (prefers-reduced-motion: no-preference) {
		.lecture {
			position: absolute;
			inset: 0;
			z-index: -1;
			overflow: clip;
		}
		.lecture::before {
			content: '';
			position: absolute;
			inset: 0;
			border-right: var(--rule-bar) solid var(--color-accent);
			background: linear-gradient(to right, transparent, var(--color-accent-wash));
			transform: translateX(-100%);
			opacity: 0;
		}
		:global([data-js-etat]) .lecture {
			display: block;
		}
		/* Le nom, en trois couches superposées à l'identique : le texte brut (encre), le nom allumé (orange), puis son
		   verdict, qui est le texte au repos. Le nom ne passe pas à la ligne, pour que les couches se recouvrent : on ne
		   fait que fondre de l'une à l'autre. */
		:global([data-js-etat]) .nom {
			position: relative;
			display: inline-block;
			white-space: nowrap;
		}
		:global([data-js-etat]) .nom::before,
		:global([data-js-etat]) .nom::after {
			content: attr(data-texte);
			position: absolute;
			inset: 0;
			opacity: 0;
		}
		:global([data-js-etat]) .nom::before {
			color: var(--color-ink);
		}
		:global([data-js-etat]) .nom::after {
			color: var(--color-accent);
		}
		/* Le verdict passe au-dessus des deux autres couches : il couvre le nom allumé pendant qu'il arrive. */
		:global([data-js-etat]) .verdict {
			position: relative;
			z-index: 1;
		}
		/* Avant la lecture, les noms sont encore du texte comme le reste ; leur verdict n'est pas rendu. */
		:global([data-js-etat='attente']) .nom::before {
			opacity: 1;
		}
		:global([data-js-etat='attente']) .verdict {
			opacity: 0;
		}
		:global([data-js-etat='attente']) .verdicts li,
		:global([data-js-etat='attente']) .resultat {
			opacity: 0;
		}

		:global([data-js-etat='joue']) .lecture::before {
			animation: lit var(--lecture) var(--ease-in-out) var(--depart) both;
		}
		:global([data-js-etat='joue']) .nom {
			--quand: calc(var(--depart) + var(--t) * var(--lecture));
		}
		:global([data-js-etat='joue']) .nom::before {
			animation: juge-brut 1.2s var(--ease-out) var(--quand) both;
		}
		:global([data-js-etat='joue']) .nom::after {
			animation: juge-allume 1.2s var(--ease-out) var(--quand) both;
		}
		:global([data-js-etat='joue']) .verdict {
			animation: juge-verdict 1.2s var(--ease-out) var(--quand) both;
		}
		:global([data-js-etat='joue']) .verdicts li {
			animation: monte 0.5s var(--ease-out) calc(var(--depart) + var(--t) * var(--lecture) + 0.5s) both;
		}
		/* La coche se déplie de gauche à droite, dans le sens où elle se trace ; la croix s'ouvre depuis son centre. */
		:global([data-js-etat='joue']) .verdicts svg {
			transform-origin: left center;
			animation: deplie 0.4s var(--ease-out) calc(var(--depart) + var(--t) * var(--lecture) + 0.7s) both;
		}
		:global([data-js-etat='joue']) .verdicts li:not(.retenu) svg {
			transform-origin: center;
			animation-name: ouvre;
		}
		:global([data-js-etat='joue']) .resultat {
			animation: monte 0.55s var(--ease-out) calc(var(--depart) + var(--lecture) + 0.8s) both;
		}
	}
	@keyframes lit {
		0% {
			transform: translateX(-100%);
			opacity: 1;
		}
		85% {
			transform: none;
			opacity: 1;
		}
		100% {
			transform: none;
			opacity: 0;
		}
	}
	/* Le nom atteint s'allume en orange, puis prend son verdict, souligné ou barré : la fin de l'animation est son
	   style au repos. Le nom allumé arrive sur le texte brut, qui s'efface une fois couvert ; le verdict arrive sur le
	   nom allumé, qui s'efface une fois couvert. */
	@keyframes juge-brut {
		0%,
		25% {
			opacity: 1;
		}
		26%,
		100% {
			opacity: 0;
		}
	}
	@keyframes juge-allume {
		0% {
			opacity: 0;
		}
		25%,
		99% {
			opacity: 1;
		}
		100% {
			opacity: 0;
		}
	}
	@keyframes juge-verdict {
		0%,
		55% {
			opacity: 0;
		}
		100% {
			opacity: 1;
		}
	}
	@keyframes monte {
		from {
			opacity: 0;
			transform: translateY(0.4rem);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes deplie {
		from {
			opacity: 0;
			transform: scaleX(0);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes ouvre {
		from {
			opacity: 0;
			transform: scale(0);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
</style>
