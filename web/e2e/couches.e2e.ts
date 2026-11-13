import type { Locator } from '@playwright/test';
import { arriver, expect, test } from './banc.js';

/*
 * Filtrer une couche : les puces de statut du volet Permis. La carte part sur Pully, où le faux canton a trois
 * dossiers en cours (`DOSSIERS` du banc) : deux à l'enquête, un dont la décision est attendue.
 */

const PULLY = '/?vue=46.50932,6.66161,14.00';

/** La puce d'un statut, dans la légende du volet Permis. */
const puce = (volet: Locator, statut: string) =>
	volet.getByRole('group', { name: /^Statuts affichés/ }).getByRole('button', { name: statut });

/** Filtre le volet Permis : « À l’enquête » masqué, il ne reste que le dossier dont la décision est attendue. */
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
	test('les puces de statut du volet Permis filtrent ses dossiers, et le filtre survit au rechargement', async ({
		page
	}) => {
		await arriver(page, PULLY);
		await page.getByRole('toolbar', { name: 'Couches' }).getByRole('button', { name: /Permis/ }).click();
		const volet = page.getByRole('region', { name: 'Permis' });

		await filtrer(volet);

		// Le filtre est dans l'adresse : un lien partagé le rétablit.
		await page.reload();

		await expect(puce(volet, 'À l’enquête')).toHaveAttribute('aria-pressed', 'false');
		await expect(volet.getByText('1 dossier en cours dans la zone affichée')).toBeVisible();
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('les puces de statut, dans la vue Couches, filtrent les dossiers, et le filtre survit au rechargement', async ({
		page
	}) => {
		await arriver(page, PULLY);
		await page.getByRole('button', { name: 'Couches', exact: true }).click();
		const volet = page.getByRole('region', { name: 'Permis' });

		await filtrer(volet);

		// Le filtre est dans l'adresse : un lien partagé le rétablit.
		await page.reload();

		await expect(page.getByRole('button', { name: 'Couches', exact: true })).toHaveAttribute('aria-pressed', 'true');
		await expect(puce(volet, 'À l’enquête')).toHaveAttribute('aria-pressed', 'false');
		await expect(volet.getByText('1 dossier en cours dans la zone affichée')).toBeVisible();
	});
});
