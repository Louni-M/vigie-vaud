// Pendant J0, le cron tourne en local contre un clone du dépôt de données, que rien ne publie encore sur Pages.
// `DONNEES_LOCALES=<chemin du clone> pnpm dev` sert ce clone à `/donnees-locales/` et y fait pointer `DONNEES`
// (`src/lib/config.ts`), à la même origine que le site. Sans cette variable, et à la construction, rien ne change.
import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import type { Plugin } from 'vite';

const PREFIXE = '/donnees-locales';

export function donneesLocales(dossier = process.env.DONNEES_LOCALES): Plugin {
	return {
		name: 'donnees-locales',
		apply: 'serve',
		config: () =>
			dossier ? { define: { 'import.meta.env.VITE_DONNEES': JSON.stringify(PREFIXE) } } : undefined,
		configureServer(server) {
			if (!dossier) return;
			const racine = resolve(dossier);
			server.middlewares.use(PREFIXE, async (req, res, suite) => {
				const chemin = resolve(racine, `.${decodeURIComponent(new URL(req.url ?? '/', 'http://x').pathname)}`);
				if (!chemin.startsWith(racine + sep)) return suite();
				try {
					const contenu = await readFile(chemin);
					res.setHeader('Content-Type', chemin.endsWith('.json') ? 'application/json' : 'application/octet-stream');
					res.setHeader('Cache-Control', 'no-cache');
					res.end(contenu);
				} catch {
					res.statusCode = 404;
					res.end();
				}
			});
		}
	};
}
