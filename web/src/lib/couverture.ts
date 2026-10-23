// Couverture déduite (décisions de #10) : il n'existe pas de fichier Couverture. Le site la déduit de la
// Couverture déclarée dans `sources.json`, de l'état des sources écrit par le cron et de l'heure courante.
import type { CoucheInscrite } from './registre/types.js';
import type { EtatSource, EtatSources, Plateforme, RaisonNonCouvert, Source } from './schema.js';
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
	/** Les plateformes retenues (section `plateformes` de `sources.json`) : l'ordre et le nom de leurs fiches. */
	plateformes?: readonly Plateforme[];
	maintenant: Date;
}

/**
 * État d'une source, qui vaut pour toutes les communes qu'elle couvre :
 * - `surveillance_interrompue` : le cron n'est pas passé depuis plus de 2 h, l'état lu est périmé ;
 * - `non_surveillee` : la source n'est pas sondée (ni bloc `sonde`, ni site de commune avec son conseil) ;
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

/** Une commune d'une plateforme, dans la liste dépliable de sa fiche. */
export interface CommunePlateforme {
	/** Sa source communale (`site-<n° OFS>`) : le conseil, le niveau et le lien vers le site (attribution). */
	source: Source;
	bfs: number;
	/** `scrape` avec l'état de sa sonde, ou `non_couvert` (sans état) pour une commune non couverte. */
	paire: Paire;
	/** Ce que sa sonde a mesuré, s'il est lisible ; `null` pour une commune non couverte, qui n'est pas sondée. */
	sonde: EtatSource | null;
}

/**
 * La fiche d'une plateforme sur la page `/couverture` (« i-web : 26 communes couvertes, 1 en panne ») : elle tient
 * lieu d'encart aux sources communales, une par commune, qui n'en ont pas.
 */
export interface FichePlateforme {
	id: string;
	nom: string;
	/** Ses communes, dans l'ordre de `sources.json`, couvertes ou non. */
	communes: CommunePlateforme[];
	couvertes: number;
	/** Communes couvertes en panne d'après l'état des sources (aucune tant qu'il est inconnu ou périmé). */
	enPanne: number;
	nonCouvertes: number;
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
	/**
	 * Les sources de la couche qui couvrent la commune, dans l'ordre de la couche. Aucune : celles qui la déclarent
	 * non couverte, avec leur raison (« Non couvert · préavis seuls »), sinon rien (« Non couvert »).
	 */
	cellule(couche: string, bfs: number): Couvrante[];
	/**
	 * Les sources des couches qui ont une Couverture, dans l'ordre du registre, chacune une fois, y compris celles
	 * qui n'en ont pas elles-mêmes (le Grand Conseil, qui porte sur le canton), sauf les sources communales : leurs
	 * communes sont dans la fiche de leur plateforme.
	 */
	sources: SourceCouverte[];
	/**
	 * Une fiche par plateforme qui a au moins une commune déclarée, dans l'ordre de la section `plateformes` ; une
	 * plateforme citée sans y être déclarée vient ensuite, sous son identifiant.
	 */
	plateformes: FichePlateforme[];
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

/**
 * Une source est sondée par le cron si elle a un bloc `sonde`, ou si c'est le site d'une commune qui a un conseil :
 * sa sonde se déduit de sa page de liste et du marqueur de sa variante (une commune non couverte n'en a pas).
 */
export const estSondee = (source: Pick<Source, 'sonde' | 'site' | 'conseil'>): boolean =>
	Boolean(source.sonde || (source.site && source.conseil));

export function deduireCouverture({
	sources,
	etat,
	couches,
	communes,
	plateformes = [],
	maintenant
}: EntreeCouverture): Couverture {
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
		const source = parId.get(id);
		if (!source || !estSondee(source)) return { etat: 'non_surveillee' };
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
	/** Une source qui déclare la commune non couverte (`mode: non_couvert`, avec sa raison). */
	const declareNonCouverte = (id: string, bfs: number) => {
		const c = parId.get(id)?.couverture;
		return c?.mode === 'non_couvert' && c.communes !== 'canton' && c.communes.includes(bfs);
	};
	/** Ce que les sondes ont mesuré pour la source, s'il est lisible, même périmé. */
	const lue = (source: Source) => (estSondee(source) && etat ? (etat.sources[source.id] ?? null) : null);
	const fiches = (): FichePlateforme[] => {
		const communales = sources.filter(
			(s) => s.site && s.couverture && s.couverture.communes !== 'canton' && s.couverture.communes.length > 0
		);
		const declarees = plateformes.map(({ id, nom }) => ({ id, nom }));
		const citees = [...new Set(communales.map((s) => s.site!.plateforme))]
			.filter((id) => !plateformes.some((p) => p.id === id))
			.map((id) => ({ id, nom: id }));
		return [...declarees, ...citees].flatMap(({ id, nom }) => {
			const siennes = communales
				.filter((s) => s.site!.plateforme === id)
				.map((source) => {
					const bfs = (source.couverture!.communes as number[])[0];
					return { source, bfs, paire: paire(source.id, bfs), sonde: lue(source) };
				});
			if (siennes.length === 0) return [];
			const couvertes = siennes.filter((c) => c.paire.mode !== 'non_couvert');
			return [
				{
					id,
					nom,
					communes: siennes,
					couvertes: couvertes.length,
					enPanne: couvertes.filter((c) => c.paire.etat?.etat === 'en_panne').length,
					nonCouvertes: siennes.length - couvertes.length
				}
			];
		});
	};
	return {
		colonnes: avecCouverture.map(({ id, nom }) => ({ id, nom })),
		cellule(id, bfs) {
			const couche = avecCouverture.find((c) => c.id === id);
			const sources = couche ? couvrantes(couche) : [];
			const couvrent = sources
				.map((s) => ({ source: parId.get(s)!, paire: paire(s, bfs) }))
				.filter((c) => c.paire.mode !== 'non_couvert');
			if (couvrent.length > 0) return couvrent;
			return sources
				.filter((s) => declareNonCouverte(s, bfs))
				.map((s) => ({ source: parId.get(s)!, paire: { mode: 'non_couvert' as const, etat: null } }));
		},
		// Une source communale est dans la fiche de sa plateforme, et une source qui ne déclare que des communes non
		// couvertes ne couvre rien : ni l'une ni l'autre n'a d'encart.
		sources: ids
			.map((id) => parId.get(id)!)
			.filter((source) => !source.site && source.couverture?.mode !== 'non_couvert')
			.map((source) => ({
				source,
				communes: communes.filter((c) => mode(source.id, c.bfs) !== 'non_couvert').length,
				etat: etatCouverture(source.id),
				sonde: lue(source)
			})),
		plateformes: fiches(),
		mode,
		etat: etatCouverture,
		paire,
		couvre,
		grisees: (volet) => (volet === null ? [] : communes.filter((c) => !couvre(volet, c.bfs)).map((c) => c.bfs))
	};
}

const MODES: Record<Mode, string> = { api: 'API', scrape: 'Scrapé', non_couvert: 'Non couvert' };

/**
 * Les raisons d'une commune non couverte d'une plateforme retenue (`couverture.raison`), le seul endroit où leurs
 * phrases s'écrivent : celle de la cellule de la Couverture (« Non couvert · préavis seuls ») et celle de l'onglet,
 * qui suit « Non couvert : » (`de` : « de Sainte-Croix », « d’Aigle »).
 */
export const RAISONS: Record<RaisonNonCouvert, { cellule: string; onglet: (de: string) => string }> = {
	preavis_seuls: { cellule: 'préavis seuls', onglet: (de) => `le site ${de} ne publie que des préavis.` },
	rien_en_ligne: {
		cellule: 'rien en ligne',
		onglet: (de) => `le site ${de} ne publie pas les séances de son conseil.`
	},
	demande_commune: {
		cellule: 'à la demande de la commune',
		onglet: (de) => `la commune ${de} a demandé que son site ne soit plus lu.`
	},
	refus_robots: { cellule: 'le site refuse les robots', onglet: (de) => `le site ${de} refuse les robots.` },
	nouveau_site: { cellule: 'nouveau site pas encore lu', onglet: (de) => `le nouveau site ${de} n’est pas encore lu.` }
};

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
 * Les `limites` d'une source (une phrase qui complète « La DGMR publie … »), avec l'apostrophe typographique ;
 * `null` pour une source qui n'en déclare pas.
 */
export const limitesDe = (source: Pick<Source, 'limites'>): string | null =>
	source.limites ? source.limites.replace(/'/g, '’') : null;

/** Ligne Limites d'un encart : « Publie surtout les routes cantonales ; … ». Sinon `null`. */
export function libelleLimites(source: Pick<Source, 'limites'>): string | null {
	const limites = limitesDe(source);
	return limites ? `Publie ${limites}.` : null;
}

/**
 * Libellé d'une cellule du tableau, une ligne par source qui couvre la commune : « API · disponible »,
 * « API · séances seulement · disponible » pour un conseil qui ne donne pas tout, « Non couvert · préavis seuls »
 * pour une commune non couverte d'une plateforme retenue, ou « Non couvert ».
 * Tant que l'état des sources n'est pas chargé (`charge` faux), l'état est remplacé par « … ».
 */
export function libelleCellule(couvrantes: readonly Couvrante[], charge = true): string[] {
	if (couvrantes.length === 0) return [libelleMode('non_couvert')];
	return couvrantes.map(({ source, paire }) => {
		if (paire.mode === 'non_couvert') {
			const raison = source.couverture?.raison;
			return [libelleMode('non_couvert'), raison ? RAISONS[raison].cellule : null].filter(Boolean).join(' · ');
		}
		const donne = source.conseil ? libelleDonne(source.conseil) : null;
		const etat = paire.etat && (charge ? libelleEtat(paire.etat) : '…');
		return [libelleMode(paire.mode), donne === 'objets et séances' ? null : donne, etat].filter(Boolean).join(' · ');
	});
}

const compte = (n: number, un: string, plusieurs: string) => `${n} ${n > 1 ? plusieurs : un}`;

/**
 * Le titre d'une fiche de plateforme : « i-web : 26 communes couvertes, 1 en panne », « aucune en panne », puis
 * les communes non couvertes s'il y en a (« 2 non couvertes »). Tant que l'état des sources n'est pas chargé
 * (`charge` faux), les pannes ne sont pas comptées.
 */
export function libellePlateforme(fiche: FichePlateforme, charge = true): string {
	const parties = [compte(fiche.couvertes, 'commune couverte', 'communes couvertes')];
	if (charge) parties.push(fiche.enPanne ? `${fiche.enPanne} en panne` : 'aucune en panne');
	if (fiche.nonCouvertes) parties.push(compte(fiche.nonCouvertes, 'non couverte', 'non couvertes'));
	return `${fiche.nom} : ${parties.join(', ')}`;
}
