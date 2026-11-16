<script lang="ts">
	/*
	 * Rail des couches : une icône par couche inscrite, dans l'ordre du registre, pleine si la couche est
	 * activée et cerclée sinon. Un clic ouvre ou ferme son volet. En tête, séparée des couches, l'entrée « Fil »
	 * ouvre le fil cantonal à la place des volets.
	 *
	 * C'est une barre d'outils verticale (motif « toolbar » de l'ARIA) : un seul arrêt de tabulation, sur la dernière
	 * icône touchée, et les flèches haut et bas, Début et Fin, d'une icône à l'autre.
	 */
	import { FIL, type Registre } from './registre.svelte.js';

	let { registre }: { registre: Registre } = $props();

	const basculer = (id: string) => (registre.volet = registre.volet === id ? null : id);

	/** Icône qui porte l'arrêt de tabulation : la dernière qui a eu le focus, sinon le Fil. */
	let arret = $state<string>(FIL);
	const ids = $derived([FIL, ...registre.couches.map((c) => c.id)]);

	function clavier(e: KeyboardEvent) {
		const i = ids.indexOf(arret);
		const j =
			e.key === 'ArrowDown'
				? (i + 1) % ids.length
				: e.key === 'ArrowUp'
					? (i - 1 + ids.length) % ids.length
					: e.key === 'Home'
						? 0
						: e.key === 'End'
							? ids.length - 1
							: -1;
		if (j < 0) return;
		e.preventDefault();
		arret = ids[j];
		(e.currentTarget as HTMLElement).querySelector<HTMLElement>(`[data-couche="${arret}"]`)?.focus();
	}
</script>

<!-- svelte-ignore a11y_interactive_supports_focus -->
<div class="rail" role="toolbar" aria-label="Couches" aria-orientation="vertical" onkeydown={clavier}>
	<button
		type="button"
		class="fil"
		data-couche={FIL}
		tabindex={arret === FIL ? 0 : -1}
		onfocus={() => (arret = FIL)}
		class:ouvert={registre.volet === FIL}
		aria-expanded={registre.volet === FIL}
		aria-controls={registre.volet === FIL ? 'volet-fil' : undefined}
		title="Fil cantonal&nbsp;: ce qui est nouveau"
		onclick={() => basculer(FIL)}
	>
		<span class="icone-fil" aria-hidden="true">≡</span>
		<span class="nom">Fil</span>
	</button>
	{#each registre.couches as c (c.id)}
		{@const active = registre.active(c.id)}
		<button
			type="button"
			data-couche={c.id}
			tabindex={arret === c.id ? 0 : -1}
			onfocus={() => (arret = c.id)}
			class:ouvert={registre.volet === c.id}
			aria-expanded={registre.volet === c.id}
			aria-controls={registre.volet === c.id ? `volet-${c.id}` : undefined}
			title="{c.nom}&nbsp;: {active ? 'affichée' : 'masquée'}"
			onclick={() => basculer(c.id)}
		>
			<span class="icone" class:off={!active} style:--c={c.icone.couleur} aria-hidden="true">{c.icone.signe}</span>
			<span class="nom">{c.nom}</span>
			<span class="etat">{active ? '' : '(masquée)'}</span>
		</button>
	{/each}
</div>

<style>
	/* Le rail des couches : du papier, un filet à droite ; la couche ouverte posée sur une feuille, marquée d'un trait
	   orange au bord, comme l'intertitre courant d'un sommaire. */
	.rail {
		display: flex;
		flex-direction: column;
		gap: 4px;
		/* Téléphone à l'horizontale : le rail, au bord gauche, s'écarte de l'encoche. */
		padding: 8px 4px 8px max(4px, env(safe-area-inset-left));
		background: var(--color-paper);
		border-right: var(--rule-hair) solid var(--color-rule);
		overflow-y: auto;
	}
	button {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 3px;
		padding: 8px 2px;
		border: 0;
		border-radius: 0;
		background: none;
		font: inherit;
		font-size: 11px;
		color: var(--color-ink-2);
		cursor: pointer;
		text-align: center;
	}
	button:hover {
		background: var(--color-paper-2);
	}
	button.ouvert {
		background: var(--color-sheet);
		box-shadow: inset var(--rule-bar) 0 0 var(--color-accent);
		color: var(--color-ink);
	}
	/* Ouverte, la couche se pose au survol sur le papier, comme les autres, et garde son trait orange. */
	button.ouvert:hover {
		background: var(--color-paper-2);
	}
	.fil {
		margin-bottom: 6px;
		padding-bottom: 10px;
		border-bottom: 1px solid var(--color-rule-2);
		font-weight: 600;
	}
	.icone-fil {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: var(--radius-pill);
		background: var(--color-ink);
		color: #fff;
		font-size: 18px;
	}
	/* Les icônes des couches : des carrés à angle droit, comme le signe des entrées du fil et l'icône du Fil. La couleur
	   de la couche quand elle est affichée ; masquée, un cadre de sa couleur sur la feuille. */
	.icone {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border-radius: var(--radius-pill);
		background: var(--c);
		color: #fff;
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 15px;
		transition: transform var(--dur-short) var(--ease-out);
	}
	.icone.off {
		background: var(--color-sheet);
		color: var(--c);
		box-shadow: inset 0 0 0 var(--rule-bar) var(--c);
	}
	button:active .icone {
		transform: scale(0.94);
	}
	/* Sans mouvement, l'icône appuyée ne bouge pas. */
	@media (prefers-reduced-motion: reduce) {
		.icone {
			transition: none;
		}
	}
	.nom {
		font-size: 0.6875rem;
		line-height: 1.2;
	}
	/* Pour les lecteurs d'écran seulement : l'icône cerclée le dit aux yeux. */
	.etat {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip-path: inset(50%);
		white-space: nowrap;
	}
</style>
