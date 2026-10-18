/// <reference types="vitest/config" />
import { existsSync, readFileSync } from 'node:fs';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { donneesLocales } from './scripts/donnees-locales.ts';
import { verifierSources } from './scripts/verifier-sources.ts';

// Pages générées à l'avance : l'accueil, les pages fixes et les 300 fiches commune
// (index swisstopo produit par pipeline/communes.py). Aucune donnée CAMAC n'est lue au build :
// les dossiers sont chargés en direct par le navigateur, et ouverts dans la fiche de leur commune (?d=).
function readJson<T>(path: string, fallback: T): T {
	return existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : fallback;
}
const communes = readJson<{ slug: string }[]>('static/communes.json', []);

export default defineConfig({
	// Toute la suite de tests à l'heure de Lausanne : une heure DGMR (heure locale codée comme de l'UTC) lue
	// par erreur en heure locale y décale de 1 ou 2 h, et le test échoue même sur une machine en UTC (la CI).
	test: { env: { TZ: 'Europe/Zurich' } },
	// MapLibre 6 charge son worker par une URL relative au module : le pré-bundling de Vite la casse.
	optimizeDeps: { exclude: ['maplibre-gl'] },
	plugins: [
		donneesLocales(),
		verifierSources({
			sources: '../sources.json',
			schema: '../schema/sources.schema.json',
			communes: 'static/communes.json'
		}),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Site entièrement statique ; 404.html sert de page d'erreur pour les adresses inconnues.
			adapter: adapter({ fallback: '404.html' }),
			paths: {
				// GitHub Pages sert le site sous /<dépôt> tant qu'il n'y a pas de domaine.
				base: (process.env.BASE_PATH ?? '') as '' | `/${string}`
			},
			prerender: {
				concurrency: 8,
				// Pas d'exploration des liens : seules les pages listées ci-dessous sont pré-générées.
				crawl: false,
				entries: ['*', ...communes.map((c) => `/commune/${c.slug}` as const)]
			}
		})
	]
});
