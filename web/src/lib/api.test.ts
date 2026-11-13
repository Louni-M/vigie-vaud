import { afterEach, describe, expect, it, vi } from 'vitest';
import { delaiExpire, sansReponse } from '#tests/sans-reponse.js';
import { appelArcgis, ErreurApi } from './api.js';

vi.mock('$app/env', () => ({ browser: true }));

const NOM = { sujet: 'Le service du canton', complement: 'du service du canton' };

describe('un appel à un service ArcGIS', () => {
	afterEach(() => {
		vi.restoreAllMocks();
		vi.unstubAllGlobals();
	});

	it('dit que le service ne répond pas quand il dépasse le délai d’attente partagé', async () => {
		vi.stubGlobal('navigator', { onLine: true });
		const delai = delaiExpire();
		const appel = appelArcgis(sansReponse, NOM, 'https://canton/query');
		await expect(appel).rejects.toBeInstanceOf(ErreurApi);
		await expect(appel).rejects.toMatchObject({ message: 'Le service du canton ne répond pas.', hors_ligne: false });
		expect(delai).toHaveBeenCalledWith(20_000);
	});

	it('dit le service injoignable quand le réseau tombe, hors ligne si le navigateur le dit', async () => {
		vi.stubGlobal('navigator', { onLine: false });
		const appel = appelArcgis(() => Promise.reject(new TypeError('réseau')), NOM, 'https://c');
		await expect(appel).rejects.toMatchObject({ message: 'Le service du canton est injoignable.', hors_ligne: true });
	});
});
