<script lang="ts">
	import favicon from '#lib/assets/favicon.svg';
	import { afterNavigate } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { AUDIENCE, cheminACompter } from '#lib/audience.js';
	import { SITE } from '#lib/config.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Le script de GoatCounter ne compte rien de lui-même (`no_onload`) : chaque changement de page est compté
	// ici, par son chemin seul. Les navigations de l'application (fiche commune, retour à la carte) sont ainsi
	// comptées, et les paramètres de la carte jamais.
	type GoatCounter = { count?: (v: { path: string }) => void };
	const compter = (path: string) => {
		const gc = (window as { goatcounter?: GoatCounter }).goatcounter;
		if (gc?.count) return gc.count({ path });
		// Script pas encore chargé (il est asynchrone) : on compte dès qu'il l'est.
		document
			.querySelector('script[data-goatcounter]')
			?.addEventListener('load', () => (window as { goatcounter?: GoatCounter }).goatcounter?.count?.({ path }), {
				once: true
			});
	};
	if (AUDIENCE) {
		afterNavigate(({ from, to }) => {
			const chemin = cheminACompter(from?.url, to?.url);
			if (chemin) compter(chemin);
		});
	}
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
	{#if AUDIENCE}
		<script
			data-goatcounter={AUDIENCE.compteur}
			data-goatcounter-settings={'{"no_onload":true}'}
			async
			src="https://gc.zgo.at/count.js"
		></script>
	{/if}
</svelte:head>

<header>
	<a class="marque" href={resolve('/(carte)')}>Vigie <span>Vaud</span></a>
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
		gap: 16px;
		padding: 0 16px;
		background: var(--accent);
		color: #fff;
		position: sticky;
		top: 0;
		z-index: 10;
	}
	header :focus-visible {
		outline-color: #fff;
	}
	.marque {
		/* Pas de flex ici : l'espace entre « Vigie » et « Vaud » serait supprimé. */
		display: inline-block;
		padding: 11px 0;
		line-height: 22px;
		color: #fff;
		text-decoration: none;
		font-weight: 700;
		font-size: 18px;
		white-space: nowrap;
	}
	.marque span {
		color: #ffb38a;
	}
	nav {
		display: flex;
		gap: 14px;
		margin-left: auto;
		font-size: 14px;
	}
	nav a {
		/* Zone tactile d'au moins 44 px de haut. */
		display: flex;
		align-items: center;
		min-height: 44px;
		padding: 0 2px;
		color: #dfe7f2;
		text-decoration: none;
		white-space: nowrap;
	}
	@media (max-width: 420px) {
		header {
			gap: 10px;
			padding: 0 12px;
		}
		.marque {
			font-size: 16px;
		}
		nav {
			gap: 10px;
			font-size: 13px;
		}
	}
	nav a[aria-current='page'] {
		color: #fff;
		font-weight: 600;
	}
</style>
