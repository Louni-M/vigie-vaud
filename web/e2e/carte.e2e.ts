import type { Page } from '@playwright/test';
import { arriver, expect, test } from './banc.js';

/*
 * Ouvrir une fiche commune par un clic sur la carte : le marqueur de son hôtel de ville. La carte part centrée sur
 * celui d'Aclens (communes.json), au zoom 14 : le marqueur est au centre de la carte.
 */

const VUE = '46.56801,6.50968,14.00';

/**
 * Clique au centre de la carte jusqu'à ce que `ouverte` soit visible : rien ne dit, dans la page, que la carte a fini
 * de dessiner ses marqueurs.
 */
async function cliquerAuCentre(page: Page, ouverte: ReturnType<Page['getByRole']>) {
	const carte = page.locator('#carte');
	await expect(async () => {
		const b = (await carte.boundingBox())!;
		await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
		await expect(ouverte).toBeVisible({ timeout: 1000 });
	}).toPass();
}

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('un clic sur l’hôtel de ville ouvre la fiche de la commune ; le retour la referme', async ({ page }) => {
		await arriver(page, `/?vue=${VUE}`);

		await cliquerAuCentre(page, page.getByRole('heading', { name: 'Aclens', level: 2 }));
		await expect(page).toHaveURL(/\/commune\/aclens(\?|$)/);
		await expect(page.getByRole('button', { name: 'Fermer la fiche d’Aclens' })).toBeVisible();
		await expect(page.getByRole('tab', { name: /Permis/ })).toBeVisible();

		await page.goBack();
		await expect(page.getByRole('heading', { name: 'Aclens', level: 2 })).toBeHidden();
		await expect(page).toHaveURL(`/?vue=${VUE}`);
		// Doute laissé par #204 : la carte rétablit la vue de l'adresse, et finit ce déplacement après le retour. La vue
		// reste dans l'adresse, inchangée : on le vérifie une fois ce déplacement fini, qu'aucun signe de la page ne marque.
		await page.waitForTimeout(1000);
		await expect(page).toHaveURL(`/?vue=${VUE}`);
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('un toucher sur l’hôtel de ville ouvre l’aperçu de la commune, puis sa fiche ; le retour les referme', async ({
		page
	}) => {
		await arriver(page, `/?vue=${VUE}`);

		const apercu = page.getByRole('button', { name: /Aclens · Voir la fiche/ });
		await cliquerAuCentre(page, apercu);
		await expect(page).toHaveURL(/\/commune\/aclens(\?|$)/);

		await apercu.click();
		const titre = page.getByRole('heading', { name: 'Aclens', level: 2 });
		await expect(titre).toBeVisible();
		await expect(titre).toBeFocused();
		await expect(page.getByRole('button', { name: 'Fiche', exact: true })).toHaveAttribute('aria-pressed', 'true');

		// Retour à l'aperçu, puis à la carte seule.
		await page.goBack();
		await expect(titre).toBeHidden();
		await expect(apercu).toBeVisible();
		await page.goBack();
		await expect(apercu).toBeHidden();
		await expect(page).toHaveURL(`/?vue=${VUE}`);
		await page.waitForTimeout(1000);
		await expect(page).toHaveURL(`/?vue=${VUE}`);
	});
});
