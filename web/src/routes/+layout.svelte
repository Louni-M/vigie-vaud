<script lang="ts">
	import '#lib/almanach/almanach.css';
	import favicon from '#lib/assets/favicon.svg';
	import { afterNavigate, beforeNavigate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page, updated } from '$app/state';
	import { adresseDeComptage, AUDIENCE, cheminACompter } from '#lib/audience.js';
	import { SITE } from '#lib/config.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Chaque changement de page est compté ici, par son chemin seul : les navigations de l'application (fiche
	// commune, retour à la carte) sont ainsi comptées, et les paramètres de la carte jamais. Le pixel part sans
	// en-tête Referer, qui porterait l'adresse complète de la page.
	if (AUDIENCE) {
		const mesure = AUDIENCE;
		afterNavigate(({ from, to }) => {
			const chemin = cheminACompter(from?.url, to?.url);
			if (!chemin) return;
			const pixel = new Image();
			pixel.referrerPolicy = 'no-referrer';
			pixel.src = adresseDeComptage(mesure, chemin, Math.random());
		});
	}
	// Après un déploiement (vu au retour sur l'onglet, ou par le contrôle horaire de SvelteKit), un changement de
	// page charge la nouvelle version en entier. Les déplacements de la carte restent sur la même page.
	beforeNavigate(({ from, to, willUnload }) => {
		if (updated.current && !willUnload && to?.url && to.url.pathname !== from?.url.pathname) {
			location.href = to.url.href;
		}
	});
	// « Carte » reste marqué comme page courante quand une fiche commune est ouverte sur la carte.
	const nav = [
		{ href: resolve('/(carte)'), label: 'Carte', groupe: '/(carte)' },
		{ href: resolve('/couverture'), label: 'Sources par commune', groupe: '/couverture' },
		{ href: resolve('/a-propos'), label: 'À propos', groupe: '/a-propos' }
	];
	const courant = (groupe: string) => page.route.id === groupe || !!page.route.id?.startsWith(`${groupe}/`);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<!-- Aperçu des liens partagés : une image commune à tout le site, à l'adresse publique (absolue). LinkedIn garde
		l'image en cache selon son adresse : quand apercu.png change, augmenter `v` pour qu'il la relise. -->
	<meta property="og:site_name" content="Vigie Vaud" />
	<meta property="og:locale" content="fr_CH" />
	<meta property="og:image" content="{SITE}/apercu.png?v=2" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:image:alt" content="Vigie Vaud : ce qui se passe dans votre commune, sur la carte du canton de Vaud" />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<!-- L'en-tête du site, dans le système Almanach (#165) : un bandeau de papier clair sur un filet d'encre, la marque à
	gauche, la page courante soulignée d'orange. -->
<!-- Lien d'évitement : chaque page porte son contenu dans <main id="contenu">. -->
<a class="evitement-contenu" href="#contenu">Aller au contenu</a>

<header>
	<a class="marque" href={resolve('/(carte)')}>
		<!-- Le repère de la vigie : un anneau d'encre et son point orange, qui sert aussi d'icône d'onglet. -->
		<svg class="repere" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
			<circle cx="12" cy="12" r="9" />
			<circle class="point" cx="12" cy="12" r="3.5" />
		</svg>
		<span translate="no">Vigie <span class="vaud">Vaud</span></span>
	</a>
	<nav aria-label="Navigation principale">
		{#each nav as l (l.href)}
			<a href={l.href} aria-current={courant(l.groupe) ? 'page' : undefined}>{l.label}</a>
		{/each}
	</nav>
</header>

{@render children()}

<style>
	/* Hors de l'écran tant qu'il n'a pas le focus clavier. */
	.evitement-contenu {
		position: absolute;
		top: 8px;
		left: 8px;
		z-index: 30;
		padding: 10px 14px;
		background: var(--color-sheet);
		color: var(--color-ink);
		font-weight: 600;
		box-shadow: 0 0 0 2px var(--color-ink);
	}
	.evitement-contenu:not(:focus) {
		clip-path: inset(50%);
		width: 1px;
		height: 1px;
		overflow: hidden;
		white-space: nowrap;
		padding: 0;
	}
	header {
		height: var(--size-header);
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: 0 max(var(--space-md), env(safe-area-inset-right)) 0 max(var(--space-md), env(safe-area-inset-left));
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		color: var(--color-ink);
		font-family: var(--font-display);
		position: sticky;
		top: 0;
		z-index: 10;
	}
	/* La marque : le repère, puis le nom, serré comme un titre, « Vaud » en orange. */
	.marque {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		min-height: 44px;
		color: var(--color-ink);
		text-decoration: none;
		font-size: 1.1875rem;
		font-weight: 700;
		letter-spacing: -0.03em;
		white-space: nowrap;
	}
	.vaud {
		color: var(--color-accent);
	}
	/* Au survol, le point du repère grossit : la marque mène à la carte. */
	.marque:hover .repere .point {
		transform: scale(1.35);
	}
	.repere {
		flex: none;
		fill: none;
		stroke: var(--color-ink);
		stroke-width: 2.25;
	}
	.repere .point {
		fill: var(--color-accent);
		stroke: none;
		transform-box: fill-box;
		transform-origin: center;
		transition: transform var(--dur-short) var(--ease-out);
	}
	nav {
		display: flex;
		align-self: stretch;
		gap: var(--space-lg);
		margin-left: auto;
		font-size: var(--text-sm);
	}
	nav a {
		/* Zone tactile de toute la hauteur du bandeau. */
		position: relative;
		display: flex;
		align-items: center;
		min-height: 44px;
		padding: 0 var(--space-3xs);
		color: var(--color-muted);
		text-decoration: none;
		white-space: nowrap;
	}
	/* Le trait de la page courante, posé juste au-dessus du filet d'encre du bandeau ; au survol, un trait d'encre se
	   déroule. */
	nav a::after {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		border-top: var(--rule-bar) solid var(--color-rule-2);
		transform: scaleX(0);
		transform-origin: left;
		transition: transform var(--dur-short) var(--ease-out);
	}
	@media (prefers-reduced-motion: reduce) {
		nav a::after,
		.repere .point {
			transition: none;
		}
	}
	nav a:hover {
		color: var(--color-ink);
	}
	nav a:hover::after {
		transform: none;
	}
	nav a[aria-current='page'] {
		color: var(--color-ink);
		font-weight: 600;
	}
	nav a[aria-current='page']::after {
		border-top-color: var(--color-accent);
		transform: none;
	}
	/* La page courante, survolée : son trait s'épaissit. */
	nav a[aria-current='page']:hover::after {
		transform: scaleY(2);
		transform-origin: bottom;
	}
	@media (max-width: 420px) {
		header {
			gap: var(--space-sm);
			padding: 0 max(var(--space-sm), env(safe-area-inset-right)) 0 max(var(--space-sm), env(safe-area-inset-left));
		}
		.marque {
			gap: var(--space-2xs);
			font-size: var(--text-md);
		}
		.repere {
			width: 20px;
			height: 20px;
		}
		nav {
			gap: var(--space-sm);
			font-size: var(--text-xs);
		}
		/* Un libellé long (« Sources par commune ») passe sur deux lignes plutôt que de pousser le menu hors de l'écran. */
		nav a {
			max-width: 6.5em;
			line-height: 1.15;
			text-align: center;
			white-space: normal;
		}
	}
	/* Une page imprimée n'a que faire de la navigation. */
	@media print {
		header {
			display: none;
		}
	}
</style>
