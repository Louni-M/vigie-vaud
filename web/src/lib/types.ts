export type Statut = 'enquete' | 'procedure' | 'delivre' | 'realise' | 'abandonne' | 'autre';

export interface Etape {
	date: string;
	statut?: Statut;
	decision?: string | null;
}

/** Un dossier tel que converti par lib/data.ts depuis le service du canton (champs vides omis). */
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
}

/** Point léger de l'historique sur la carte (la fiche complète est chargée à la demande). */
export type PointHisto = Pick<Dossier, 'id' | 'statut' | 'nature' | 'debut' | 'fin' | 'lon' | 'lat'>;

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
