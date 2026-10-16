// Module de données de la couche Conseils, partagé par ses composants : il lit les fichiers que le cron publie sur
// les Pages du dépôt de données (fichiers de lecture et archive, ADR 0015). Le site n'y vérifie que `version` : le
// contenu est valide au JSON Schema dès l'écriture, côté cron.
import { DONNEES } from '#lib/config.js';
import type { ConseilIndexe, IndexConseils, LigneObjet, ListeObjets, ListeSeances, Seance } from '#lib/schema.js';

/** Seule version des fichiers des conseils que le site connaît. */
export const VERSION_CONSEILS = 1;

/** Objets récents montrés d'emblée dans l'onglet Conseil : on lit des années jusqu'à en avoir autant. */
export const OBJETS_RECENTS = 8;

/** Les Objets d'un conseil chargés jusqu'ici, année par année, du plus récent au plus ancien. */
export interface PageObjets {
	objets: LigneObjet[];
	/** L'année que lirait `objetsSuivants`, ou `null` quand toutes les années sont lues. */
	suivante: number | null;
}

export interface DonneesConseils {
	/**
	 * `conseils/index.json` : les conseils couverts, dans l'ordre de `sources.json`, et le nombre d'Objets du Grand
	 * Conseil rattachés à chaque commune.
	 */
	index(): Promise<IndexConseils>;
	/** `conseils/<cle>/objets-<année>.json` : les Objets du conseil déposés cette année-là. */
	objetsAnnee(cle: string, annee: number): Promise<ListeObjets>;
	/**
	 * Les Objets récents du conseil : la liste de l'année la plus récente, puis la précédente tant qu'il y a moins
	 * de `OBJETS_RECENTS` Objets. Les années viennent de `objets_par_annee` : aucune liste vide n'est demandée.
	 */
	objetsRecents(conseil: ConseilIndexe): Promise<PageObjets>;
	/** La page suivante : les Objets de l'année suivante (plus ancienne) ajoutés à ceux de `page`. */
	objetsSuivants(conseil: ConseilIndexe, page: PageObjets): Promise<PageObjets>;
	/** `conseils/<cle>/seances.json` : toutes les Séances du conseil, de la plus récente à la plus ancienne. */
	seances(cle: string): Promise<ListeSeances>;
	/** Le fichier d'archive d'une Séance, par sa clé (`5586/2026-10-06` : `conseils/5586/seances/2026-10-06.json`). */
	seance(cle: string): Promise<Seance>;
}

export interface Options {
	fetch: typeof fetch;
	/** Adresse de base des Pages du dépôt de données, sans barre finale. */
	donnees?: string;
}

/** Les années d'Objets d'un conseil, de la plus récente à la plus ancienne. */
const annees = (conseil: ConseilIndexe) =>
	Object.entries(conseil.objets_par_annee)
		.filter(([, n]) => n > 0)
		.map(([a]) => Number(a))
		.sort((a, b) => b - a);

/**
 * Chaque fichier est lu une fois par visite ; une lecture rejette s'il est injoignable, absent ou d'une version
 * inconnue, et la demande suivante le relit.
 */
export function creerDonneesConseils({ fetch: f, donnees = DONNEES }: Options): DonneesConseils {
	/** Un fichier du dépôt de données, par son chemin ; rejette s'il n'est pas lisible dans une version connue. */
	async function lire<T>(chemin: string): Promise<T> {
		const reponse = await f(`${donnees}/${chemin}`);
		if (!reponse.ok) throw new Error(`${chemin} : HTTP ${reponse.status}`);
		const contenu = (await reponse.json()) as { version?: unknown } | null;
		if (contenu?.version !== VERSION_CONSEILS)
			throw new Error(`${chemin} : version inconnue (${String(contenu?.version)})`);
		return contenu as T;
	}

	const lus = new Map<string, Promise<unknown>>();
	function lireUneFois<T>(chemin: string): Promise<T> {
		let lecture = lus.get(chemin) as Promise<T> | undefined;
		if (!lecture) {
			const l = lire<T>(chemin);
			l.catch(() => {
				if (lus.get(chemin) === l) lus.delete(chemin);
			});
			lus.set(chemin, l);
			lecture = l;
		}
		return lecture;
	}

	const objetsAnnee = (cle: string, annee: number) => lireUneFois<ListeObjets>(`conseils/${cle}/objets-${annee}.json`);

	async function objetsSuivants(conseil: ConseilIndexe, page: PageObjets): Promise<PageObjets> {
		if (page.suivante === null) return page;
		const liste = await objetsAnnee(conseil.cle, page.suivante);
		const reste = annees(conseil).filter((a) => a < page.suivante!);
		return { objets: [...page.objets, ...liste.objets], suivante: reste[0] ?? null };
	}

	return {
		index: () => lireUneFois<IndexConseils>('conseils/index.json'),
		objetsAnnee,
		async objetsRecents(conseil) {
			let page: PageObjets = { objets: [], suivante: annees(conseil)[0] ?? null };
			while (page.suivante !== null && page.objets.length < OBJETS_RECENTS) page = await objetsSuivants(conseil, page);
			return page;
		},
		objetsSuivants,
		seances: (cle) => lireUneFois<ListeSeances>(`conseils/${cle}/seances.json`),
		seance(cle) {
			const [conseil, jour] = cle.split('/');
			return lireUneFois<Seance>(`conseils/${conseil}/seances/${jour}.json`);
		}
	};
}

/** Les données des conseils de la visite en cours. */
export const conseils = creerDonneesConseils({ fetch: (entree, init) => fetch(entree, init) });
