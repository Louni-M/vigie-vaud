import { describe, expect, it } from 'vitest';
import { CLE_RECHARGEMENT, DELAI_RECHARGEMENT, estFeuilleDeStyle, reserverRechargement } from './rechargement.js';

function stockage(depart: Record<string, string> = {}) {
	const valeurs = new Map(Object.entries(depart));
	return {
		valeurs,
		getItem: (cle: string) => valeurs.get(cle) ?? null,
		setItem: (cle: string, valeur: string) => void valeurs.set(cle, valeur)
	};
}

const T = 1_760_000_000_000;

describe('rechargement de secours', () => {
	it('recharge une fois, puis plus pendant le délai : pas de boucle', () => {
		const s = stockage();
		expect(reserverRechargement(() => s, T)).toBe(true);
		expect(s.valeurs.get(CLE_RECHARGEMENT)).toBe(String(T));
		expect(reserverRechargement(() => s, T + 2_000)).toBe(false);
		expect(reserverRechargement(() => s, T + DELAI_RECHARGEMENT - 1)).toBe(false);
	});

	it('recharge de nouveau une fois le délai passé (un autre déploiement)', () => {
		const s = stockage({ [CLE_RECHARGEMENT]: String(T) });
		expect(reserverRechargement(() => s, T + DELAI_RECHARGEMENT)).toBe(true);
		expect(s.valeurs.get(CLE_RECHARGEMENT)).toBe(String(T + DELAI_RECHARGEMENT));
	});

	it('ignore une valeur illisible ou une date dans le futur', () => {
		expect(reserverRechargement(() => stockage({ [CLE_RECHARGEMENT]: 'n’importe quoi' }), T)).toBe(true);
		expect(reserverRechargement(() => stockage({ [CLE_RECHARGEMENT]: String(T + 60_000) }), T)).toBe(true);
	});

	it('ne recharge pas sans stockage utilisable', () => {
		expect(
			reserverRechargement(() => {
				throw new DOMException('refusé', 'SecurityError');
			}, T)
		).toBe(false);
		const plein = {
			...stockage(),
			setItem: () => {
				throw new DOMException('plein', 'QuotaExceededError');
			}
		};
		expect(reserverRechargement(() => plein, T)).toBe(false);
	});
});

describe('erreur de préchargement de Vite', () => {
	it('reconnaît une feuille de style manquante', () => {
		const url = 'https://louni-m.github.io/vigie-vaud/_app/immutable/assets/Recherche.DHEGk7Aa.css';
		expect(estFeuilleDeStyle(new Error(`Unable to preload CSS for ${url}`))).toBe(true);
	});

	it('laisse passer un module de code manquant', () => {
		expect(estFeuilleDeStyle(new TypeError('Failed to fetch dynamically imported module: …/nodes/3.js'))).toBe(false);
		expect(estFeuilleDeStyle(undefined)).toBe(false);
	});
});
