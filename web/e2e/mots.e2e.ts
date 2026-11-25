import { arriver, expect, test } from './banc.js';

/*
 * Les mots montrés au visiteur : un sujet porte le même nom partout, et aucun des termes qu'un visiteur ne comprenait
 * pas (relevés le 23 novembre 2026) ne reste à l'écran sur les pages de la carte.
 */

/** Les termes relevés comme non compris, tels qu'ils s'affichaient. */
const NON_COMPRIS = [
	/Fil cantonal/,
	/\bAffichée\b/,
	/\bpermanente\b/,
	/Sans commune/,
	/\bCouverture\b/,
	/Non couvert/,
	/i-web/,
	/Quicksite/,
	/importés? il y a/,
	/pastille cerclée/,
	/Objets récents/,
	/\bpréavis\b/
];

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('le titre de l’accueil dit tout ce que contient le site', async ({ page }) => {
		await arriver(page, '/');
		await expect(page).toHaveTitle(
			'Vigie Vaud – permis, routes, conseils communaux et Grand Conseil du canton de Vaud'
		);
	});

	test('Routes porte le même nom au sommaire, dans sa liste et dans la fiche d’une commune', async ({
		page
	}) => {
		await arriver(page, '/');
		const sommaire = page.getByRole('region', { name: 'Ce que montre Vigie Vaud' });
		await expect(sommaire.getByRole('link', { name: /^Routes/ })).toBeVisible();
		await sommaire.getByRole('link', { name: /^Routes/ }).click();
		await expect(page.getByRole('heading', { name: 'Routes', level: 2 })).toBeVisible();

		await page.goto('/commune/pully?volet=routes');
		await expect(page.getByRole('tab', { name: /^Routes/ })).toBeVisible();
		await expect(page.getByRole('tab', { name: /^Permis de construire/ })).toBeVisible();
	});

	test('les sources des conseils ne nomment pas les plateformes des sites', async ({ page }) => {
		await arriver(page, '/?volet=conseils');
		const rubrique = page.getByRole('region', { name: 'Conseils communaux' });
		await expect(rubrique.getByText(/communes? suivies?/).first()).toBeVisible();
		await expect(rubrique).not.toContainText('i-web');
		await expect(rubrique).not.toContainText('Quicksite');
	});

	for (const adresse of ['/', '/?volet=permis', '/?volet=routes', '/?volet=conseils', '/commune/pully', '/grand-conseil'])
		test(`aucun terme relevé comme non compris sur ${adresse}`, async ({ page }) => {
			await arriver(page, adresse);
			await expect(page.locator('#carte .maplibregl-canvas')).toBeVisible();
			// Les nombres et les listes chargés, le texte de la page est complet.
			await page.waitForTimeout(1000);
			const texte = await page.locator('body').innerText();
			for (const terme of NON_COMPRIS) expect(texte, `${terme} sur ${adresse}`).not.toMatch(terme);
		});
});

test.describe('sur téléphone', { tag: '@telephone' }, () => {
	test('la barre du bas dit Sujets et Carte, et Détail seulement quand une fiche est ouverte', async ({ page }) => {
		await arriver(page, '/');
		const barre = page.getByRole('navigation', { name: 'Affichage' });
		await expect(barre.getByRole('button')).toHaveText(['Sujets', 'Carte']);
		await page.goto('/commune/pully');
		await expect(barre.getByRole('button')).toHaveText(['Sujets', 'Carte', 'Détail']);
	});
});
