/*
 * PROTOTYPE (ticket « Couche Routes sur la carte, volet et onglet Routes ») : à jeter. Restrictions de circulation
 * de la DGMR lues en direct (couches 596 en cours et 595 à venir), rattachées aux communes par leur position
 * (≥ 20 m parcourus, sinon la plus grande part), rangées par longueur. Aucun test, aucune reprise sur erreur.
 */
import { inscrireEtat } from '#lib/fraicheur.js';
import { getLimites, type Limites } from '#lib/socle/communes.js';
import type { Commune, Emprise, Zone } from '#lib/types.js';

const BASE = 'https://www.ogc.vd.ch/public/rest/services/OGC/wmsVD/MapServer';

export type Sorte = 'fermeture' | 'deviation' | 'feux' | 'particuliere' | 'autre';
export type Quand = 'en-cours' | 'a-venir';
export type Variante = 'A' | 'B' | 'C';

export const SORTES: Record<Sorte, { nom: string; pluriel: string; couleur: string }> = {
	fermeture: { nom: 'Fermeture', pluriel: 'Fermetures', couleur: '#c92a2a' },
	deviation: { nom: 'Déviation', pluriel: 'Déviations', couleur: '#e8590c' },
	feux: { nom: 'Feux', pluriel: 'Feux', couleur: '#e0a800' },
	particuliere: { nom: 'Restriction particulière', pluriel: 'Restrictions particulières', couleur: '#7048e8' },
	autre: { nom: 'Autre', pluriel: 'Autres', couleur: '#868e96' }
};
export const SORTES_ORDRE: Sorte[] = ['fermeture', 'deviation', 'feux', 'particuliere', 'autre'];

const SORTE: Record<string, Sorte> = {
	Fermeture: 'fermeture',
	Déviation: 'deviation',
	Feux: 'feux',
	'Restriction particulière': 'particuliere'
};

/** Un instant de la source : jour AAAA-MM-JJ, et l'heure locale si elle n'est pas minuit. */
export interface Instant {
	jour: string;
	heure: string | null;
}

export interface Passage {
	commune: Commune;
	metres: number;
}

export interface Restriction {
	id: number;
	sorte: Sorte;
	quand: Quand;
	/** NOM de la source (« Moudon, Sorbiers E2 »). */
	nom: string;
	rhrc: string | null;
	debut: Instant;
	fin: Instant;
	/** Plage quotidienne (HEURE_DEBUT – HEURE_FIN), seulement pour les fermetures de nuit. */
	plage: [string, string] | null;
	weekEnd: boolean | null;
	travaux: string | null;
	entite: string | null;
	remarque: string | null;
	lignes: [number, number][][];
	longueur: number;
	/** Communes traversées, de la plus longue à la plus courte. */
	communes: Passage[];
	milieu: [number, number];
	emprise: Emprise;
	/** RHRC + NOM : les restrictions d'une même intervention (fermeture et sa déviation). */
	groupe: string;
}

/** Les restrictions d'une même intervention : RHRC + NOM. */
export interface Groupe {
	cle: string;
	nom: string;
	rhrc: string | null;
	restrictions: Restriction[];
	/** La restriction « principale » : tout sauf une déviation, sinon la première. */
	principale: Restriction;
	quand: Quand;
	debut: Instant;
	fin: Instant;
	communes: Passage[];
}

const instant = (ms: number): Instant => {
	const iso = new Date(ms).toISOString();
	const heure = iso.slice(11, 16);
	return { jour: iso.slice(0, 10), heure: heure === '00:00' ? null : heure };
};
const texte = (v: unknown) => (v == null || String(v).trim() === '' ? null : String(v).trim());

/* ---- Géométrie ---- */

const R = 6371000;
function metres([a, b]: [number, number], [c, d]: [number, number]) {
	const k = Math.cos(((b + d) / 2) * (Math.PI / 180));
	return Math.hypot((c - a) * k, d - b) * (Math.PI / 180) * R;
}

function dansAnneau(lon: number, lat: number, anneau: number[][]): boolean {
	let dedans = false;
	for (let i = 0, j = anneau.length - 1; i < anneau.length; j = i++) {
		const [xi, yi] = anneau[i];
		const [xj, yj] = anneau[j];
		if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) dedans = !dedans;
	}
	return dedans;
}
const dansLimites = (lon: number, lat: number, l: Limites) =>
	l.some(([ext, ...trous]) => dansAnneau(lon, lat, ext) && !trous.some((t) => dansAnneau(lon, lat, t)));
const dansEmprise = (lon: number, lat: number, [o, s, e, n]: Emprise) => lon >= o && lon <= e && lat >= s && lat <= n;

/** Échantillonne la ligne tous les 10 m, et compte les mètres parcourus dans chaque commune. */
function passages(lignes: [number, number][][], communes: readonly Commune[], limites: Record<string, Limites>) {
	const parBfs = new Map<number, number>();
	let derniere: Commune | null = null;
	const communeDe = (lon: number, lat: number) => {
		if (derniere && dansLimites(lon, lat, limites[derniere.bfs] ?? [])) return derniere;
		derniere =
			communes.find((c) => dansEmprise(lon, lat, c.bbox) && dansLimites(lon, lat, limites[c.bfs] ?? [])) ?? null;
		return derniere;
	};
	for (const ligne of lignes)
		for (let i = 1; i < ligne.length; i++) {
			const [a, b] = [ligne[i - 1], ligne[i]];
			const d = metres(a, b);
			const n = Math.max(1, Math.round(d / 10));
			for (let k = 0; k < n; k++) {
				const t = (k + 0.5) / n;
				const c = communeDe(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t);
				if (c) parBfs.set(c.bfs, (parBfs.get(c.bfs) ?? 0) + d / n);
			}
		}
	const tous = [...parBfs].map(([bfs, m]) => ({ commune: communes.find((c) => c.bfs === bfs)!, metres: m }));
	tous.sort((x, y) => y.metres - x.metres);
	const retenus = tous.filter((p) => p.metres >= 20);
	return retenus.length ? retenus : tous.slice(0, 1);
}

function milieu(lignes: [number, number][][], longueur: number): [number, number] {
	let reste = longueur / 2;
	for (const l of lignes)
		for (let i = 1; i < l.length; i++) {
			const d = metres(l[i - 1], l[i]);
			if (d >= reste) {
				const t = reste / d;
				return [l[i - 1][0] + (l[i][0] - l[i - 1][0]) * t, l[i - 1][1] + (l[i][1] - l[i - 1][1]) * t];
			}
			reste -= d;
		}
	return lignes[0][0];
}

/* ---- Chargement ---- */

interface Feature {
	properties: Record<string, string | number | null>;
	geometry: { type: 'LineString'; coordinates: [number, number][] } | { type: 'MultiLineString'; coordinates: [number, number][][] };
}

async function couche(n: 595 | 596): Promise<Feature[]> {
	const r = await fetch(`${BASE}/${n}/query?where=1%3D1&outFields=*&outSR=4326&f=geojson`);
	if (!r.ok) throw new Error(`DGMR ${n} : ${r.status}`);
	return (await r.json()).features;
}

function versRestriction(f: Feature, quand: Quand, communes: readonly Commune[], limites: Record<string, Limites>): Restriction {
	const p = f.properties;
	const lignes = f.geometry.type === 'LineString' ? [f.geometry.coordinates] : f.geometry.coordinates;
	const longueur = lignes.reduce((s, l) => s + l.slice(1).reduce((t, pt, i) => t + metres(l[i], pt), 0), 0);
	const xs = lignes.flat().map((c) => c[0]);
	const ys = lignes.flat().map((c) => c[1]);
	const hd = texte(p.HEURE_DEBUT);
	const hf = texte(p.HEURE_FIN);
	const we = texte(p.WEEK_END)?.toLowerCase();
	return {
		id: Number(p.OBJECTID),
		sorte: SORTE[String(p.RESTRICTION)] ?? 'autre',
		quand,
		nom: texte(p.NOM) ?? 'Sans nom',
		rhrc: texte(p.RHRC),
		debut: instant(Number(p.DATE_DEBUT)),
		fin: instant(Number(p.DATE_FIN)),
		plage: hd && hf ? [hd, hf] : null,
		weekEnd: we === 'oui' ? true : we === 'non' ? false : null,
		travaux: texte(p.TYPE),
		entite: texte(p.ENTITE),
		remarque: texte(p.REMARQUE),
		lignes,
		longueur,
		communes: passages(lignes, communes, limites),
		milieu: milieu(lignes, longueur),
		emprise: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
		groupe: `${texte(p.RHRC) ?? ''}|${texte(p.NOM) ?? ''}`
	};
}

function grouper(rs: Restriction[]): Groupe[] {
	const parCle = new Map<string, Restriction[]>();
	for (const r of rs) parCle.set(r.groupe, [...(parCle.get(r.groupe) ?? []), r]);
	return [...parCle].map(([cle, membres]) => {
		membres.sort((a, b) => SORTES_ORDRE.indexOf(a.sorte) - SORTES_ORDRE.indexOf(b.sorte));
		const principale = membres.find((r) => r.sorte !== 'deviation') ?? membres[0];
		const debut = membres.map((r) => r.debut).sort((a, b) => cmp(a, b))[0];
		const fin = membres.map((r) => r.fin).sort((a, b) => cmp(b, a))[0];
		const m = new Map<number, Passage>();
		// Communes de la principale d'abord, puis celles que seules les déviations traversent.
		for (const r of [principale, ...membres.filter((x) => x !== principale)])
			for (const p of r.communes) if (!m.has(p.commune.bfs)) m.set(p.commune.bfs, p);
		return {
			cle,
			nom: principale.nom,
			rhrc: principale.rhrc,
			restrictions: membres,
			principale,
			quand: membres.some((r) => r.quand === 'en-cours') ? 'en-cours' : 'a-venir',
			debut,
			fin,
			communes: [...m.values()]
		};
	});
}

const cmp = (a: Instant, b: Instant) => `${a.jour} ${a.heure ?? ''}`.localeCompare(`${b.jour} ${b.heure ?? ''}`);
export const parDebut = <T extends { debut: Instant }>(a: T, b: T) => cmp(a.debut, b.debut);

/* ---- État partagé par les composants ---- */

class Routes {
	restrictions = $state.raw<Restriction[]>([]);
	groupes = $state.raw<Groupe[]>([]);
	charge = $state(false);
	erreur = $state<string | null>(null);
	/** Réglages des volets (hors de l'adresse : prototype). */
	sortes = $state<Sorte[]>([...SORTES_ORDRE]);
	quand = $state<Quand[]>(['en-cours', 'a-venir']);
	/** Variante C : horizon en jours (0 : aujourd'hui seulement, null : tout). */
	horizon = $state<number | null>(null);
	/** Variante B : groupe survolé dans la liste ou sur la carte. */
	survol = $state<string | null>(null);
	private promesse: Promise<Restriction[]> | null = null;
	private derniere: Date | null = null;

	charger(communes: readonly Commune[]): Promise<Restriction[]> {
		this.promesse ??= (async () => {
			try {
				const [enCours, aVenir, limites] = await Promise.all([couche(596), couche(595), getLimites(fetch)]);
				const rs = [
					...enCours.map((f) => versRestriction(f, 'en-cours', communes, limites)),
					...aVenir.map((f) => versRestriction(f, 'a-venir', communes, limites))
				];
				this.restrictions = rs;
				this.groupes = grouper(rs);
				this.charge = true;
				this.derniere = new Date();
				inscrireEtat('dgmr-restrictions', { derniere: this.derniere, erreur: null, recharger() {} });
				return rs;
			} catch (e) {
				this.erreur = String(e);
				this.promesse = null;
				throw e;
			}
		})();
		return this.promesse;
	}

	restriction(id: number) {
		return this.restrictions.find((r) => r.id === id);
	}
	groupeDe(r: Restriction) {
		return this.groupes.find((g) => g.cle === r.groupe)!;
	}
}

export const routes = new Routes();

/** Jour AAAA-MM-JJ d'aujourd'hui, en heure locale. */
export const aujourdhui = () => {
	const d = new Date();
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
export const plusJours = (jour: string, n: number) => {
	const d = new Date(`${jour}T12:00:00Z`);
	d.setUTCDate(d.getUTCDate() + n);
	return d.toISOString().slice(0, 10);
};
export const joursEntre = (a: string, b: string) =>
	Math.round((Date.parse(`${b}T12:00:00Z`) - Date.parse(`${a}T12:00:00Z`)) / 86400000);

export const visible = (r: Restriction, zone: Zone | null) => {
	if (!zone) return true;
	const [o, s, e, n] = zone;
	const [ro, rs, re, rn] = r.emprise;
	return ro <= e && re >= o && rs <= n && rn >= s;
};

/** La restriction passe les réglages du volet de la variante. */
export function retenue(r: Restriction, v: Variante): boolean {
	if (v === 'C') {
		if (routes.horizon === null) return true;
		const j = aujourdhui();
		return r.debut.jour <= plusJours(j, routes.horizon);
	}
	return routes.sortes.includes(r.sorte) && routes.quand.includes(r.quand);
}

/* ---- Textes ---- */

const fmtJour = new Intl.DateTimeFormat('fr-CH', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
const fmtLong = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
const jourD = (j: string) => new Date(`${j}T12:00:00Z`);
export const jourCourt = (j: string) => fmtJour.format(jourD(j));
export const jourLong = (j: string) => fmtLong.format(jourD(j));
const h = (s: string) => s.replace(/^0(\d)/, '$1').replace(':', ' h ').replace(/ h 00$/, ' h');
export const heure = (i: Instant) => (i.heure ? h(i.heure) : null);
export const plageTexte = (p: [string, string]) => `de ${h(p[0])} à ${h(p[1])}`;

/** « Du lun. 12 oct. à 7 h au lun. 19 oct. à 7 h ». */
export function periode(r: { debut: Instant; fin: Instant }, long = false): string {
	const f = long ? jourLong : jourCourt;
	const a = `${f(r.debut.jour)}${r.debut.heure ? ` à ${h(r.debut.heure)}` : ''}`;
	const b = `${f(r.fin.jour)}${r.fin.heure ? ` à ${h(r.fin.heure)}` : ''}`;
	return `Du ${a} au ${b}`;
}

/** « depuis 3 jours », « dans 5 jours », « encore 12 jours ». */
export function echeance(r: { quand: Quand; debut: Instant; fin: Instant }): string {
	const j = aujourdhui();
	if (r.quand === 'a-venir') {
		const n = joursEntre(j, r.debut.jour);
		return n <= 0 ? 'commence aujourd’hui' : n === 1 ? 'commence demain' : `commence dans ${n} jours`;
	}
	const n = joursEntre(j, r.fin.jour);
	return n <= 0 ? 'se termine aujourd’hui' : n === 1 ? 'jusqu’à demain' : `encore ${n} jours`;
}

export const longueurTexte = (m: number) => (m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(1).replace('.', ',')} km`);

export const communesTexte = (ps: Passage[], max = 3) =>
	ps.length <= max ? ps.map((p) => p.commune.nom).join(', ') : `${ps.slice(0, max).map((p) => p.commune.nom).join(', ')} et ${ps.length - max} autres`;

const RESEAUX: Record<string, string> = { B: 'réseau de base', C: 'réseau complémentaire', IL: 'intérêt local' };
/** « 626-B-P » → « Route cantonale 626 (réseau de base, principale) ». */
export function rhrcTexte(rhrc: string | null): string | null {
	const m = rhrc?.match(/^(\d+)\s*-\s*(B|C|IL)\s*-\s*(P|S)$/);
	if (!m) return rhrc;
	return `Route cantonale ${m[1]} (${RESEAUX[m[2]]}, ${m[3] === 'P' ? 'principale' : 'secondaire'})`;
}

/** La portée de la source, dite en tête ou au pied de l'onglet Routes. */
export const PORTEE =
	'La DGMR publie les restrictions de circulation des routes cantonales. Celles des routes communales n’y figurent pas toujours : renseignez-vous aussi auprès de la commune.';

/** Mètres parcourus dans une commune par la restriction. */
export const metresDans = (r: Restriction, slug: string) => r.communes.find((p) => p.commune.slug === slug)?.metres ?? 0;
