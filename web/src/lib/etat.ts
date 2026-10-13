import { resolve } from '$app/paths';
import { NATURES, STATUTS_ORDRE } from './labels';
import type { Centre, Statut } from './types';

/**
 * État de la carte principale reflété dans l'URL (`/?d=…&vue=…`), pour le bouton retour et les liens à partager.
 * Lu uniquement dans le navigateur : les pages sont pré-générées sans paramètres.
 */
export interface EtatCarte {
	/** Dossier ouvert. */
	d: number | null;
	vue: Centre | null;
	/** `null` : statuts par défaut. */
	statuts: Statut[] | null;
	nature: string;
	historique: boolean;
	depuis: number | null;
	aerien: boolean;
	tri: Tri;
	/** Lien depuis une page commune : cadre la carte sur la commune (lu, jamais écrit). */
	commune: string | null;
}

/** Ordre de la liste : publication la plus récente d'abord, ou fin d'enquête la plus proche. */
export type Tri = 'recent' | 'fin';

export const STATUTS_EN_COURS: Statut[] = ['enquete', 'procedure'];

const entier = (s: string | null) => (s && /^\d+$/.test(s) ? Number(s) : null);

export function lireEtat(params: Pick<URLSearchParams, 'get'>): EtatCarte {
	const vue = params.get('vue')?.split(',').map(Number);
	const statuts = params
		.get('statuts')
		?.split(',')
		.filter((s): s is Statut => STATUTS_ORDRE.includes(s as Statut));
	const nature = params.get('nature') ?? '';
	return {
		d: entier(params.get('d')),
		vue: vue?.length === 3 && vue.every(Number.isFinite) ? { lat: vue[0], lon: vue[1], zoom: vue[2] } : null,
		statuts: statuts ?? null,
		nature: nature in NATURES ? nature : '',
		historique: params.get('historique') === '1',
		depuis: entier(params.get('depuis')),
		aerien: params.get('fond') === 'aerien',
		tri: params.get('tri') === 'fin' ? 'fin' : 'recent',
		commune: params.get('commune')
	};
}

/** Chaîne de requête (avec « ? », ou vide) ; seules les valeurs différentes des valeurs par défaut sont écrites. */
export function ecrireEtat(
	e: Omit<EtatCarte, 'commune'>,
	statutsParDefaut: Statut[],
	depuisParDefaut: number
): string {
	const p: [string, string][] = [];
	if (e.d != null) p.push(['d', String(e.d)]);
	if (e.vue) p.push(['vue', [e.vue.lat.toFixed(5), e.vue.lon.toFixed(5), e.vue.zoom.toFixed(2)].join(',')]);
	if (e.historique) p.push(['historique', '1']);
	if (e.historique && e.depuis != null && e.depuis !== depuisParDefaut) p.push(['depuis', String(e.depuis)]);
	const statuts = e.statuts ?? statutsParDefaut;
	if (statuts.length !== statutsParDefaut.length || statuts.some((s) => !statutsParDefaut.includes(s)))
		p.push(['statuts', STATUTS_ORDRE.filter((s) => statuts.includes(s)).join(',')]);
	if (e.nature) p.push(['nature', e.nature]);
	if (e.tri !== 'recent') p.push(['tri', e.tri]);
	if (e.aerien) p.push(['fond', 'aerien']);
	// Virgules laissées en clair : l'URL reste lisible.
	return p.length ? `?${p.map(([k, v]) => `${k}=${encodeURIComponent(v).replace(/%2C/g, ',')}`).join('&')}` : '';
}

/** Lien vers la carte principale, ouverte sur un dossier ou cadrée sur une commune. */
export const lienCarteDossier = (id: number) => `${resolve('/')}?d=${id}`;
export const lienCarteCommune = (slug: string) => `${resolve('/')}?commune=${encodeURIComponent(slug)}`;
