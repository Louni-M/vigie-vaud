import { afterEach, describe, expect, it, vi } from 'vitest';
import { couchePermis } from './index.js';
import { entite, fauxCanton } from '#tests/faux-canton.js';

// Le client du canton refuse de partir ailleurs que dans un navigateur.
vi.mock('$app/env', () => ({ browser: true }));

afterEach(() => vi.unstubAllGlobals());

describe('couche Permis', () => {
	it('titre un dossier ouvert par son n° et le nom de la fiche où il est ouvert', () => {
		expect(couchePermis.titre?.('248845', 'Lutry')).toBe('Dossier n° 248845 – Lutry – Vigie Vaud');
	});

	it('localise un dossier dans la seule fiche de sa commune, à son point', async () => {
		vi.stubGlobal('fetch', fauxCanton([entite(248845, {}, [6.72, 46.5])]).fetch);

		expect(await couchePermis.localiser?.('248845')).toEqual({
			fiches: [{ commune: 'lutry' }],
			position: [6.72, 46.5]
		});
	});

	it('ne localise pas un n° inconnu du canton', async () => {
		vi.stubGlobal('fetch', fauxCanton([]).fetch);

		expect(await couchePermis.localiser?.('999999')).toBeNull();
		expect(await couchePermis.localiser?.('abc')).toBeNull();
	});
});
