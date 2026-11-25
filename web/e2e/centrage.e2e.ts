import type { Page } from '@playwright/test';
import { arriver, centreDeLaCarte, expect, test } from './banc.js';

/*
 * Ce qu'on ouvre se place au centre de ce qu'on voit de la carte : entre le panneau posé à gauche et la fiche ouverte
 * à droite, et sur toute la carte quand il reste trop peu de place à côté du panneau (`margeDuPanneau`).
 *
 * La vue par défaut (une commune qu'on ouvre) n'entre pas dans l'adresse : fermer la fiche l'y écrit, sans bouger la
 * carte. Le dossier 260102 est à 6,664 E ; 46,511 N (banc.ts) ; l'hôtel de ville d'Aclens à 6,50968 E ; 46,56801 N
 * (static/communes.json), au sud-ouest de son emprise terrestre.
 */

const ACLENS = { lat: 46.56801, lon: 6.50968 };
const DOSSIER = { lat: 46.511, lon: 6.664 };

/** La vue `vue=lat,lon,zoom` de l'adresse ; vide tant qu'elle n'y est pas. */
function vue(page: Page): { lat: number; lon: number; zoom: number } | null {
	const v = new URL(page.url()).searchParams.get('vue');
	if (!v) return null;
	const [lat, lon, zoom] = v.split(',').map(Number);
	return { lat, lon, zoom };
}

/** Ferme la fiche d'Aclens et rend la vue que la carte avait : la fermeture l'écrit dans l'adresse. */
async function vueDeLaFicheAclens(page: Page) {
	await expect(page.getByRole('heading', { name: 'Aclens', level: 2 })).toBeVisible();
	// La carte a fini de cadrer la commune (un saut à l'arrivée) et la colonne de la fiche de s'ouvrir.
	await page.waitForTimeout(1000);
	await page.getByRole('button', { name: 'Fermer la fiche d’Aclens' }).click();
	await expect(page).toHaveURL(/vue=/);
	return vue(page)!;
}

test.describe('sur bureau', { tag: '@bureau' }, () => {
	test('une commune ouverte a son hôtel de ville au centre de la vue, pas le milieu de son emprise', async ({ page }) => {
		await arriver(page, '/commune/aclens');
		const v = await vueDeLaFicheAclens(page);
		expect(v.lat, 'latitude du centre').toBeCloseTo(ACLENS.lat, 4);
		expect(v.lon, 'longitude du centre').toBeCloseTo(ACLENS.lon, 4);
	});

	test('la fenêtre redimensionnée, le centre de la vue reste au milieu de ce qu’on voit', async ({ page }) => {
		await arriver(page, `/?volet=permis&vue=${DOSSIER.lat.toFixed(5)},${DOSSIER.lon.toFixed(5)},17.00`);
		await expect(page.getByRole('region', { name: 'Permis de construire' })).toContainText('Pose de panneaux solaires');
		await page.setViewportSize({ width: 1024, height: 700 });
		// On recommence tant que les dossiers ne sont pas dessinés : un clic au centre de ce qu'on voit ouvre celui-là.
		await expect(async () => {
			await page.mouse.click(...(await centreDeLaCarte(page)));
			await expect(page).toHaveURL(/d=260102/, { timeout: 1000 });
		}).toPass();
	});

	test.describe('carte étroite (tablette, fiche ouverte)', () => {
		test.use({ viewport: { width: 800, height: 800 } });

		test('la marge du panneau cède : une commune est cadrée sur toute la carte, pas dans une bande', async ({
			page
		}) => {
			// 800 px de large : 480 px de carte à côté de la fiche, dont 370 sous le panneau. Cadrée dans les 110 px restants,
			// Aclens tombait au zoom 9 (mesuré : 9,1) ; sur les 480 px, elle passe le zoom 12.
			await arriver(page, '/commune/aclens');
			const v = await vueDeLaFicheAclens(page);
			expect(v.zoom, 'zoom du cadrage').toBeGreaterThan(12);
		});

		test.describe('avec animation', () => {
			test.use({ reducedMotion: 'no-preference' });

			test('un vol survit à la marge qui change en route : la fiche ouverte la rend nulle', async ({ page }) => {
				// La fiche de Pully s'ouvre pendant le vol vers le dossier : la carte rétrécit et sa marge passe de 370 px à 0.
				// Poser la marge arrête le vol ; sans relance, il s'arrêterait à côté du dossier.
				await arriver(page, '/?volet=permis&vue=46.50300,6.65000,13.00');
				await page.getByRole('region', { name: 'Permis de construire' }).getByText('Pose de panneaux solaires').click();
				await expect(page).toHaveURL(/\/commune\/pully\?.*d=260102/);
				await expect(async () => {
					const v = vue(page);
					expect(v?.lat, 'latitude du centre').toBeCloseTo(DOSSIER.lat, 4);
					expect(v?.lon, 'longitude du centre').toBeCloseTo(DOSSIER.lon, 4);
				}).toPass({ timeout: 15_000 });
			});
		});
	});
});
