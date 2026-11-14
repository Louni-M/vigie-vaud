import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DELAIS_ESSAI } from './etat-source.svelte.js';
import { estSondee } from './couverture.js';
import type { EtatSources, ImportConseils } from './schema.js';
import { SOURCES } from './sources.js';
// Importés dès la collecte, hors du délai des tests : leur première transformation par Vite, qui prend des secondes
// sur une machine chargée, est faite ; les modules neufs de chaque test ne sont plus qu'évalués.
import './couverture-courante.svelte.js';
import './imports-courants.svelte.js';

/*
 * La Couverture courante et les imports courants, chargés une fois par visite dans le navigateur, se rétablissent
 * d'un échec passager du dépôt de données sans que la page soit rechargée. Chaque test importe des modules neufs :
 * leur état vit le temps de la visite.
 */

vi.mock('$app/env', () => ({ browser: true }));

const MAINTENANT = new Date('2026-11-13T10:00:00Z');
const json = (corps: unknown) => new Response(JSON.stringify(corps), { status: 200 });

/** Le `fetch` du navigateur : d'abord en panne, puis le dépôt de données répond `corps`. */
function pannePuis(corps: unknown) {
	const f = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValue(json(corps));
	vi.stubGlobal('fetch', f);
	return f;
}

describe('chargement courant après un échec passager', () => {
	beforeEach(() => {
		vi.useFakeTimers({ now: MAINTENANT });
		vi.resetModules();
	});
	afterEach(() => {
		vi.useRealTimers();
		vi.unstubAllGlobals();
	});

	it('la Couverture courante retrouve l’état des sources', async () => {
		const sondee = SOURCES.find(estSondee)!;
		const etat: EtatSources = {
			version: 1,
			genere: MAINTENANT.toISOString(),
			sources: {
				[sondee.id]: {
					etat: 'en_panne',
					depuis: '2026-11-13T08:00:00Z',
					derniere_sonde: '2026-11-13T08:00:00Z',
					dernier_succes: null,
					echecs_consecutifs: 1,
					motif: 'injoignable'
				}
			}
		};
		const f = pannePuis(etat);
		const { couvertureChargee, couvertureCourante } = await import('./couverture-courante.svelte.js');

		expect(couvertureCourante().etat(sondee.id)).toEqual({ etat: 'inconnu' });
		await vi.advanceTimersByTimeAsync(0);
		expect(couvertureChargee()).toBe(true);
		expect(couvertureCourante().etat(sondee.id)).toEqual({ etat: 'inconnu' });

		await vi.advanceTimersByTimeAsync(DELAIS_ESSAI[0]);
		expect(couvertureCourante().etat(sondee.id)).toEqual({ etat: 'en_panne', depuis: '2026-11-13T08:00:00Z' });
		expect(f).toHaveBeenCalledTimes(2);
	});

	it('les imports courants retrouvent le dernier import des conseils', async () => {
		const imports: ImportConseils = { version: 1, genere: MAINTENANT.toISOString(), conseils: { vd: '2026-11-13T05:10:00Z' } };
		const f = pannePuis(imports);
		const { importsCharges, importsCourants } = await import('./imports-courants.svelte.js');

		expect(importsCourants()).toBeNull();
		await vi.advanceTimersByTimeAsync(0);
		expect(importsCharges()).toBe(true);
		expect(importsCourants()).toBeNull();

		await vi.advanceTimersByTimeAsync(DELAIS_ESSAI[0]);
		expect(importsCourants()).toEqual(imports);
		expect(f).toHaveBeenCalledTimes(2);
	});
});
