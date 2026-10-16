import type { Centre } from '#lib/types.js';
import type { CoucheInscrite, Lecteur, Ouvert } from './types.js';

/**
 * L'état de la carte que porte la requête de l'adresse. La commune ouverte est dans le chemin
 * (`/commune/<slug>`, ADR 0012) ; tout le reste est ici, lu dans le navigateur seulement
 * (les pages sont pré-générées sans paramètres).
 */
export interface EtatUrl {
	/** Couches activées, dans l'ordre du registre ; les couches permanentes en font toujours partie. */
	actives: string[];
	vue: Centre | null;
	ouvert: Ouvert | null;
	/** Paramètres décodés de chaque couche qui a un codec, par identifiant de couche. */
	parametres: Record<string, unknown>;
}

/** Clés de requête propres au registre ; les clés d'élément des couches s'y ajoutent. */
export const CLES_REGISTRE = ['couches', 'vue'] as const;

function lireVue(texte: string | null): Centre | null {
	const v = texte?.split(',').map((s) => (s.trim() === '' ? NaN : Number(s)));
	return v?.length === 3 && v.every(Number.isFinite) ? { lat: v[0], lon: v[1], zoom: v[2] } : null;
}

const parDefaut = (couches: readonly CoucheInscrite[]) =>
	couches.filter((c) => c.permanente || c.activeParDefaut).map((c) => c.id);

export function lireUrl(couches: readonly CoucheInscrite[], params: Lecteur): EtatUrl {
	const demandees = params.get('couches')?.split(',');
	const actives = demandees
		? couches.filter((c) => c.permanente || demandees.includes(c.id)).map((c) => c.id)
		: parDefaut(couches);
	const avecElement = couches.find((c) => c.cleElement && params.get(c.cleElement));
	return {
		actives,
		vue: lireVue(params.get('vue')),
		ouvert: avecElement ? { couche: avecElement.id, element: params.get(avecElement.cleElement!)! } : null,
		parametres: Object.fromEntries(couches.flatMap((c) => (c.codec ? [[c.id, c.codec.lire(params)]] : [])))
	};
}

/** Requête de l'adresse (avec « ? », ou vide) ; seules les valeurs différentes des valeurs par défaut sont écrites. */
export function ecrireUrl(couches: readonly CoucheInscrite[], e: EtatUrl): string {
	const paires: [string, string][] = [];
	const cle = couches.find((c) => c.id === e.ouvert?.couche)?.cleElement;
	if (e.ouvert && cle) paires.push([cle, e.ouvert.element]);

	const reglables = couches.filter((c) => !c.permanente);
	const actives = reglables.filter((c) => e.actives.includes(c.id)).map((c) => c.id);
	const defaut = reglables.filter((c) => c.activeParDefaut).map((c) => c.id);
	if (actives.join(',') !== defaut.join(',')) paires.push(['couches', actives.join(',')]);

	if (e.vue) paires.push(['vue', [e.vue.lat.toFixed(5), e.vue.lon.toFixed(5), e.vue.zoom.toFixed(2)].join(',')]);
	for (const c of couches) if (c.codec && c.id in e.parametres) paires.push(...c.codec.ecrire(e.parametres[c.id]));
	// Virgules et barres obliques laissées en clair (`?c=vd/26_INT_140`) : l'adresse reste lisible.
	const valeur = (v: string) => encodeURIComponent(v).replace(/%2C/g, ',').replace(/%2F/g, '/');
	return paires.length ? `?${paires.map(([k, v]) => `${k}=${valeur(v)}`).join('&')}`
		: '';
}

/** Clés de requête prises plus d'une fois, par le registre ou par les couches inscrites. */
export function clesEnDouble(couches: readonly CoucheInscrite[]): string[] {
	const vues = new Set<string>(CLES_REGISTRE);
	const doubles = new Set<string>();
	for (const c of couches)
		for (const cle of [...(c.cleElement ? [c.cleElement] : []), ...(c.codec?.cles ?? [])]) {
			if (vues.has(cle)) doubles.add(cle);
			vues.add(cle);
		}
	return [...doubles];
}
