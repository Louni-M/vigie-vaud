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
		{ href: resolve('/couverture'), label: 'Couverture', groupe: '/couverture' },
		{ href: resolve('/a-propos'), label: 'À propos', groupe: '/a-propos' }
	];
	const courant = (groupe: string) => page.route.id === groupe || !!page.route.id?.startsWith(`${groupe}/`);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<!-- Aperçu des liens partagés : une image commune à tout le site, à l'adresse publique (absolue). -->
	<meta property="og:site_name" content="Vigie Vaud" />
	<meta property="og:locale" content="fr_CH" />
	<meta property="og:image" content="{SITE}/apercu.png" />
	<meta property="og:image:width" content="1200" />
	<meta property="og:image:height" content="630" />
	<meta property="og:image:alt" content="Vigie Vaud : ce qui se passe dans votre commune, sur la carte du canton de Vaud" />
	<meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<!-- L'en-tête du site, dans le système Almanach (#165) : un bandeau de papier clair sur un filet d'encre, la marque à
	gauche, la page courante soulignée d'orange. -->
<header data-theme="almanach">
	<a class="marque" href={resolve('/(carte)')}>
		<!-- Le repère de la vigie : un anneau d'encre et son point orange, qui sert aussi d'icône d'onglet. -->
		<svg class="repere" viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
			<circle cx="12" cy="12" r="9" />
			<circle class="point" cx="12" cy="12" r="3.5" />
		</svg>
		<span>Vigie <span class="vaud">Vaud</span></span>
	</a>
	<nav>
		{#each nav as l (l.href)}
			<a href={l.href} aria-current={courant(l.groupe) ? 'page' : undefined}>{l.label}</a>
		{/each}
	</nav>
</header>

{@render children()}

<style>
	:global(:root) {
		color-scheme: light;
		--bg: #f6f7f9;
		--surface: #ffffff;
		--surface-2: #f8f6f2;
		--text: #1d2330;
		--muted: #687082;
		--line: #dfe3ea;
		--accent: #1f3a5f;
		--enquete: #d9480f;
		/* Variante plus foncée pour le texte (contraste AA sur fond blanc). */
		--enquete-texte: #b93d0b;
		--erreur: #b02a00;
		--focus: #1f6feb;
		--header-h: 52px;
	}
	:global(*) {
		box-sizing: border-box;
	}
	:global(html, body) {
		margin: 0;
		background: var(--bg);
		color: var(--text);
		font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
		-webkit-text-size-adjust: 100%;
	}
	:global(a) {
		color: var(--accent);
	}
	:global(:focus-visible) {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}
	:global(.bouton) {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		min-height: 40px;
		padding: 9px 14px;
		border-radius: 8px;
		background: var(--accent);
		color: #fff;
		text-decoration: none;
		font-weight: 600;
		font-size: 14px;
		border: 0;
		cursor: pointer;
	}
	@media (pointer: coarse) {
		:global(.bouton) {
			min-height: 44px;
		}
	}
	:global(.bouton.secondaire) {
		background: var(--surface);
		color: var(--accent);
		box-shadow: inset 0 0 0 1px var(--accent);
	}
	:global(.page) {
		max-width: 860px;
		margin: 0 auto;
		padding: 20px 16px 48px;
	}
	:global(.source) {
		font-size: 12px;
		color: var(--muted);
	}
	header {
		height: var(--header-h);
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: 0 var(--space-md);
		border-bottom: var(--rule-bar) solid var(--color-rule-2);
		background: var(--color-sheet);
		color: var(--color-ink);
		font-family: var(--font-display);
		position: sticky;
		top: 0;
		z-index: 10;
	}
	header :focus-visible {
		outline: var(--rule-bar) solid var(--color-focus);
		outline-offset: var(--space-3xs);
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
	.repere {
		flex: none;
		fill: none;
		stroke: var(--color-ink);
		stroke-width: 2.25;
	}
	.repere .point {
		fill: var(--color-accent);
		stroke: none;
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
		transition: color var(--dur-short) var(--ease-out);
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
	@media (max-width: 420px) {
		header {
			gap: var(--space-sm);
			padding: 0 var(--space-sm);
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
	}
	/* Une page imprimée n'a que faire de la navigation. */
	@media print {
		header {
			display: none;
		}
	}
</style>
