import { asset } from '$app/paths';
import type { Commune, CommuneResume, Dossier, Meta } from './types';

type Fetch = typeof fetch;

// Cache au niveau du module : utile pendant la pré-génération (des milliers de fiches
// partagent les mêmes tranches) comme dans le navigateur.
const cache = new Map<string, Promise<unknown>>();

function getJson<T>(f: Fetch, path: string): Promise<T> {
	let p = cache.get(path) as Promise<T> | undefined;
	if (!p) {
		p = f(asset(path as Parameters<typeof asset>[0])).then((r) => {
			if (!r.ok) throw new Error(`${path} : ${r.status}`);
			return r.json() as Promise<T>;
		});
		p.catch(() => cache.delete(path));
		cache.set(path, p);
	}
	return p;
}

export const getMeta = (f: Fetch) => getJson<Meta>(f, 'data/meta.json');
export const getActive = (f: Fetch) => getJson<Dossier[]>(f, 'data/active.json');
export const getCommunes = (f: Fetch) => getJson<Commune[]>(f, 'data/communes.json');
export const getCommuneResume = (f: Fetch, slug: string) =>
	getJson<CommuneResume>(f, `data/communes/${slug}.json`);
export const getCommuneDossiers = (f: Fetch, slug: string) =>
	getJson<Dossier[]>(f, `data/communes/tout/${slug}.json`);

export async function getDossier(f: Fetch, id: number): Promise<Dossier | undefined> {
	const shard = await getJson<Dossier[]>(f, `data/dossiers/${Math.floor(id / 1000)}.json`).catch(
		() => [] as Dossier[]
	);
	return shard.find((d) => d.id === id);
}
