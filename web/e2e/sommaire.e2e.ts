import type { Page } from '@playwright/test';
import { arriver, centreDeLaCarte, expect, test } from './banc.js';

/*
 * Le sommaire, écran d'arrivée : une ligne par sujet, avec son nombre, qui ouvre sa liste ; la carte ne dessine que
 * le sujet ouvert. Le faux canton a trois dossiers en cours à Pully (`DOSSIERS` du banc), la DGMR factice aucune
 * restriction, et l'index factice trois conseils : le Grand Conseil, Lausanne et Yverdon-les-Bains.
 */

/** Pully, au zoom 17, centrée sur le dossier 260102 : l'hôtel de ville est assez loin pour ne pas prendre le clic. */
const SUR_LE_DOSSIER = '/?vue=46.51100,6.66400,17.00';

const sommaire = (page: Page) => page.getByRole('region', { name: 'Ce que montre Vigie Vaud' });
const ligne = (page: Page, nom: string) => sommaire(page).getByRole('link', { name: new RegExp(`^${nom}`) });

/** Clique au centre de ce qu'on voit de la carte. */
async function cliquerAuCentre(page: Page) {
	await page.mouse.click(...(await centreDeLaCarte(page)));
}

// Sur téléphone, la vue Carte : une légende cachée sous une autre vue ne compterait pas (`getByRole` ignore ce qui est caché).
for (const adresse of ['/?affichage=carte', '/?volet=routes&affichage=carte', '/commune/pully?affichage=carte'])
	test(`la carte n’a pas de légende, sur ${adresse}`, async ({ page }) => {
		await arriver(page, adresse);
		await expect(page.locator('#carte .maplibregl-canvas')).toBeVisible();
		await expect(page.getByRole('region', { name: 'Légende de la carte' })).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Légende', exact: true })).toHaveCount(0);
	});

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('l’arrivée montre le sommaire, ses quatre sujets et leurs nombres, et aucune liste', async ({ page }) => {
		await arriver(page, '/?vue=46.50932,6.66161,14.00');
		const lignes = sommaire(page).getByRole('link');
		await expect(lignes).toHaveCount(4);
		await expect(lignes.nth(0)).toContainText('Permis de construire');
		await expect(lignes.nth(1)).toContainText('Routes');
		await expect(lignes.nth(2)).toContainText('Conseils communaux');
		await expect(lignes.nth(3)).toContainText('Grand Conseil');
		await expect(ligne(page, 'Permis de construire')).toContainText('3 dossiers en cours dans la zone affichée');
		await expect(ligne(page, 'Routes')).toContainText('Aucune restriction de circulation dans la zone affichée');
		await expect(ligne(page, 'Grand Conseil')).toContainText('pour tout le canton');
		await expect(page.getByText(/Pose de panneaux solaires/)).toBeHidden();
	});

	test('la carte ne dessine que la rubrique ouverte', async ({ page }) => {
		await arriver(page, SUR_LE_DOSSIER);
		// Au sommaire, les permis ne sont pas dessinés : un clic sur le dossier n'ouvre rien.
		await expect(ligne(page, 'Permis de construire')).toContainText('dossier');
		await page.waitForTimeout(500);
		await cliquerAuCentre(page);
		await page.waitForTimeout(500);
		await expect(page).not.toHaveURL(/d=/);

		// La rubrique ouverte, ses dossiers le sont.
		await ligne(page, 'Permis de construire').click();
		await expect(page).toHaveURL(/volet=permis/);
		await expect(async () => {
			await cliquerAuCentre(page);
			await expect(page).toHaveURL(/d=260102/, { timeout: 1000 });
		}).toPass();

		// Revenu au sommaire, puis dans Routes : les permis ne le sont plus.
		await page.goto(SUR_LE_DOSSIER);
		await ligne(page, 'Routes').click();
		await expect(page.getByRole('heading', { name: 'Routes', level: 2 })).toBeVisible();
		await page.waitForTimeout(800);
		await cliquerAuCentre(page);
		await page.waitForTimeout(500);
		await expect(page).not.toHaveURL(/d=/);
	});

	test('la ligne Grand Conseil ouvre sa fiche, qui liste les objets sans commune, et reste marquée', async ({ page }) => {
		await arriver(page, '/');
		await ligne(page, 'Grand Conseil').click();
		await expect(page).toHaveURL(/\/grand-conseil(\?|$)/);
		await expect(page.getByRole('heading', { name: 'Grand Conseil', level: 2 })).toBeVisible();
		await expect(page.getByText('Quelle politique pour les transports publics régionaux ?').first()).toBeVisible();
		await expect(ligne(page, 'Grand Conseil')).toHaveAttribute('aria-current', 'page');
	});

	test('les nombres de la fiche d’une commune comptent la zone affichée, comme les listes qu’ils ouvrent', async ({
		page
	}) => {
		await arriver(page, '/commune/pully');
		await expect(ligne(page, 'Permis de construire')).toContainText('3 dossiers en cours dans la zone affichée');
		await expect(ligne(page, 'Grand Conseil')).toContainText('pour tout le canton');
		await ligne(page, 'Permis de construire').click();
		const rubrique = page.getByRole('region', { name: 'Permis de construire' });
		await expect(rubrique.getByText('3 dossiers en cours dans la zone affichée')).toBeVisible();
	});

	test('une source en échec rend sa ligne indisponible, et sa rubrique propose de réessayer', async ({ page }) => {
		await page.route(/MapServer\/537\/query/, (r) => r.fulfill({ status: 500, body: '' }));
		await arriver(page, '/');
		await expect(ligne(page, 'Permis de construire')).toContainText('indisponible', { timeout: 20_000 });
		await expect(ligne(page, 'Conseils communaux')).toContainText('communes suivies');
		await ligne(page, 'Permis de construire').click();
		await expect(page.getByRole('button', { name: 'Réessayer' })).toBeVisible();
	});

	test('une ligne est un lien : Ctrl-clic ouvre la rubrique dans un nouvel onglet', async ({ page, context }) => {
		await arriver(page, '/');
		await expect(ligne(page, 'Routes')).toHaveAttribute('href', '/?volet=routes');
		const [nouvelle] = await Promise.all([
			context.waitForEvent('page'),
			ligne(page, 'Routes').click({ modifiers: ['ControlOrMeta'] })
		]);
		await expect(nouvelle).toHaveURL(/\/\?volet=routes$/);
		await expect(page).toHaveURL(/\/$/);
	});

	test('au clavier, la rubrique ouverte reçoit le focus, et le retour le rend à sa ligne', async ({ page }) => {
		await arriver(page, '/');
		await ligne(page, 'Routes').focus();
		await page.keyboard.press('Enter');
		const titre = page.getByRole('heading', { name: 'Routes', level: 2 });
		await expect(titre).toBeFocused();

		await page.getByRole('link', { name: 'Tous les sujets' }).click();
		await expect(ligne(page, 'Routes')).toBeFocused();

		// Échap, depuis la rubrique, ramène aussi au sommaire.
		await page.keyboard.press('Enter');
		await expect(titre).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(ligne(page, 'Routes')).toBeFocused();
	});

	test('Routes se trie par début, le plus récent d’abord, et l’adresse le garde', async ({ page }) => {
		await arriver(page, '/?volet=routes');
		await page.getByRole('combobox', { name: 'Ordre de la liste' }).selectOption('recent');
		await expect(page).toHaveURL(/ordre=recent/);
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('à 375 × 812, le sommaire entier et la recherche se voient sans défiler', async ({ page }) => {
		await page.setViewportSize({ width: 375, height: 812 });
		await arriver(page, '/');
		await expect(page.getByRole('button', { name: 'Sujets', exact: true })).toHaveAttribute('aria-pressed', 'true');
		const barre = (await page.getByRole('navigation', { name: 'Affichage' }).boundingBox())!;
		for (const cible of [page.getByRole('searchbox'), ...['Permis de construire', 'Routes', 'Conseils communaux', 'Grand Conseil'].map((n) => ligne(page, n))]) {
			const b = (await cible.boundingBox())!;
			expect(b.y + b.height, 'au-dessus de la barre du bas').toBeLessThanOrEqual(barre.y);
		}
		await expect(page.getByText(/Pose de panneaux solaires/)).toBeHidden();
	});

	test('une rubrique ouverte passe à la carte et en revient, seule dans le panneau', async ({ page }) => {
		await arriver(page, '/');
		await ligne(page, 'Routes').click();
		await expect(page.getByRole('heading', { name: 'Routes', level: 2 })).toBeVisible();
		await expect(sommaire(page)).toBeHidden();
		await expect(page.getByRole('heading', { level: 2, name: 'Permis de construire' })).toBeHidden();

		await page.getByRole('button', { name: 'Carte', exact: true }).click();
		await expect(page.getByRole('heading', { name: 'Routes', level: 2 })).toBeHidden();
		await page.getByRole('button', { name: 'Sujets', exact: true }).click();
		await expect(page.getByRole('heading', { name: 'Routes', level: 2 })).toBeVisible();
		await page.getByRole('link', { name: 'Tous les sujets' }).click();
		await expect(sommaire(page)).toBeVisible();
	});
});
