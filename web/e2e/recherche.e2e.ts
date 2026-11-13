import type { Page } from '@playwright/test';
import { ADRESSE, arriver, expect, test } from './banc.js';

/*
 * Parcourir la Recherche au clavier : « Pully » donne la commune (liste locale), puis une adresse (faux service de
 * swisstopo). Les flèches vont du champ aux résultats et d'un résultat à l'autre, Entrée choisit.
 *
 * On ne vérifie que ce que voit la personne : la Recherche plein écran du téléphone passe par l'historique, et la façon
 * dont elle le fait est appelée à changer (#205).
 */

/** Tape « Pully » dans le champ qui a le focus, et parcourt les résultats au clavier, jusqu'à la commune. */
async function parcourir(page: Page) {
	const champ = page.getByRole('searchbox');
	await page.keyboard.type('Pully');
	const resultats = page.getByRole('list', { name: 'Résultats de recherche' });
	const commune = resultats.getByRole('button', { name: /^Commune\s*Pully$/ });
	const adresse = resultats.getByRole('button', { name: new RegExp(`^Adresse\\s*${ADRESSE}$`) });
	// L'adresse n'arrive qu'après le délai de saisie et la réponse du service.
	await expect(adresse).toBeVisible();
	await expect(resultats.getByRole('button')).toHaveCount(2);

	await page.keyboard.press('ArrowDown');
	await expect(commune).toBeFocused();
	await page.keyboard.press('ArrowDown');
	await expect(adresse).toBeFocused();
	// Au bout de la liste, la flèche bas reste sur le dernier résultat.
	await page.keyboard.press('ArrowDown');
	await expect(adresse).toBeFocused();
	await page.keyboard.press('ArrowUp');
	await expect(commune).toBeFocused();
	// Du premier résultat, la flèche haut remonte au champ.
	await page.keyboard.press('ArrowUp');
	await expect(champ).toBeFocused();
	await page.keyboard.press('ArrowDown');
	await expect(commune).toBeFocused();
}

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('les flèches parcourent les résultats, Entrée ouvre la fiche de la commune et rend le focus au champ', async ({
		page
	}) => {
		await arriver(page, '/');
		const champ = page.getByRole('searchbox');
		await champ.focus();

		await parcourir(page);
		await page.keyboard.press('Enter');

		await expect(page.getByRole('heading', { name: 'Pully', level: 2 })).toBeVisible();
		await expect(page.getByRole('list', { name: 'Résultats de recherche' })).toBeHidden();
		await expect(champ).toHaveValue('Pully');
		await expect(champ).toBeFocused();
	});

	test('Échap ferme la liste ; le champ garde son texte et le focus', async ({ page }) => {
		await arriver(page, '/');
		const champ = page.getByRole('searchbox');
		await champ.focus();
		await page.keyboard.type('Pully');
		const resultats = page.getByRole('list', { name: 'Résultats de recherche' });
		await expect(resultats.getByRole('button')).toHaveCount(2);

		await page.keyboard.press('Escape');
		await expect(resultats).toBeHidden();
		await expect(champ).toHaveValue('Pully');
		await expect(champ).toBeFocused();
	});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('la Recherche plein écran se parcourt au clavier ; Entrée la referme sur l’aperçu de la commune', async ({
		page
	}) => {
		await arriver(page, '/');
		await page.getByRole('searchbox').click();
		await expect(page.getByRole('button', { name: 'Annuler' })).toBeVisible();
		await expect(page.getByRole('searchbox')).toBeFocused();

		await parcourir(page);
		await page.keyboard.press('Enter');

		await expect(page.getByRole('button', { name: 'Annuler' })).toBeHidden();
		await expect(page.getByRole('button', { name: /Pully · Voir la fiche/ })).toBeVisible();
		await expect(page.getByRole('searchbox')).toHaveValue('Pully');
	});

	test('le retour du navigateur referme la Recherche plein écran sans rien ouvrir', async ({ page }) => {
		await arriver(page, '/');
		await page.getByRole('searchbox').click();
		await page.keyboard.type('Pully');
		await expect(page.getByRole('list', { name: 'Résultats de recherche' }).getByRole('button')).toHaveCount(2);

		await page.goBack();

		await expect(page.getByRole('button', { name: 'Annuler' })).toBeHidden();
		await expect(page.getByRole('button', { name: /Voir la fiche/ })).toBeHidden();
		await expect(page.getByRole('button', { name: 'Carte', exact: true })).toHaveAttribute('aria-pressed', 'true');
	});
});
