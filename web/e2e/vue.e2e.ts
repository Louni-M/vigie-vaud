import type { Page } from '@playwright/test';
import { arriver, expect, test } from './banc.js';

/*
 * La vue de la carte dans l'adresse (`vue=lat,lon,zoom`) : seule celle que la personne a choisie y entre, jamais le
 * cadrage par défaut d'une commune qu'on ouvre, et le précédent la rétablit sans que l'adresse passe par une autre.
 *
 * La carte finit ses déplacements après les signes de la page : on lit donc toutes les adresses écrites dans
 * l'historique (`pushState`, `replaceState`), et pas seulement la dernière. Chaque scénario tourne avec et sans
 * animation : la suite demande moins d'animations (playwright.config.ts), et la carte saute alors au lieu de voler.
 */

const VUE = '46.56801,6.50968,14.00';

/** Les écritures de l'historique, et les retours du navigateur, depuis l'arrivée sur la page. */
async function suivreHistorique(page: Page) {
	await page.addInitScript(() => {
		const journal: string[] = [];
		(window as unknown as { __historique: string[] }).__historique = journal;
		for (const nom of ['pushState', 'replaceState'] as const) {
			const ecrire = history[nom].bind(history);
			history[nom] = (etat: unknown, titre: string, url?: string | URL | null) => {
				if (url != null) {
					const u = new URL(url, location.href);
					journal.push(`${nom} ${u.pathname}${u.search}`);
				}
				return ecrire(etat, titre, url);
			};
		}
		addEventListener('popstate', () => journal.push(`popstate ${location.pathname}${location.search}`));
	});
}

/** Les adresses écrites depuis le dernier retour du navigateur. */
async function ecritesDepuisRetour(page: Page) {
	const journal = await page.evaluate(() => (window as unknown as { __historique: string[] }).__historique);
	return journal.slice(journal.findLastIndex((l) => l.startsWith('popstate')) + 1);
}

/** Choisit une commune dans la Recherche : le champ de la carte sur bureau, la Recherche plein écran sur téléphone. */
async function chercherCommune(page: Page, nom: string) {
	await page.getByRole('searchbox').click();
	await page.getByRole('searchbox').fill(nom);
	await page
		.getByRole('list', { name: 'Résultats de recherche' })
		.getByRole('button', { name: new RegExp(`^Commune\\s*${nom}$`) })
		.click();
	// Sur bureau, la fiche ; sur téléphone, son aperçu en bas de la carte.
	await expect(
		page.getByRole('heading', { name: nom, level: 2 }).or(page.getByRole('button', { name: `${nom} · Voir la fiche` }))
	).toBeVisible();
}

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('un clic sur l’hôtel de ville juste après un tour de molette n’écrit pas le cadrage de la commune', async ({
		page
	}) => {
		// La carte part centrée sur l'hôtel de ville d'Aclens : son marqueur est au centre (voir carte.e2e.ts).
		await arriver(page, `/?vue=${VUE}`);
		const carte = page.locator('#carte');
		const titre = page.getByRole('heading', { name: 'Aclens', level: 2 });
		// La carte compte comme geste de la personne un déplacement qui commence moins d'une demi-seconde après un tour
		// de molette (MapLibre ne joint pas toujours l'évènement à son zoom). Le tour, ici, est de ceux que la carte ne
		// suit pas, comme la fin de l'inertie d'un pavé tactile : il arrive sur le conteneur de la carte, que la carte
		// écoute, et pas sur son canevas, que MapLibre écoute. Il tombe pendant l'ouverture de la fiche, quand elle
		// entre dans l'historique, juste avant que la carte cadre la commune : depuis le scénario, il arriverait trop
		// tard, la page étant lente à dessiner sans carte graphique.
		await page.evaluate(() => {
			const pousser = history.pushState.bind(history);
			history.pushState = (...args: Parameters<History['pushState']>) => {
				const conteneur = document.querySelector('#carte .maplibregl-canvas-container')?.parentElement;
				conteneur?.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true }));
				return pousser(...args);
			};
		});
		// On recommence tant que les marqueurs ne sont pas dessinés.
		await expect(async () => {
			const b = (await carte.boundingBox())!;
			await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
			await expect(titre).toBeVisible({ timeout: 1000 });
		}).toPass();
		await page.waitForTimeout(1500);
		await expect(page).toHaveURL('/commune/aclens');
		// La vue que la carte a prise pour celle de la personne n'entre dans l'adresse qu'à sa prochaine écriture : un
		// autre onglet de la fiche.
		await page.getByRole('tab').nth(1).click();
		await expect(page).toHaveURL(/\/commune\/aclens\?onglet=/);
		await page.waitForTimeout(500);
		await expect(page).not.toHaveURL(/vue=/);
	});
});

for (const reducedMotion of ['reduce', 'no-preference'] as const)
	test.describe(reducedMotion === 'reduce' ? 'sans animation' : 'avec animation', () => {
		test.use({ reducedMotion });

		test('ouvrir une commune n’écrit pas son cadrage par défaut dans l’adresse', async ({ page }) => {
			await arriver(page, '/');
			await chercherCommune(page, 'Aclens');
			// Sur téléphone, l'aperçu s'affiche sur la vue Carte, qui n'est pas celle qui va avec la fiche.
			const propre = /\/commune\/aclens(\?affichage=carte)?$/;
			await expect(page).toHaveURL(propre);
			// La carte a fini de cadrer la commune, et la colonne de la fiche de s'ouvrir (bureau) : la carte a changé de
			// taille, sans que la vue devienne un choix de la personne.
			await page.waitForTimeout(1500);
			await expect(page).toHaveURL(propre);
		});

		test('le précédent rétablit la vue de l’adresse, sans en écrire une autre entre-temps', async ({ page }) => {
			await suivreHistorique(page);
			await arriver(page, `/?vue=${VUE}`);
			await chercherCommune(page, 'Pully');
			await expect(page).toHaveURL(/^[^?]*\/commune\/pully(\?|$)/);

			await page.goBack();
			await expect(page).toHaveURL(`/?vue=${VUE}`);
			// La carte revient à la vue de l'adresse : d'un saut, ou en un vol d'une demi-seconde.
			await page.waitForTimeout(1500);
			await expect(page).toHaveURL(`/?vue=${VUE}`);
			const autres = (await ecritesDepuisRetour(page)).filter((l) => !l.endsWith(` /?vue=${VUE}`));
			expect(autres, 'adresses écrites après le précédent').toEqual([]);
		});
	});
