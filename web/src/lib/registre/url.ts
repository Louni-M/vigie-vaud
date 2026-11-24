import { lireAffichage, type Affichage } from '#lib/socle/telephone.js';
import type { Centre } from '#lib/types.js';
import { rubriqueAVolet, rubriqueDeLElement } from './rubriques.js';
import type { CoucheInscrite, Lecteur, Ouvert } from './types.js';

/** Le panneau à l'arrivée : le sommaire, à la place d'une rubrique ouverte. */
export const SOMMAIRE = 'sommaire';

/**
 * L'état de la carte que porte la requête de l'adresse. La commune ouverte est dans le chemin
 * (`/commune/<slug>`, ADR 0012) ; tout le reste est ici, lu dans le navigateur seulement
 * (les pages sont pré-générées sans paramètres).
 */
export interface EtatUrl {
	vue: Centre | null;
	ouvert: Ouvert | null;
	/** Paramètres décodés de chaque couche qui a un codec, par identifiant de couche. */
	parametres: Record<string, unknown>;
	/**
	 * Ce que montre le panneau : `SOMMAIRE`, ou l'identifiant d'une rubrique à volet (`volet=routes`). Sans `volet=`,
	 * celui que donne l'élément ouvert (`panneauDeLElement`).
	 */
	panneau: string;
	/**
	 * Vue du téléphone (`affichage=panneau`) ; `null` : celle de l'arrivée, que le registre n'écrit pas (la fiche
	 * quand une fiche est ouverte, la carte quand un élément ou une vue de la carte l'est, sinon le panneau).
	 */
	affichage: Affichage | null;
	/**
	 * Onglet choisi dans la fiche commune, l'id de sa couche (`onglet=conseils`) ; `null` : le premier, que le registre
	 * n'écrit pas, pas plus que celui de l'élément ouvert.
	 */
	onglet: string | null;
}

/**
 * Clés de requête propres au registre ; les clés d'élément des couches s'y ajoutent. `couches`, que les anciennes
 * adresses portent encore, est ignorée et jamais écrite : elle reste réservée.
 */
export const CLES_REGISTRE = ['couches', 'vue', 'volet', 'affichage', 'onglet'] as const;

function lireVue(texte: string | null): Centre | null {
	const v = texte?.split(',').map((s) => (s.trim() === '' ? NaN : Number(s)));
	return v?.length === 3 && v.every(Number.isFinite) ? { lat: v[0], lon: v[1], zoom: v[2] } : null;
}

/**
 * Le panneau qu'ouvre une adresse sans `volet=` : la rubrique de l'élément ouvert, si elle a un volet ; sinon le
 * sommaire.
 */
export function panneauDeLElement(couches: readonly CoucheInscrite[], ouvert: Ouvert | null): string {
	const r = ouvert && rubriqueDeLElement(couches, ouvert);
	return r && !r.rubrique.fiche ? r.rubrique.id : SOMMAIRE;
}

export function lireUrl(couches: readonly CoucheInscrite[], params: Lecteur): EtatUrl {
	const avecElement = couches.find((c) => c.cleElement && params.get(c.cleElement));
	const ouvert = avecElement ? { couche: avecElement.id, element: params.get(avecElement.cleElement!)! } : null;
	// Un volet que nomme l'adresse l'emporte ; s'il n'est pas celui d'une rubrique (l'ancien fil, `volet=`), c'est le
	// sommaire.
	const volet = params.get('volet');
	const affichage = params.get('affichage');
	const onglet = params.get('onglet');
	return {
		vue: lireVue(params.get('vue')),
		ouvert,
		parametres: Object.fromEntries(couches.flatMap((c) => (c.codec ? [[c.id, c.codec.lire(params)]] : []))),
		panneau: volet === null ? panneauDeLElement(couches, ouvert) : rubriqueAVolet(couches, volet) ? volet : SOMMAIRE,
		affichage: lireAffichage(affichage),
		onglet: couches.find((c) => c.id === onglet && c.composants.Onglet)?.id ?? null
	};
}

/**
 * Requête de l'adresse (avec « ? », ou vide) ; seules les valeurs différentes des valeurs par défaut sont écrites :
 * le panneau dès qu'il n'est pas celui que donne l'élément ouvert (`volet=sommaire` pour un élément ouvert depuis le
 * sommaire). La vue du téléphone et l'onglet, dont la valeur par défaut dépend du chemin, sont écrits dès qu'ils ne
 * sont pas `null`.
 */
export function ecrireUrl(couches: readonly CoucheInscrite[], e: EtatUrl): string {
	const paires: [string, string][] = [];
	const cle = couches.find((c) => c.id === e.ouvert?.couche)?.cleElement;
	if (e.ouvert && cle) paires.push([cle, e.ouvert.element]);


	if (e.vue) paires.push(['vue', [e.vue.lat.toFixed(5), e.vue.lon.toFixed(5), e.vue.zoom.toFixed(2)].join(',')]);
	for (const c of couches) if (c.codec && c.id in e.parametres) paires.push(...c.codec.ecrire(e.parametres[c.id]));
	if (e.panneau !== panneauDeLElement(couches, e.ouvert)) paires.push(['volet', e.panneau]);
	if (e.affichage) paires.push(['affichage', e.affichage]);
	if (e.onglet) paires.push(['onglet', e.onglet]);
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
