import type { Locator } from '@playwright/test';
import { arriver, expect, test } from './banc.js';

/*
 * Filtrer une rubrique : les puces de statut de Permis de construire. La carte part sur Pully, où le faux canton a trois
 * dossiers en cours (`DOSSIERS` du banc) : deux à l'enquête, un dont la décision est attendue.
 */

const PULLY = '/?vue=46.50932,6.66161,14.00';

/** La puce d'un statut, dans la rubrique Permis de construire. */
const puce = (volet: Locator, statut: string) =>
	volet.getByRole('group', { name: /^Statuts affichés/ }).getByRole('button', { name: statut });

/** Filtre Permis de construire : « À l’enquête » masqué, il ne reste que le dossier dont la décision est attendue. */
async function filtrer(volet: Locator) {
	await expect(volet.getByText('3 dossiers en cours dans la zone affichée')).toBeVisible();
	await expect(volet.getByText(/Pose de panneaux solaires/)).toBeVisible();

	const enquete = puce(volet, 'À l’enquête');
	await enquete.click();

	await expect(enquete).toHaveAttribute('aria-pressed', 'false');
	await expect(volet.getByText('1 dossier en cours dans la zone affichée')).toBeVisible();
	await expect(volet.getByText(/Démolition d.un garage/)).toBeVisible();
	await expect(volet.getByText(/Pose de panneaux solaires/)).toBeHidden();
	await expect(volet.getByText(/Agrandissement d.une villa/)).toBeHidden();
}

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('les puces de statut de Permis de construire filtrent ses dossiers, et le filtre survit au rechargement', async ({
		page
	}) => {
		await arriver(page, PULLY);
		await page.getByRole('link', { name: /^Permis de construire/ }).click();
		const volet = page.getByRole('region', { name: 'Permis de construire' });

		await filtrer(volet);

		// Le filtre est dans l'adresse : un lien partagé le rétablit.
		await page.reload();

		await expect(puce(volet, 'À l’enquête')).toHaveAttribute('aria-pressed', 'false');
		await expect(volet.getByText('1 dossier en cours dans la zone affichée')).toBeVisible();
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('les puces de statut, dans le panneau, filtrent les dossiers, et le filtre survit au rechargement', async ({
		page
	}) => {
		// L'adresse nomme une vue de la carte : le téléphone arrive sur la carte.
		await arriver(page, PULLY);
		await page.getByRole('button', { name: 'Sujets', exact: true }).click();
		await page.getByRole('link', { name: /^Permis de construire/ }).click();
		const volet = page.getByRole('region', { name: 'Permis de construire' });

		await filtrer(volet);

		// Le filtre est dans l'adresse : un lien partagé le rétablit.
		await page.reload();

		await expect(page.getByRole('button', { name: 'Sujets', exact: true })).toHaveAttribute('aria-pressed', 'true');
		await expect(puce(volet, 'À l’enquête')).toHaveAttribute('aria-pressed', 'false');
		await expect(volet.getByText('1 dossier en cours dans la zone affichée')).toBeVisible();
	});
});
