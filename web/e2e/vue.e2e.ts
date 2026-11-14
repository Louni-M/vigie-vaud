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
