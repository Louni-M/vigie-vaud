import { defineConfig, devices } from '@playwright/test';

/*
 * Suite Playwright : le site construit (`pnpm build`), servi par `vite preview`, avec des services factices
 * (`e2e/banc.ts`). Aucune requête ne quitte la machine. Chaque scénario tourne sur bureau et en vue téléphone.
 *
 * Les fichiers s'appellent `*.e2e.ts` : Vitest ne les ramasse pas (il cherche `*.test.ts` et `*.spec.ts`).
 */

const PORT = 4319;

export default defineConfig({
	testDir: 'e2e',
	testMatch: '*.e2e.ts',
	fullyParallel: true,
	// Chaque page dessine sa carte en logiciel (SwiftShader, ci-dessous) : au-delà de trois à la fois, elles se
	// disputent le processeur et les délais d'attente sautent. Le runner de la CI a quatre cœurs.
	workers: process.env.CI ? 2 : 3,
	timeout: 60_000,
	expect: { timeout: 10_000 },
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 1 : 0,
	reporter: process.env.CI ? [['list'], ['github']] : 'list',
	use: {
		baseURL: `http://localhost:${PORT}`,
		locale: 'fr-CH',
		timezoneId: 'Europe/Zurich',
		// Les vols de la carte deviennent des sauts, et les volets apparaissent en fondu court : rien à attendre.
		reducedMotion: 'reduce',
		trace: 'retain-on-failure',
		launchOptions: {
			args: [
				// Seconde barrière, sous celle de `e2e/banc.ts` : aucun nom d'hôte autre que localhost ne se résout, ce qui
				// couvre aussi ce que l'interception ne voit pas (preconnect, dns-prefetch).
				'--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost',
				// MapLibre dessine en WebGL : Chromium le rend par SwiftShader, en logiciel, partout. La carte graphique d'un
				// poste ne change donc rien au rendu, qui est celui de la CI, sans carte graphique.
				'--use-angle=swiftshader',
				'--enable-unsafe-swiftshader'
			]
		}
	},
	// Un scénario étiqueté `@bureau` ou `@telephone` ne tourne que dans son projet ; les autres, dans les deux.
	projects: [
		{
			name: 'bureau',
			grepInvert: /@telephone/,
			use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } }
		},
		// Moins de 760 px de large : la mise en page du téléphone (`TELEPHONE`, lib/socle/telephone.ts), au doigt.
		{ name: 'telephone', grepInvert: /@bureau/, use: { ...devices['Pixel 7'] } }
	],
	webServer: {
		command: `pnpm exec vite preview --port ${PORT} --strictPort`,
		url: `http://localhost:${PORT}`,
		// Jamais un serveur déjà lancé (`pnpm dev`) : la suite teste le site construit.
		reuseExistingServer: false
	}
});
