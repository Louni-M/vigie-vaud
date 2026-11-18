import { arriver, expect, test } from './banc.js';

/*
 * Ouvrir un volet pour la première fois. Le Volet d'une couche est un module chargé à part, à sa première ouverture :
 * le volet ne doit apparaître qu'avec son contenu, sans quoi sa bulle s'ouvre sur sa seule tête, l'ancien volet se
 * replie à cette taille, et la liste arrive d'un coup à la fin.
 *
 * Les modules du site sont retardés une fois la page chargée, comme sur un vrai réseau : servis par `vite preview`,
 * ils arriveraient avant la première image. Le scénario ne mesure aucun délai ; il regarde la première image où le
 * volet est là.
 */

test('le volet d’une couche ouvert pour la première fois apparaît avec son contenu', { tag: '@bureau' }, async ({
	page
}) => {
	await arriver(page, '/');
	await expect(page.getByRole('region', { name: 'Fil cantonal' })).toBeVisible();
	await page.route('**/_app/immutable/**', async (route) => {
		await new Promise((fin) => setTimeout(fin, 300));
		await route.fallback();
	});

	// À chaque image, jusqu'à la première où le volet Routes est là : a-t-il déjà sa légende ?
	await page.evaluate(() => {
		const w = window as unknown as { premiereImage?: boolean };
		const image = () => {
			const volet = document.getElementById('volet-routes');
			if (!volet) return requestAnimationFrame(image);
			w.premiereImage = volet.querySelector('[aria-label^="Sortes affichées"]') !== null;
		};
		requestAnimationFrame(image);
	});
	await page.getByRole('toolbar', { name: 'Couches' }).getByRole('button', { name: /Routes/ }).click();

	const volet = page.getByRole('region', { name: 'Routes' });
	await expect(volet.getByRole('group', { name: /^Sortes affichées/ })).toBeVisible();
	const premiereImage = await page.evaluate(() => (window as unknown as { premiereImage?: boolean }).premiereImage);
	expect(premiereImage, 'la légende du volet, dès sa première image').toBe(true);
});
