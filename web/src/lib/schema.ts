/* Fichier généré par `pnpm schema` depuis pipeline/schema.py : ne pas modifier.
 * Pour changer le schéma commun, modifier les modèles Pydantic puis relancer `pnpm schema`. */

export type DocumentCommun = Enveloppe | FichierSources;
export type Lien = string;
export type VoieAcces = 'direct' | 'cron' | 'worker' | 'preparee';
export type SorteFraicheur = 'donnee' | 'requete' | 'millesime';
export type NumeroOfs = number;
export type ModeCouverture = 'api' | 'scrape';

/**
 * Enveloppe de chaque fichier du dépôt de données.
 */
export interface Enveloppe {
	/**
	 * Version majeure du format : seul un changement incompatible l'augmente. Le site refuse une version qu'il ne connaît pas.
	 */
	version: number;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
}
/**
 * `sources.json` : chaque source y est déclarée une seule fois, pour le site et pour le cron.
 */
export interface FichierSources {
	$schema?: string | null;
	sources: Source[];
}
export interface Source {
	/**
	 * Identifiant stable, clé de la source dans l'état des sources.
	 */
	id: string;
	nom: string;
	/**
	 * Nom affiché dans le badge de fraîcheur (« · CAMAC »).
	 */
	nom_court: string;
	attribution: Attribution;
	voie_acces: VoieAcces;
	fraicheur: SorteFraicheur;
	couverture: CouvertureDeclaree;
	/**
	 * Sans sonde, la source n'est pas surveillée.
	 */
	sonde?: Sonde | null;
}
export interface Attribution {
	/**
	 * Texte affiché, par ex. « © swisstopo ».
	 */
	texte: string;
	lien: Lien;
	licence: string;
}
export interface CouvertureDeclaree {
	/**
	 * « canton » (les 300 communes) ou la liste des n° OFS des communes couvertes.
	 */
	communes: 'canton' | [NumeroOfs, ...NumeroOfs[]];
	mode: ModeCouverture;
}
/**
 * Requête de vérification envoyée par le cron, sans conserver de données.
 */
export interface Sonde {
	url: Lien;
	/**
	 * Délai de réponse en secondes.
	 */
	delai: number;
	/**
	 * Champs que doit porter chaque enregistrement renvoyé.
	 */
	champs?: string[];
	/**
	 * Une réponse sans enregistrement compte comme un échec.
	 */
	jamais_vide?: boolean;
}
