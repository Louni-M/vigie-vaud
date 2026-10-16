import type {
	ConseilIndexe,
	EntreeFil,
	FilConseils,
	IndexConseils,
	LigneObjet,
	Objet,
	RattachementsCommune,
	Seance
} from '#lib/schema.js';

/**
 * Faux dépôt de données des conseils, pour les tests : des fabriques de fichiers de lecture et d'archive, typées par
 * les types générés depuis le schéma Pydantic, et un `fetch` qui sert ces fichiers par leur chemin
 * (`conseils/index.json`, `conseils/vd/objets/26_INT_140.json`…), comme les Pages du dépôt de données.
 */

/** Heure de passage du cron des fichiers fabriqués. */
export const GENERE = '2026-10-14T05:00:00Z';

/** Un Objet en ligne légère ; par défaut, une interpellation du Grand Conseil sans commune. */
export function ligneObjet(champs: Partial<LigneObjet> = {}): LigneObjet {
	return {
		cle: 'vd/26_INT_140',
		numero: '26_INT_140',
		type: 'Interpellation',
		depose: '2026-10-06',
		titre: 'Quelle politique pour les transports publics régionaux ?',
		auteurs: [{ nom: 'Alice Martin', parti: 'PS' }],
		nombre_auteurs: 1,
		statut: { libelle: 'Déposé', date: '2026-10-06' },
		derniere_etape: '2026-10-06',
		communes: [],
		...champs
	};
}

/** Le Grand Conseil dans l'index. */
export function grandConseil(champs: Partial<ConseilIndexe> = {}): ConseilIndexe {
	return {
		cle: 'vd',
		source: 'openparldata-vd',
		nom: 'Grand Conseil',
		commune: null,
		donne: ['objets', 'seances'],
		objets: 1,
		objets_par_annee: { '2026': 1 },
		recents: [ligneObjet()],
		seances: 1,
		prochaine_seance: null,
		derniere_seance: 'vd/2026-10-06',
		...champs
	};
}

/** Le Conseil communal de Lausanne dans l'index : il donne les Objets et les Séances. */
export function conseilLausanne(champs: Partial<ConseilIndexe> = {}): ConseilIndexe {
	return {
		cle: '5586',
		source: 'openparldata-5586',
		nom: 'Conseil communal de Lausanne',
		commune: 5586,
		donne: ['objets', 'seances'],
		objets: 2,
		objets_par_annee: { '2026': 2 },
		recents: [
			ligneObjet({ cle: '5586/POS26-012', numero: 'POS26/012', type: 'Postulat', depose: '2026-10-07' }),
			ligneObjet({ cle: '5586/INT26-031', numero: 'INT26/031', depose: '2026-10-02' })
		],
		seances: 1,
		prochaine_seance: '5586/2026-10-20',
		derniere_seance: '5586/2026-10-06',
		...champs
	};
}

/** Le Conseil communal d'Yverdon-les-Bains dans l'index : OpenParlData n'en donne que les Séances. */
export function conseilYverdon(champs: Partial<ConseilIndexe> = {}): ConseilIndexe {
	return {
		cle: '5938',
		source: 'openparldata-5938',
		nom: 'Conseil communal d’Yverdon-les-Bains',
		commune: 5938,
		donne: ['seances'],
		objets: 0,
		objets_par_annee: {},
		recents: [],
		seances: 1,
		prochaine_seance: null,
		derniere_seance: '5938/2026-10-01',
		...champs
	};
}

/** `conseils/index.json` ; par défaut, les trois conseils couverts, dans l'ordre de `sources.json`. */
export function indexConseils(champs: Partial<IndexConseils> = {}): IndexConseils {
	return {
		version: 1,
		genere: GENERE,
		conseils: [grandConseil(), conseilLausanne(), conseilYverdon()],
		communes: {},
		...champs
	};
}

/** `conseils/communes/<ofs>.json` : les Objets du Grand Conseil rattachés à la commune (Pully par défaut). */
export function rattachementsCommune(objets: LigneObjet[], commune = 5590): RattachementsCommune {
	return { version: 1, genere: GENERE, commune, objets };
}

/** Une entrée de `conseils/fil.json` ; par défaut, l'Objet de `ligneObjet()`. */
export function entreeFil(champs: Partial<EntreeFil> = {}): EntreeFil {
	return {
		cle: 'vd/26_INT_140',
		conseil: 'vd',
		sorte: 'objet',
		type: 'Interpellation',
		date: '2026-10-06',
		titre: 'Quelle politique pour les transports publics régionaux ?',
		communes: [],
		points: null,
		...champs
	};
}

/** `conseils/fil.json`. */
export function filConseils(entrees: EntreeFil[] = [entreeFil()]): FilConseils {
	return { version: 1, genere: GENERE, entrees };
}

/** Le fichier d'archive d'un Objet ; par défaut, celui de `ligneObjet()`. */
export function objet(champs: Partial<Objet> = {}): Objet {
	return {
		version: 1,
		genere: GENERE,
		id: 140,
		numero: '26_INT_140',
		type: 'Interpellation',
		statut: { libelle: 'Déposé', date: '2026-10-06' },
		depose: '2026-10-06',
		titre: 'Quelle politique pour les transports publics régionaux ?',
		contributeurs: [{ nom: 'Alice Martin', parti: 'PS', role: 'Auteur·e', sorte: 'personne' }],
		etapes: [{ date: '2026-10-06', libelle: 'Dépôt' }],
		documents: [],
		lien: null,
		communes: [],
		...champs
	};
}

/** Le fichier d'archive d'une Séance ; par défaut, celle du Grand Conseil du 6 octobre 2026. */
export function seance(champs: Partial<Seance> = {}): Seance {
	return {
		version: 1,
		genere: GENERE,
		id: 1006,
		date: '2026-10-06',
		nom: 'Séance du Grand Conseil',
		lien: null,
		ordre_du_jour: [
			{ numero: '1', titre: 'Communications', categorie: null, resultat: null, objet: null },
			{
				numero: '2',
				titre: 'Quelle politique pour les transports publics régionaux ?',
				categorie: 'Interpellations',
				resultat: null,
				objet: 'vd/26_INT_140'
			}
		],
		...champs
	};
}

export interface FauxDepotConseils {
	fetch: typeof fetch;
	/** Chemins demandés, relatifs à l'adresse de base, dans l'ordre. */
	requetes: string[];
	/** Pose ou remplace un fichier (`undefined` : le retire). */
	poser(chemin: string, contenu: unknown): void;
	/** Le dépôt répond désormais par cette erreur HTTP (`null` : rétabli). */
	panne(statut: number | null): void;
	/** Le dépôt devient injoignable, comme sans réseau : `fetch` échoue (`false` : rétabli). */
	horsLigne(oui: boolean): void;
}

/** Adresse de base des Pages du faux dépôt de données. */
export const DONNEES = 'https://donnees.test';

/**
 * Un `fetch` qui sert ces fichiers sous `DONNEES`, par leur chemin (« conseils/index.json »), et 404 pour les autres.
 * Le contenu est relu à chaque requête : `poser` change ce que verra la suivante.
 */
export function fauxDepotConseils(fichiers: Record<string, unknown> = {}): FauxDepotConseils {
	const contenus = new Map(Object.entries(fichiers));
	const requetes: string[] = [];
	let statutPanne: number | null = null;
	let injoignable = false;

	const repondre = async (entree: RequestInfo | URL): Promise<Response> => {
		const url = String(entree instanceof Request ? entree.url : entree);
		if (!url.startsWith(`${DONNEES}/`)) throw new Error(`Adresse non prévue par le faux dépôt : ${url}`);
		const chemin = url.slice(DONNEES.length + 1);
		requetes.push(chemin);
		if (injoignable) throw new TypeError('Failed to fetch');
		if (statutPanne) return new Response('', { status: statutPanne });
		if (!contenus.has(chemin)) return new Response('Not Found', { status: 404 });
		return new Response(JSON.stringify(contenus.get(chemin)), {
			status: 200,
			headers: { 'Content-Type': 'application/json' }
		});
	};

	return {
		fetch: repondre as typeof fetch,
		requetes,
		poser: (chemin, contenu) => (contenu === undefined ? contenus.delete(chemin) : contenus.set(chemin, contenu)),
		panne: (s) => (statutPanne = s),
		horsLigne: (oui) => (injoignable = oui)
	};
}
