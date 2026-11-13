import { afterEach, describe, expect, it, vi } from 'vitest';
import { delaiExpire, sansReponse } from '#tests/sans-reponse.js';
import { DELAI_REQUETE, delaiDepasse, lireJsonVersionne, memoPromesse, requeteAvecDelai } from './chargement.js';

afterEach(() => vi.restoreAllMocks());

const reponse = (corps: unknown, status = 200) =>
	new Response(typeof corps === 'string' ? corps : JSON.stringify(corps), { status });

describe('la lecture d’un fichier JSON versionné', () => {
	it('rend le contenu d’un fichier de la version connue', async () => {
		const f = vi.fn(async (_e: RequestInfo | URL, _i?: RequestInit) => reponse({ version: 1, n: 3 }));
		expect(await lireJsonVersionne(f, 'https://d/index.json', 1, { init: { cache: 'no-cache' } })).toEqual({
			version: 1,
			n: 3
		});
		expect(f).toHaveBeenCalledWith('https://d/index.json', expect.objectContaining({ cache: 'no-cache' }));
	});

	it('rejette un fichier d’une version inconnue, ou qui n’est pas un objet versionné', async () => {
		await expect(lireJsonVersionne(async () => reponse({ version: 2 }), 'https://d/i.json', 1)).rejects.toThrow(
			'https://d/i.json : version inconnue (2)'
		);
		await expect(lireJsonVersionne(async () => reponse('null'), 'https://d/i.json', 1)).rejects.toThrow(
			/version inconnue/
		);
	});

	it('rejette un fichier absent, illisible ou injoignable', async () => {
		await expect(lireJsonVersionne(async () => reponse('', 503), 'https://d/i.json', 1)).rejects.toThrow(
			'https://d/i.json : HTTP 503'
		);
		await expect(lireJsonVersionne(async () => reponse('', 404), 'https://d/i.json', 1)).rejects.toThrow(/HTTP 404/);
		await expect(lireJsonVersionne(async () => reponse('{'), 'https://d/i.json', 1)).rejects.toThrow();
		await expect(
			lireJsonVersionne(() => Promise.reject(new TypeError('réseau')), 'https://d/i.json', 1)
		).rejects.toThrow('réseau');
	});

	it('donne ce que vaut un fichier absent quand on le dit, au lieu de rejeter', async () => {
		expect(await lireJsonVersionne(async () => reponse('', 404), 'https://d/i.json', 1, { absent: { vaut: null } })).toBe(
			null
		);
	});

	it('rejette quand le dépôt de données ne répond pas à temps', async () => {
		delaiExpire();
		const erreur = await lireJsonVersionne(sansReponse, 'https://d/i.json', 1).catch((e) => e);
		expect(delaiDepasse(erreur)).toBe(true);
	});
});

describe('une promesse gardée par clé', () => {
	it('est la même pour une clé, en cours puis réussie : le chargement n’est fait qu’une fois', async () => {
		const memo = memoPromesse<string>();
		const g = vi.fn(async () => 'lu');
		const p = memo('a', g);
		expect(memo('a', g)).toBe(p);
		expect(await p).toBe('lu');
		expect(memo('a', g)).toBe(p);
		expect(g).toHaveBeenCalledTimes(1);
	});

	it('est propre à chaque clé', async () => {
		const memo = memoPromesse<string>();
		expect(await memo('a', async () => 1)).toBe(1);
		expect(await memo('b', async () => 2)).toBe(2);
	});

	it('est oubliée en cas d’échec : l’appel suivant réessaie', async () => {
		const memo = memoPromesse<string>();
		const g = vi.fn().mockRejectedValueOnce(new Error('panne')).mockResolvedValueOnce('lu');
		await expect(memo('a', g)).rejects.toThrow('panne');
		expect(memo.demandee('a')).toBe(false);
		expect(await memo('a', g)).toBe('lu');
		expect(g).toHaveBeenCalledTimes(2);
	});

	it('dit si une clé est demandée : en cours ou réussie', async () => {
		const memo = memoPromesse<void>();
		expect(memo.demandee()).toBe(false);
		const p = memo(undefined, async () => 'lu');
		expect(memo.demandee()).toBe(true);
		await p;
		expect(memo.demandee()).toBe(true);
	});
});

describe('une requête avec délai d’attente', () => {
	it('est interrompue quand le serveur ne répond pas à temps', async () => {
		const erreur = await requeteAvecDelai(sansReponse, 'https://d/x.json', {}, 5).catch((e) => e);
		expect(delaiDepasse(erreur)).toBe(true);
	});

	it('attend 20 s par défaut, comme le client du canton', async () => {
		const delai = delaiExpire();
		const erreur = await requeteAvecDelai(sansReponse, 'https://d/x.json').catch((e) => e);
		expect(delaiDepasse(erreur)).toBe(true);
		expect(delai).toHaveBeenCalledWith(20_000);
		expect(DELAI_REQUETE).toBe(20_000);
	});

	it('rend la réponse du serveur, avec les options de la requête', async () => {
		const f = vi.fn(async (_e: RequestInfo | URL, _i?: RequestInit) => new Response('{}'));
		const r = await requeteAvecDelai(f, 'https://d/x.json', { cache: 'no-cache' });
		expect(await r.json()).toEqual({});
		expect(f).toHaveBeenCalledWith('https://d/x.json', expect.objectContaining({ cache: 'no-cache' }));
	});

	it('ne prend pas une panne du réseau pour un délai dépassé', async () => {
		const erreur = await requeteAvecDelai(() => Promise.reject(new TypeError('réseau')), 'https://d').catch((e) => e);
		expect(erreur).toBeInstanceOf(TypeError);
		expect(delaiDepasse(erreur)).toBe(false);
	});
});
