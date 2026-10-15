export type Statut = 'enquete' | 'procedure' | 'delivre' | 'realise' | 'abandonne' | 'autre';

export interface Etape {
	date: string;
	statut?: Statut;
	decision?: string | null;
}

/** Un dossier tel que converti par le module de données Permis (lib/couches/permis/donnees.svelte.ts) depuis le service du canton (champs vides omis). */
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

/** Ancienne commune absorbée par une fusion, ou ancien nom gardé sous le même n° OFS (répertoire de l'OFS). */
export interface AncienNom {
	nom: string;
	slug: string;
	type: 'Ancienne commune' | 'Ancien nom';
	/** Année de la fusion ou du changement de nom. */
	annee: number;
}

/** Une commune actuelle, telle que l'écrit la préparation des communes (pipeline/communes.py). */
export interface Commune {
	bfs: number;
	nom: string;
	slug: string;
	habitants: number | null;
	/** Emprise complète, lac compris (rattachement des dossiers). */
	bbox: [number, number, number, number];
	/** Emprise de la partie terrestre, pour cadrer la carte. */
	cadre: [number, number, number, number];
	/** Hôtel de ville [lon, lat], toujours en terre ferme. */
	hotel: [number, number];
	/** Adresse officielle de l'hôtel de ville ; vide quand sa position est approximative. */
	adresse: string;
	anciens: AncienNom[];
}

/** Point léger de l'historique sur la carte (la fiche complète est chargée à la demande). */
export type PointHisto = Pick<Dossier, 'id' | 'statut' | 'nature' | 'debut' | 'fin' | 'lon' | 'lat'>;

/** Emprise [ouest, sud, est, nord] de la carte, en WGS84. */
export type Zone = [number, number, number, number];

/** Centre et zoom de la carte. */
export interface Centre {
	lon: number;
	lat: number;
	zoom: number;
}

export type Resultat =
	| { type: 'adresse'; genre: string; label: string; lon: number; lat: number }
	| { type: 'commune'; label: string; commune: Commune }
	/** Élément d'une couche, fourni par son `chercher` ; `genre` est le nom de la couche. */
	| { type: 'element'; genre: string; label: string; couche: string; element: string };
