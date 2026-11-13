import { vi } from 'vitest';

/** Un `fetch` qui ne répond jamais : il ne rejette, avec la raison de l'interruption, que si sa requête est interrompue. */
export const sansReponse = (_entree: RequestInfo | URL, init?: RequestInit) =>
	new Promise<Response>((_, ko) => {
		const signal = init?.signal;
		if (signal?.aborted) ko(signal.reason);
		signal?.addEventListener('abort', () => ko(signal.reason));
	});

/**
 * Fait expirer tout de suite le délai d'attente des requêtes (`AbortSignal.timeout`), et rend l'espion : ses appels
 * disent le délai demandé. À rétablir par `vi.restoreAllMocks()`.
 */
export const delaiExpire = () =>
	vi.spyOn(AbortSignal, 'timeout').mockImplementation(() => {
		const c = new AbortController();
		c.abort(new DOMException('Délai dépassé', 'TimeoutError'));
		return c.signal;
	});
