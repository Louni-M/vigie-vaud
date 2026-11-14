import type { Environment } from 'vitest/runtime';

/**
 * Environnement des tests `*.svelte.test.ts` : Node, mais les modules compilés pour le navigateur. Les runes y
 * ont leur comportement du client (`$effect` s'exécute), sans DOM ni SvelteKit.
 */
export default {
	name: 'client',
	viteEnvironment: 'client',
	setup: () => ({ teardown: () => {} })
} satisfies Environment;
