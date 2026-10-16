/*
 * PROTOTYPE (ticket #51), à jeter : les objets et séances RÉELS des trois conseils qu'OpenParlData expose pour Vaud
 * (Grand Conseil, Lausanne, Yverdon), lus directement depuis le navigateur (CORS ouvert), une fois par jour et par
 * onglet du navigateur (sessionStorage). La vraie couche passera par le cron (ADR 0015).
 *
 * Simplifications du prototype : rattachement naïf (nom exact d'une commune ou d'une ancienne commune dans le TITRE
 * d'un objet du Grand Conseil, quelques exclusions seulement, pas le texte des documents) ; pas de masquage des
 * noms de particuliers (ADR 0007) hormis les auteur·e·s des pétitions ; une seule source dans sources.json.
 */
import type { Commune } from '#lib/types.js';

const API = 'https://api.openparldata.ch/v1';

/** Les conseils de la couche : le Grand Conseil (`null`) et les conseils communaux, par slug de commune. */
export const CONSEILS = [
	{ cle: 'VD', commune: null, nom: 'Grand Conseil', donne: 'objets et séances' },
	{ cle: '5586', commune: 'lausanne', nom: 'Conseil communal de Lausanne', donne: 'objets et séances' },
	{ cle: '5938', commune: 'yverdon-les-bains', nom: 'Conseil communal d’Yverdon-les-Bains', donne: 'séances seulement' }
] as const;

/** Le Parlement vaudois, place du Château 6, Lausanne (Cité). */
export const PARLEMENT: [number, number] = [6.63596, 46.52358];

export interface Etape {
	date: string | null;
	titre: string;
}

export interface ElementConseil {
	/** `o-<id OpenParlData>` pour un objet, `s-<id>` pour une séance. */
	id: string;
	opd: number;
	sorte: 'objet' | 'seance';
	/** Conseil communal : le slug de sa commune ; Grand Conseil : `null`. */
	conseil: string | null;
	/** Type brut du conseil (« Interpellation »…) ; « Séance » pour une séance. */
	type: string;
	numero?: string;
	titre: string;
	auteurs: { nom: string; parti?: string }[];
	statut?: string;
	/** AAAA-MM-JJ : dépôt d'un objet, jour d'une séance. */
	date: string;
	/** Il y a combien de jours (négatif : à venir). */
	age: number;
	/** Communes rattachées : celle du conseil, ou celles nommées dans le titre d'un objet du Grand Conseil. */
	communes: string[];
	url?: string;
	etapes?: Etape[];
}

export const conseils = $state({
	elements: [] as ElementConseil[],
	charge: false,
	erreur: null as string | null
});

export const element = (id: string) => conseils.elements.find((x) => x.id === id);

const aujourdHui = () => {
	const d = new Date();
	d.setHours(12, 0, 0, 0);
	return d;
};
const ilYa = (jours: number) => {
	const d = aujourdHui();
	d.setDate(d.getDate() - jours);
	return d.toISOString().slice(0, 10);
};
const age = (date: string) => Math.round((+aujourdHui() - +new Date(`${date}T12:00:00`)) / 86400000);

export function dateDe(x: ElementConseil): Date {
	return new Date(`${x.date}T12:00:00`);
}

export const nomConseil = (x: Pick<ElementConseil, 'conseil'>) =>
	CONSEILS.find((c) => c.commune === x.conseil)?.nom ?? 'Conseil communal';

/* ---- Lecture ---- */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Brut = any;
const fr = (t: Brut): string => t?.fr ?? t?.de ?? '';

/** Les étapes d'OpenParlData n'ont parfois qu'un libellé allemand (harmonisé). */
const ETAPES_DE: Record<string, string> = {
	Eingereicht: 'Déposé',
	Traktandiert: 'Inscrit à l’ordre du jour',
	Überwiesen: 'Renvoyé',
	'Behandelt vom Parlament': 'Traité par le conseil',
	Erledigt: 'Liquidé',
	Abgeschrieben: 'Classé',
	Beantwortet: 'Répondu'
};
const etape = (e: Brut): Etape => ({
	date: e.date ? String(e.date).slice(0, 10) : null,
	titre: e.title?.fr ?? ETAPES_DE[e.title?.de] ?? e.title?.de ?? '?'
});

async function lire(chemin: string): Promise<Brut[]> {
	const r = await fetch(`${API}${chemin}`);
	if (!r.ok) throw new Error(`${r.status} ${chemin}`);
	return (await r.json()).data;
}
const pause = (ms: number) => new Promise((r) => setTimeout(r, ms));

/* ---- Rattachement naïf par le nom ---- */

const echapper = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
/** Faux positifs connus (#47) : « Mur » et « Premier » pris pour des communes. */
const BANNIS = new Set(['Mur', 'Premier']);

function rattacheur(communes: readonly Commune[]) {
	const noms: { re: RegExp; slug: string }[] = [];
	for (const c of communes) {
		for (const nom of [c.nom, ...c.anciens.map((a) => a.nom)]) {
			if (BANNIS.has(nom)) continue;
			noms.push({ re: new RegExp(`(?<![\\p{L}\\-])${echapper(nom)}(?![\\p{L}\\-])`, 'u'), slug: c.slug });
		}
	}
	return (titre: string): string[] => {
		// Contextes exclus (ADR 0016), en très bref : districts, la rivière Orbe.
		const t = titre.replace(/district (de |d’|d')[\p{L}\- ]+/giu, '').replace(/(l’|l')Orbe/gi, '');
		const trouves: { slug: string; i: number }[] = [];
		for (const n of noms) {
			const m = n.re.exec(t);
			if (m && !trouves.some((x) => x.slug === n.slug)) trouves.push({ slug: n.slug, i: m.index });
		}
		return trouves.sort((a, b) => a.i - b.i).map((x) => x.slug);
	};
}

/* ---- Chargement ---- */

function objet(a: Brut, conseil: string | null, rattacher: (t: string) => string[]): ElementConseil {
	const titre = fr(a.title);
	const type = fr(a.type_name) || 'Objet';
	const etapes: Etape[] | undefined = a.events?.data?.map(etape);
	const date = String(a.begin_date).slice(0, 10);
	return {
		id: `o-${a.id}`,
		opd: a.id,
		sorte: 'objet',
		conseil,
		type,
		numero: a.number ?? undefined,
		titre,
		// Pétitions : les pétitionnaires sont des particuliers, sans auteur·e affiché·e (#49).
		auteurs: /pétition/i.test(type)
			? []
			: (a.contributors?.data ?? [])
					.filter((c: Brut) => c.type === 'person' || c.fullname)
					.map((c: Brut) => ({ nom: c.fullname, parti: fr(c.party) || undefined })),
		// Statut : `state_name`, sinon la dernière étape (#49).
		statut: fr(a.state_name) || (etapes?.length ? etapes.at(-1)!.titre : undefined),
		date,
		age: age(date),
		communes: conseil ? [conseil] : rattacher(titre),
		url: fr(a.url_external) || undefined,
		etapes
	};
}

function seance(m: Brut, conseil: string | null): ElementConseil {
	const date = String(m.begin_date).slice(0, 10);
	return {
		id: `s-${m.id}`,
		opd: m.id,
		sorte: 'seance',
		conseil,
		type: 'Séance',
		titre: fr(m.name).replace(/ (\d{4}) \1/, ' $1'),
		auteurs: [],
		date,
		age: age(date),
		communes: conseil ? [conseil] : [],
		url: fr(m.url_external) || undefined
	};
}

let enCours: Promise<void> | null = null;

/** Charge les trois conseils une fois ; les appels suivants attendent le même chargement. */
export function charger(communes: readonly Commune[]): Promise<void> {
	return (enCours ??= (async () => {
		const cle = `prototype-conseils-${ilYa(0)}`;
		try {
			const cache = sessionStorage.getItem(cle);
			if (cache) {
				conseils.elements = JSON.parse(cache);
				conseils.charge = true;
				return;
			}
		} catch {
			/* pas de sessionStorage : on lit l'API */
		}
		try {
			const rattacher = rattacheur(communes);
			const xs: ElementConseil[] = [];
			const gc = await lire(`/affairs/?body_key=VD&from_begin_date=${ilYa(150)}&sort_by=-begin_date&limit=400&expand=contributors`);
			xs.push(...gc.filter((a) => !/grâce/i.test(fr(a.type_name))).map((a) => objet(a, null, rattacher)));
			await pause(400);
			const lau = await lire(`/affairs/?body_key=5586&from_begin_date=${ilYa(200)}&sort_by=-begin_date&limit=200&expand=contributors,events`);
			xs.push(...lau.map((a) => objet(a, 'lausanne', rattacher)));
			await pause(400);
			// Grand Conseil : ses séances seulement, pas celles du Conseil d'État (group_id 3726).
			const sgc = await lire(`/meetings/?body_key=VD&group_id=1965&from_begin_date=${ilYa(150)}&sort_by=-begin_date&limit=40`);
			xs.push(...sgc.map((m) => seance(m, null)));
			await pause(400);
			const slau = await lire(`/meetings/?body_key=5586&from_begin_date=${ilYa(200)}&sort_by=-begin_date&limit=30`);
			xs.push(...slau.map((m) => seance(m, 'lausanne')));
			await pause(400);
			const syve = await lire(`/meetings/?body_key=5938&from_begin_date=${ilYa(365)}&sort_by=-begin_date&limit=30`);
			xs.push(...syve.map((m) => seance(m, 'yverdon-les-bains')));
			conseils.elements = xs;
			conseils.charge = true;
			try {
				sessionStorage.setItem(cle, JSON.stringify(xs));
			} catch {
				/* tant pis */
			}
		} catch (e) {
			conseils.erreur = String(e);
			enCours = null;
		}
	})());
}

/* ---- Détails, lus à l'ouverture d'un élément ---- */

export interface Document {
	nom: string;
	url: string;
	date: string | null;
	categorie: string;
}
export interface Point {
	numero: string;
	titre: string;
	categorie?: string;
	resultat?: string;
	/** L'objet du point, quand il est parmi les objets chargés. */
	objet?: string;
}
export interface Details {
	etapes: Etape[];
	documents: Document[];
	ordreDuJour: Point[];
}

const details = new Map<string, Promise<Details>>();

export function detailsDe(x: ElementConseil): Promise<Details> {
	let p = details.get(x.id);
	if (!p) {
		p = (async (): Promise<Details> => {
			if (x.sorte === 'seance') {
				const pts = await lire(`/meetings/${x.opd}/agendas/?limit=300`);
				return {
					etapes: [],
					documents: [],
					ordreDuJour: pts
						.sort((a, b) => (a.item_number ?? 0) - (b.item_number ?? 0))
						.map((p) => {
							const o = conseils.elements.find(
								(y) => y.sorte === 'objet' && y.conseil === x.conseil && ((p.item_affair_number && y.numero === p.item_affair_number) || (p.item_affair_id && y.opd === p.item_affair_id))
							);
							return {
								numero: p.item_number_display ?? String(p.item_number ?? ''),
								titre: p.item_title ?? '',
								categorie: p.item_category ?? undefined,
								resultat: p.item_result ?? undefined,
								objet: o?.id
							};
						})
				};
			}
			const [ev, docs] = await Promise.all([
				x.etapes ? Promise.resolve(null) : lire(`/affairs/${x.opd}/events/?limit=50`),
				lire(`/affairs/${x.opd}/docs/?limit=30&fields=id,name,url,date,category,format`)
			]);
			return {
				etapes: x.etapes ?? (ev ?? []).map(etape),
				documents: docs.map((d) => ({ nom: d.name ?? 'Document', url: d.url, date: d.date ? String(d.date).slice(0, 10) : null, categorie: fr(d.category) })),
				ordreDuJour: []
			};
		})();
		details.set(x.id, p);
		p.catch(() => details.delete(x.id));
	}
	return p;
}

/* ---- Requêtes communes aux variantes ---- */

const recentsDabord = (a: ElementConseil, b: ElementConseil) => a.age - b.age;

/** Les éléments du conseil communal d'une commune. */
export const duConseil = (slug: string | null) => conseils.elements.filter((x) => x.conseil === slug);

export function seancesDe(slug: string | null) {
	const xs = duConseil(slug).filter((x) => x.sorte === 'seance');
	return {
		avenir: xs.filter((x) => x.age < 0).sort((a, b) => b.age - a.age),
		passees: xs.filter((x) => x.age >= 0).sort(recentsDabord)
	};
}

export const objetsDe = (slug: string | null) => duConseil(slug).filter((x) => x.sorte === 'objet').sort(recentsDabord);

/** Les objets du Grand Conseil rattachés à une commune, les plus récents d'abord. */
export const auGrandConseil = (slug: string) =>
	conseils.elements.filter((x) => x.conseil === null && x.sorte === 'objet' && x.communes.includes(slug)).sort(recentsDabord);

/** Nombre d'objets d'une commune (son conseil, plus le Grand Conseil qui la nomme) ces `jours` derniers jours. */
export function activite(jours: number) {
	const n = new Map<string, { communal: number; gc: number; seances: number }>();
	for (const x of conseils.elements) {
		if (x.age < 0 || x.age > jours) continue;
		for (const s of x.communes) {
			const v = n.get(s) ?? { communal: 0, gc: 0, seances: 0 };
			if (x.sorte === 'seance') v.seances++;
			else if (x.conseil === null) v.gc++;
			else v.communal++;
			n.set(s, v);
		}
	}
	return n;
}

export const jourLong = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
export const jourCourt = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short' });
export const jourSemaine = new Intl.DateTimeFormat('fr-CH', { weekday: 'short', day: 'numeric', month: 'short' });
