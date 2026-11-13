import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushSync } from 'svelte';
import { creerEtatSource, DELAIS_ESSAI } from './etat-source.svelte.js';

/*
 * L'état d'une source chargée une fois par visite (état des sources, imports des conseils) : il réessaie après un
 * échec, sans que la page ait à le redemander.
 */

const passe = (ms: number) => vi.advanceTimersByTimeAsync(ms);

describe('état de source partagé', () => {
	beforeEach(() => vi.useFakeTimers());
	afterEach(() => vi.useRealTimers());

	it('se rétablit après un échec passager, sans nouvelle demande de la page', async () => {
		const charger = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new TypeError('réseau')).mockResolvedValue('lu');
		const s = creerEtatSource(charger, { actif: true });

		expect(s.valeur()).toBeNull();
		expect(s.chargee()).toBe(false);
		await passe(0);
		// Le premier essai a échoué : chargée (« inconnue ») pour l'instant, sans valeur.
		expect(s.chargee()).toBe(true);
		expect(s.valeur()).toBeNull();

		await passe(DELAIS_ESSAI[0]);
		expect(s.valeur()).toBe('lu');
		expect(charger).toHaveBeenCalledTimes(2);
	});

	it('prévient ceux qui la lisent quand la valeur arrive après un échec', async () => {
		const charger = vi.fn<() => Promise<string>>().mockRejectedValueOnce(new TypeError('réseau')).mockResolvedValue('lu');
		const s = creerEtatSource(charger, { actif: true });
		const vus: (string | null)[] = [];
		const fin = $effect.root(() => {
			$effect(() => {
				vus.push(s.valeur());
			});
		});
		flushSync();
		await passe(0);
		await passe(DELAIS_ESSAI[0]);
		flushSync();
		expect(vus.at(-1)).toBe('lu');
		fin();
	});

	it('espace ses essais quand la source reste en panne, puis réessaie à intervalle fixe', async () => {
		const charger = vi.fn<() => Promise<string>>().mockRejectedValue(new TypeError('réseau'));
		const s = creerEtatSource(charger, { actif: true });
		s.valeur();
		await passe(0);
		expect(charger).toHaveBeenCalledTimes(1);
		// Ni la page qui relit, ni le temps qui passe avant le délai, ne relancent la requête.
		s.valeur();
		s.chargee();
		await passe(DELAIS_ESSAI[0] - 1);
		expect(charger).toHaveBeenCalledTimes(1);
		await passe(1);
		expect(charger).toHaveBeenCalledTimes(2);
		await passe(DELAIS_ESSAI[1]);
		expect(charger).toHaveBeenCalledTimes(3);
		const dernier = DELAIS_ESSAI.at(-1)!;
		for (const d of DELAIS_ESSAI.slice(2)) await passe(d);
		expect(charger).toHaveBeenCalledTimes(DELAIS_ESSAI.length + 1);
		await passe(dernier);
		expect(charger).toHaveBeenCalledTimes(DELAIS_ESSAI.length + 2);
	});

	it('ne charge qu’une fois, quel que soit le nombre de lectures, et plus rien après la réussite', async () => {
		let fini!: (v: string) => void;
		const charger = vi.fn(() => new Promise<string>((ok) => (fini = ok)));
		const s = creerEtatSource(charger, { actif: true });
		s.valeur();
		s.chargee();
		s.valeur();
		fini('lu');
		await passe(0);
		s.valeur();
		await passe(10 * DELAIS_ESSAI.at(-1)!);
		expect(charger).toHaveBeenCalledTimes(1);
		expect(s.valeur()).toBe('lu');
	});

	it('ne charge rien hors du navigateur (pré-génération)', async () => {
		const charger = vi.fn(async () => 'lu');
		const s = creerEtatSource(charger, { actif: false });
		expect(s.valeur()).toBeNull();
		expect(s.chargee()).toBe(false);
		await passe(0);
		expect(charger).not.toHaveBeenCalled();
	});
});
