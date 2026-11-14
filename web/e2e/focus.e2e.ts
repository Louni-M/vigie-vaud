import { arriver, expect, test } from './banc.js';

/*
 * Retrouver le focus après la fermeture d'un volet. Sur bureau, le volet d'une couche se ferme par sa croix ou par
 * Échap, et le focus revient à l'icône du rail qui l'avait ouvert.
 *
 * Le téléphone n'a pas de volet qui se ferme : la vue Couches les empile, sans croix. Ce qui s'y ouvre et s'y ferme en
 * gardant le focus, c'est l'élément ouvert dans une fiche (un dossier) : le fermer par le fil d'Ariane rend le focus à
 * l'onglet de sa couche.
 */

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('fermer le volet par Échap ou par sa croix rend le focus à l’icône du rail qui l’avait ouvert', async ({ page }) => {
		await arriver(page, '/');
		const icone = page.getByRole('toolbar', { name: 'Couches' }).getByRole('button', { name: /Permis/ });
		const volet = page.getByRole('region', { name: 'Permis' });

		// Échap, le focus dans le volet.
		await icone.click();
		await expect(icone).toHaveAttribute('aria-expanded', 'true');
		await volet.getByRole('switch').focus();
		await expect(volet.getByRole('switch')).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(volet).toBeHidden();
		await expect(icone).toBeFocused();
		await expect(icone).toHaveAttribute('aria-expanded', 'false');

		// La croix.
		await icone.click();
		await volet.getByRole('button', { name: 'Fermer le volet Permis' }).click();
		await expect(volet).toBeHidden();
		await expect(icone).toBeFocused();
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('fermer le dossier ouvert dans la fiche rend le focus à l’onglet Permis', async ({ page }) => {
		await arriver(page, '/commune/pully?d=260101');
		await expect(page.getByRole('heading', { name: 'Pully', level: 2 })).toBeVisible();
		const ariane = page.getByRole('navigation', { name: 'Fil d’Ariane' });
		await expect(ariane).toContainText('260101');
		await expect(page.getByRole('article').getByText(/Agrandissement d.une villa/)).toBeVisible();

		await ariane.getByRole('link').click();

		await expect(ariane).toBeHidden();
		await expect(page.getByRole('tab', { name: /Permis/ })).toBeFocused();
		await expect(page.getByRole('tab', { name: /Permis/ })).toHaveAttribute('aria-selected', 'true');
	});
});
