import type { Page } from '@playwright/test';
import { arriver, expect, test } from './banc.js';

/*
 * Retrouver le focus après la fermeture d'un volet. Sur bureau, le volet d'une couche se ferme par sa croix ou par
 * Échap, et le focus revient à l'icône du rail qui l'avait ouvert.
 *
 * Le téléphone n'a pas de volet qui se ferme : la vue Couches les empile, sans croix. Ce qui s'y ouvre et s'y ferme en
 * gardant le focus, c'est l'élément ouvert dans une fiche (un dossier) : le fermer par le fil d'Ariane rend le focus à
 * l'onglet de sa couche.
 *
 * Fermer une fiche, par sa croix ou celle de son aperçu (téléphone), ou la Recherche plein écran du téléphone, au
 * clavier, rend le focus au champ de recherche qui les avait ouvertes.
 */

/** Ouvre la fiche de Pully au clavier, depuis le champ de recherche : la Recherche plein écran sur téléphone. */
async function ouvrirPullyAuClavier(page: Page) {
	const champ = page.getByRole('searchbox');
	await champ.focus();
	await page.keyboard.type('Pully');
	const commune = page
		.getByRole('list', { name: 'Résultats de recherche' })
		.getByRole('button', { name: /^Commune\s*Pully$/ });
	await expect(commune).toBeVisible();
	await page.keyboard.press('ArrowDown');
	await expect(commune).toBeFocused();
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/\/commune\/pully(\?|$)/);
	await expect(champ).toBeFocused();
}

/** Active au clavier un bouton qui n'est pas forcément le suivant dans l'ordre de tabulation. */
async function activerAuClavier(page: Page, nom: string | RegExp) {
	const bouton = page.getByRole('button', { name: nom });
	await bouton.focus();
	await page.keyboard.press('Enter');
}

test('fermer la fiche par sa croix rend le focus au champ de recherche qui l’avait ouverte', async ({ page }) => {
	await arriver(page, '/');
	await ouvrirPullyAuClavier(page);
	const titre = page.getByRole('heading', { name: 'Pully', level: 2 });
	// Sur téléphone, la fiche s'ouvre d'abord en aperçu, sur la carte.
	const apercu = page.getByRole('button', { name: /Pully · Voir la fiche/ });
	if (await apercu.isVisible()) await activerAuClavier(page, /Pully · Voir la fiche/);
	await expect(titre).toBeVisible();

	await activerAuClavier(page, 'Fermer la fiche de Pully');

	await expect(titre).toBeHidden();
	await expect(page).toHaveURL(/\/(\?|$)/);
	await expect(page.getByRole('searchbox')).toBeFocused();
	await expect(page.getByRole('button', { name: 'Annuler' })).toBeHidden();
});

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
	test('fermer l’aperçu par sa croix rend le focus au champ de recherche qui l’avait ouvert', async ({ page }) => {
		await arriver(page, '/');
		await ouvrirPullyAuClavier(page);
		const apercu = page.getByRole('button', { name: /Pully · Voir la fiche/ });
		await expect(apercu).toBeVisible();

		await activerAuClavier(page, 'Fermer l’aperçu de Pully');

		await expect(apercu).toBeHidden();
		await expect(page.getByRole('searchbox')).toBeFocused();
		await expect(page.getByRole('button', { name: 'Annuler' })).toBeHidden();
	});

	test('fermer la Recherche plein écran par Échap ou par « Annuler » rend le focus au champ', async ({ page }) => {
		await arriver(page, '/');
		const champ = page.getByRole('searchbox');
		const annuler = page.getByRole('button', { name: 'Annuler' });

		// Échap.
		await champ.focus();
		await expect(annuler).toBeVisible();
		await page.keyboard.type('Pully');
		await page.keyboard.press('Escape');
		await expect(annuler).toBeHidden();
		await expect(champ).toBeFocused();
		await expect(champ).toHaveValue('');

		// « Annuler », au clavier : le champ a le focus, sans rouvrir la Recherche.
		await champ.blur();
		await champ.focus();
		await expect(annuler).toBeVisible();
		await activerAuClavier(page, 'Annuler');
		await expect(annuler).toBeHidden();
		await expect(champ).toBeFocused();
		await page.waitForTimeout(300);
		await expect(annuler).toBeHidden();
	});

	test('ouverte au doigt, la Recherche se referme sans focus sur le champ, pour fermer le clavier de l’écran', async ({
		page
	}) => {
		await arriver(page, '/');
		const champ = page.getByRole('searchbox');
		const annuler = page.getByRole('button', { name: 'Annuler' });

		// « Annuler », touché.
		await champ.tap();
		await expect(annuler).toBeVisible();
		await annuler.tap();
		await expect(annuler).toBeHidden();
		await expect(champ).not.toBeFocused();

		// « Rechercher » sur le clavier de l'écran : ses touches arrivent dans le champ, Entrée comprise.
		await champ.tap();
		await expect(annuler).toBeVisible();
		await page.keyboard.type('Pully');
		await expect(page.getByRole('list', { name: 'Résultats de recherche' }).getByRole('button')).toHaveCount(2);
		await page.keyboard.press('Enter');
		await expect(page.getByRole('button', { name: /Pully · Voir la fiche/ })).toBeVisible();
		await expect(annuler).toBeHidden();
		await expect(champ).not.toBeFocused();
	});

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
