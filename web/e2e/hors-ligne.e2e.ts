import { expect, test } from './banc.js';

/*
 * La suite ne fait aucune requête hors de la machine : la garde du banc refuse toute requête vers une autre machine
 * qu'aucun service factice n'a prise, et le scénario échoue. Ce test le montre, puis efface ce qu'elle a relevé.
 */

test('refuse et relève toute requête vers une autre machine que rien n’intercepte', async ({ page, reseau }) => {
	await page.goto('/');

	const issue = await page.evaluate(() =>
		fetch('https://exemple.invalid/fuite.json').then(
			() => 'servie',
			() => 'refusée'
		)
	);

	expect(issue).toBe('refusée');
	expect(reseau.inattendues).toEqual(['GET https://exemple.invalid/fuite.json']);
	// Relevée, elle ferait échouer ce test à la fin (voir le suivant) : on l'efface, c'est ce qu'on voulait montrer.
	reseau.inattendues.length = 0;
});

test('fait échouer le scénario qui a tenté une telle requête, même si tout le reste passe', async ({ page }) => {
	// Ce test doit échouer, à la fin, par la garde seule : Playwright le compte réussi s'il échoue.
	test.fail();
	await page.goto('/');

	await page.evaluate(() => fetch('https://exemple.invalid/fuite.json').catch(() => {}));
});
