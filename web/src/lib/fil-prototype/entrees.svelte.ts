/*
 * PROTOTYPE (ticket #45), à jeter : les entrées du fil cantonal. Objets et séances viennent de la couche Conseils
 * factice ; les nouveaux dossiers de permis sont les vrais dossiers mis à l'enquête ces 14 derniers jours.
 */
import type { Map as MlMap, GeoJSONSource } from 'maplibre-gl';
import { natureLabel } from '#lib/labels.js';
import { permis } from '#lib/couches/permis/donnees.svelte.js';
import { ELEMENTS, dateDe, type ElementConseil } from '#lib/couches/conseils-prototype/donnees.js';
import type { Cible } from '#lib/registre/types.js';
import type { Commune, Dossier, Zone } from '#lib/types.js';

export type TypeEntree = 'objet' | 'seance' | 'permis';
export const TYPES: { id: TypeEntree; nom: string; couleur: string; signe: string }[] = [
	{ id: 'objet', nom: 'Objets', couleur: '#7a3e9d', signe: '§' },
	{ id: 'seance', nom: 'Séances', couleur: '#2f6f8f', signe: '◷' },
	{ id: 'permis', nom: 'Nouveaux dossiers', couleur: '#c0392b', signe: 'P' }
];
export const typeDe = (t: TypeEntree) => TYPES.find((x) => x.id === t)!;

export interface Entree {
	cle: string;
	type: TypeEntree;
	date: Date;
	/** Séance annoncée, pas encore tenue. */
	avenir: boolean;
	/** « Motion », « Séance », « Construction nouvelle ». */
	sorte: string;
	titre: string;
	/** Qui : « Grand Conseil », « Conseil communal de Pully », « Lutry ». */
	qui: string;
	/** Communes rattachées (vide : sans rattachement, l'entrée n'est que dans le fil). */
	communes: Commune[];
	/** Où la carte vole, et ce qui est surligné au survol. */
	positions: [number, number][];
	cible: Cible | null;
	conseil?: ElementConseil;
	dossier?: Dossier;
}

const JOURS_NOUVEAU = 14;

function depuisConseil(x: ElementConseil, communes: readonly Commune[]): Entree {
	const cs = x.communes.map((s) => communes.find((c) => c.slug === s)).filter((c): c is Commune => !!c);
	const conseil = x.conseil ? communes.find((c) => c.slug === x.conseil) : null;
	return {
		cle: `o:${x.id}`,
		type: x.sorte,
		date: dateDe(x),
		avenir: x.age < 0,
		sorte: x.type,
		titre: x.titre,
		qui: conseil ? `Conseil communal de ${conseil.nom}` : 'Grand Conseil',
		communes: cs,
		positions: cs.map((c) => c.hotel),
		cible: cs.length ? { couche: 'conseils', element: x.id, position: cs[0].hotel } : null,
		conseil: x
	};
}

function depuisDossier(d: Dossier, communes: readonly Commune[]): Entree {
	const c = communes.find((c) => c.slug === d.slug);
	return {
		cle: `d:${d.id}`,
		type: 'permis',
		date: new Date(`${d.debut}T12:00:00`),
		avenir: false,
		sorte: natureLabel(d.nature),
		titre: d.description ?? natureLabel(d.nature),
		qui: d.commune,
		communes: c ? [c] : [],
		positions: [[d.lon, d.lat]],
		cible: { couche: 'permis', element: String(d.id), position: [d.lon, d.lat] },
		dossier: d
	};
}

/** Toutes les entrées, la plus récente d'abord ; les séances à venir en tête. */
export function toutes(communes: readonly Commune[]): Entree[] {
	const limite = new Date();
	limite.setDate(limite.getDate() - JOURS_NOUVEAU);
	const seuil = limite.toISOString().slice(0, 10);
	const dossiers = permis.actifs.filter((d) => d.statut === 'enquete' && (d.debut ?? '') >= seuil);
	return [...ELEMENTS.map((x) => depuisConseil(x, communes)), ...dossiers.map((d) => depuisDossier(d, communes))].sort(
		(a, b) => Number(b.avenir) - Number(a.avenir) || (a.avenir ? +a.date - +b.date : +b.date - +a.date)
	);
}

export const dansZone = (e: Entree, z: Zone | null) =>
	!!z && e.positions.some(([lon, lat]) => lon >= z[0] && lon <= z[2] && lat >= z[1] && lat <= z[3]);

export const sansRattachement = (e: Entree) => e.cible === null;

/** Jour relatif : « aujourd'hui », « hier », « mardi 7 oct. », « jeudi 21 oct. (à venir) ». */
const fmtJour = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'short' });
export function jour(d: Date): string {
	const a = new Date();
	a.setHours(12, 0, 0, 0);
	const n = Math.round((+a - +d) / 86400000);
	if (n === 0) return 'Aujourd’hui';
	if (n === 1) return 'Hier';
	if (n === -1) return 'Demain';
	const s = fmtJour.format(d);
	return s[0].toUpperCase() + s.slice(1);
}
export const court = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short' });

/** Regroupe des entrées par jour, dans l'ordre. */
export function parJour(es: Entree[]): { jour: string; entrees: Entree[] }[] {
	const g: { jour: string; entrees: Entree[] }[] = [];
	for (const e of es) {
		const j = e.avenir ? `À venir · ${jour(e.date)}` : jour(e.date);
		if (g.at(-1)?.jour === j) g.at(-1)!.entrees.push(e);
		else g.push({ jour: j, entrees: [e] });
	}
	return g;
}

/** Filtre par type et par portée, partagé par les variantes (chacune le présente à sa façon). */
export class Filtre {
	types = $state<TypeEntree[]>(['objet', 'seance', 'permis']);
	/** Limité à la zone visible de la carte, ou tout le canton. */
	zone = $state(true);
	basculer(t: TypeEntree) {
		this.types = this.types.includes(t) ? this.types.filter((x) => x !== t) : [...this.types, t];
	}
	seul(t: TypeEntree) {
		this.types = this.types.length === 1 && this.types[0] === t ? TYPES.map((x) => x.id) : [t];
	}
}

/* ---- Survol : l'entrée survolée est surlignée sur la carte ---- */

const ID = 'fil-surbrillance';
export function surligner(map: MlMap | null, e: Entree | null) {
	if (!map) return;
	const data: Parameters<GeoJSONSource["setData"]>[0] & object = {
		type: 'FeatureCollection',
		features: (e?.positions ?? []).map((p) => ({ type: 'Feature', geometry: { type: 'Point', coordinates: p }, properties: {} }))
	};
	const s = map.getSource(ID) as GeoJSONSource | undefined;
	if (s) return s.setData(data);
	map.addSource(ID, { type: 'geojson', data });
	map.addLayer({
		id: ID,
		type: 'circle',
		source: ID,
		paint: { 'circle-radius': 16, 'circle-color': 'rgba(255,200,0,0.25)', 'circle-stroke-color': '#e0a800', 'circle-stroke-width': 3 }
	});
}
