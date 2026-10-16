// Couverture déduite (décisions de #10) : il n'existe pas de fichier Couverture. Le site la déduit de la
// Couverture déclarée dans `sources.json`, de l'état des sources écrit par le cron et de l'heure courante.
import type { CoucheInscrite } from './registre/types.js';
import type { EtatSource, EtatSources, Source } from './schema.js';
import { libelleDonne } from './sources.js';

/** Mode d'une paire (source, commune), connu à la construction. */
export type Mode = 'api' | 'scrape' | 'non_couvert';

export interface EntreeCouverture {
	/** Sources déclarées dans `sources.json`. */
	sources: readonly Source[];
	/** État des sources lu dans le dépôt de données ; `null` s'il est inaccessible ou d'une version inconnue. */
	etat: EtatSources | null;
	/** Couches du registre. */
	couches: readonly CoucheInscrite[];
	/** Les communes actuelles (n° OFS). */
	communes: readonly { bfs: number }[];
	maintenant: Date;
}

/**
 * État d'une source, qui vaut pour toutes les communes qu'elle couvre :
 * - `surveillance_interrompue` : le cron n'est pas passé depuis plus de 2 h, l'état lu est périmé ;
 * - `non_surveillee` : la source n'a pas de bloc `sonde` ;
 * - `inconnu` : l'état des sources est inaccessible, d'une version inconnue, ou ne cite pas la source.
 */
export type EtatCouverture =
	| { etat: 'disponible' }
	| { etat: 'en_panne'; depuis: string | null }
	| { etat: 'surveillance_interrompue' }
	| { etat: 'non_surveillee' }
	| { etat: 'inconnu' };

/** Au-delà, le dernier passage du cron est trop ancien pour qu'on lise son état comme actuel. */
const INTERRUPTION = 2 * 3600_000;

/** Les deux axes d'une paire (source, commune) ; l'état n'est donné que si la commune est couverte. */
export interface Paire {
	mode: Mode;
	etat: EtatCouverture | null;
}

/** Une source qui a une Couverture, telle que la montre la page `/couverture`. */
export interface SourceCouverte {
	source: Source;
	/** Nombre de communes couvertes. */
	communes: number;
	etat: EtatCouverture;
	/** Ce que les sondes ont mesuré, s'il est lisible, même périmé (dernière sonde et dernier succès). */
	sonde: EtatSource | null;
}

/** Une colonne du tableau de la page `/couverture` : une couche qui a une Couverture. */
export interface ColonneCouverture {
	id: string;
	nom: string;
}

/** Une source qui couvre la commune, dans une cellule du tableau, avec sa paire. */
export interface Couvrante {
	source: Source;
	paire: Paire;
}

export interface Couverture {
	/** Les couches qui ont une Couverture, dans l'ordre du registre : les colonnes du tableau des communes. */
	colonnes: ColonneCouverture[];
	/** Les sources de la couche qui couvrent la commune, dans l'ordre de la couche ; aucune : « Non couvert ». */
	cellule(couche: string, bfs: number): Couvrante[];
	/**
	 * Les sources des couches qui ont une Couverture, dans l'ordre du registre, chacune une fois, y compris celles
	 * qui n'en ont pas elles-mêmes (le Grand Conseil, qui porte sur le canton).
	 */
	sources: SourceCouverte[];
	mode(source: string, bfs: number): Mode;
	etat(source: string): EtatCouverture;
	paire(source: string, bfs: number): Paire;
	/**
	 * Une couche couvre une commune dès qu'une de ses sources la couvre : sa Couverture est l'union de celles de ses
	 * sources. Une couche dont aucune source n'a de Couverture couvre toutes les communes et n'en grise aucune.
	 */
	couvre(couche: string, bfs: number): boolean;
	/**
	 * Communes grisées sur la carte (bureau) quand le volet de cette couche est ouvert : celles qu'elle ne couvre
	 * pas. Sans volet ouvert, aucune. Une panne ne grise rien : seul le mode compte, jamais l'état.
	 */
	grisees(volet: string | null): number[];
}

export function deduireCouverture({ sources, etat, couches, communes, maintenant }: EntreeCouverture): Couverture {
	const parId = new Map(sources.map((s) => [s.id, s]));
	const mode = (id: string, bfs: number): Mode => {
		// Une source sans Couverture (le Grand Conseil, qui porte sur le canton) ne couvre aucune commune.
		const couverture = parId.get(id)?.couverture;
		if (!couverture) return 'non_couvert';
		const { communes, mode } = couverture;
		return communes === 'canton' || communes.includes(bfs) ? mode : 'non_couvert';
	};
	const interrompue = etat !== null && maintenant.getTime() - Date.parse(etat.genere) > INTERRUPTION;
	const etatCouverture = (id: string): EtatCouverture => {
		if (!parId.get(id)?.sonde) return { etat: 'non_surveillee' };
		if (!etat) return { etat: 'inconnu' };
		if (interrompue) return { etat: 'surveillance_interrompue' };
		const lu = etat.sources[id];
		if (!lu) return { etat: 'inconnu' };
		return lu.etat === 'en_panne' ? { etat: 'en_panne', depuis: lu.depuis } : { etat: 'disponible' };
	};
	/** Les sources de la couche qui ont une Couverture : celle de la couche est leur union. */
	const couvrantes = (c: CoucheInscrite) => c.sources.filter((s) => parId.get(s)?.couverture);
	// Une couche dont aucune source n'a de Couverture couvre toutes les communes : elle n'a pas de Couverture.
	const avecCouverture = couches.filter((c) => couvrantes(c).length > 0);
	const ids = [...new Set(avecCouverture.flatMap((c) => c.sources))].filter((id) => parId.has(id));
	const couvre = (id: string, bfs: number) => {
		const couche = avecCouverture.find((c) => c.id === id);
		return !couche || couvrantes(couche).some((s) => mode(s, bfs) !== 'non_couvert');
	};
	const paire = (id: string, bfs: number): Paire => {
		const m = mode(id, bfs);
		return { mode: m, etat: m === 'non_couvert' ? null : etatCouverture(id) };
	};
	return {
		colonnes: avecCouverture.map(({ id, nom }) => ({ id, nom })),
		cellule(id, bfs) {
			const couche = avecCouverture.find((c) => c.id === id);
			return (couche ? couvrantes(couche) : [])
				.map((s) => ({ source: parId.get(s)!, paire: paire(s, bfs) }))
				.filter((c) => c.paire.mode !== 'non_couvert');
		},
		sources: ids.map((id) => {
			const source = parId.get(id)!;
			const e = etatCouverture(id);
			const lu = source.sonde && etat ? (etat.sources[id] ?? null) : null;
			return {
				source,
				communes: communes.filter((c) => mode(id, c.bfs) !== 'non_couvert').length,
				etat: e,
				sonde: lu
			};
		}),
		mode,
		etat: etatCouverture,
		paire,
		couvre,
		grisees: (volet) => (volet === null ? [] : communes.filter((c) => !couvre(volet, c.bfs)).map((c) => c.bfs))
	};
}

const MODES: Record<Mode, string> = { api: 'API', scrape: 'Scrapé', non_couvert: 'Non couvert' };

const jour = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short', timeZone: 'Europe/Zurich' });
const heure = new Intl.DateTimeFormat('fr-CH', { hour: 'numeric', minute: '2-digit', timeZone: 'Europe/Zurich' });

/** Un instant à l'heure de Lausanne, à la minute : « 12 oct., 14 h », « 1 déc., 8 h 47 ». */
export function dateHeure(iso: string): string {
	const d = new Date(iso);
	const [h, m] = heure.format(d).split(':').map(Number);
	return `${jour.format(d)}, ${h} h${m ? ` ${String(m).padStart(2, '0')}` : ''}`;
}

/** Libellé du mode : « API », « Scrapé » ou « Non couvert ». */
export const libelleMode = (mode: Mode) => MODES[mode];

/** Libellé de l'état : « disponible », « en panne depuis le 12 oct., 14 h », « surveillance interrompue »… */
export function libelleEtat(e: EtatCouverture): string {
	switch (e.etat) {
		case 'disponible':
			return 'disponible';
		case 'en_panne':
			return e.depuis ? `en panne depuis le ${dateHeure(e.depuis)}` : 'en panne';
		case 'surveillance_interrompue':
			return 'surveillance interrompue';
		case 'non_surveillee':
			return 'non surveillée';
		case 'inconnu':
			return 'inconnu';
	}
}

/** Libellé d'une paire : « API · disponible », « Scrapé · en panne depuis le 12 oct., 14 h », « Non couvert ». */
export const libellePaire = ({ mode, etat }: Paire) =>
	etat ? `${libelleMode(mode)} · ${libelleEtat(etat)}` : libelleMode(mode);

/** Ligne Communes d'un encart : « Porte sur le canton » sans Couverture, sinon « 1 commune sur 300 »… */
export function libelleCommunes({ source, communes }: SourceCouverte, total: number): string {
	if (!source.couverture) return 'Porte sur le canton';
	return `${communes} ${communes > 1 ? 'communes' : 'commune'} sur ${total}`;
}

/**
 * Libellé d'une cellule du tableau, une ligne par source qui couvre la commune : « API · disponible »,
 * « API · séances seulement · disponible » pour un conseil qui ne donne pas tout, ou « Non couvert ».
 * Tant que l'état des sources n'est pas chargé (`charge` faux), l'état est remplacé par « … ».
 */
export function libelleCellule(couvrantes: readonly Couvrante[], charge = true): string[] {
	if (couvrantes.length === 0) return [libelleMode('non_couvert')];
	return couvrantes.map(({ source, paire }) => {
		const donne = source.conseil ? libelleDonne(source.conseil) : null;
		const etat = paire.etat && (charge ? libelleEtat(paire.etat) : '…');
		return [libelleMode(paire.mode), donne === 'objets et séances' ? null : donne, etat].filter(Boolean).join(' · ');
	});
}
