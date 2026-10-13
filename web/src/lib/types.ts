export type Statut = 'enquete' | 'procedure' | 'delivre' | 'realise' | 'abandonne' | 'autre';

export interface Etape {
	date: string;
	statut?: Statut;
	decision?: string | null;
}

/** Un dossier tel qu'écrit par pipeline/fetch.py (champs vides omis). */
export interface Dossier {
	id: number;
	fao?: string;
	debut?: string;
	fin?: string;
	nature: string;
	description?: string;
	decision?: string;
	date_decision?: string;
	statut: Statut;
	url?: string;
	lon: number;
	lat: number;
	bfs: number;
	commune: string;
	slug: string;
	historique?: Etape[];
}

export interface Commune {
	bfs: number;
	nom: string;
	slug: string;
	habitants: number | null;
	bbox: [number, number, number, number];
	total: number;
	statuts: Record<Statut, number>;
}

export interface Meta {
	mise_a_jour: string;
	genere_le: string;
	total: number;
	statuts: Record<Statut, number>;
	derniere_enquete: string | null;
	source: string;
}

/** Centre et zoom de la carte. */
export interface Centre {
	lon: number;
	lat: number;
	zoom: number;
}

export type Resultat =
	| { type: 'adresse'; genre: string; label: string; lon: number; lat: number }
	| { type: 'commune'; label: string; commune: Commune }
	| { type: 'dossier'; label: string; id: number };

/** Résumé intégré à la page d'une commune (pipeline/fetch.py). */
export interface CommuneResume {
	actifs: Dossier[];
	recents: Dossier[];
	par_annee: Record<string, number>;
}
