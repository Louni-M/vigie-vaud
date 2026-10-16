/* Fichier généré par `pnpm schema` depuis pipeline/schema.py : ne pas modifier.
 * Pour changer le schéma commun, modifier les modèles Pydantic puis relancer `pnpm schema`. */

export type DocumentCommun = Enveloppe | EtatSources | ImportConseils | FichierSources;
export type EtatSonde = 'disponible' | 'en_panne';
export type Horodatage = string;
export type Lien = string;
export type VoieAcces = 'direct' | 'cron' | 'worker' | 'preparee';
export type SorteFraicheur = 'donnee' | 'requete' | 'millesime' | 'import';
export type NumeroOfs = number;
export type ModeCouverture = 'api' | 'scrape';
export type DonneeConseil = 'objets' | 'seances';

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
 * `etat-sources.json` : l'état de chaque source sondée, indexé par identifiant de source.
 */
export interface EtatSources {
	/**
	 * Version 1. Le cron repart de zéro devant une autre version.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	/**
	 * Seules les sources qui ont un bloc `sonde` y figurent.
	 */
	sources: {
		[k: string]: EtatSource;
	};
}
/**
 * Ce que les sondes ont mesuré pour une source, dans un état binaire (sans « dégradée »).
 *
 * Aucun numéro d'issue n'y figure.
 */
export interface EtatSource {
	etat: EtatSonde;
	/**
	 * En panne : heure de la première sonde en échec. Disponible : heure du retour, ou de la première sonde réussie ; `null` tant qu'aucune sonde n'a réussi.
	 */
	depuis: Horodatage | null;
	derniere_sonde: Horodatage;
	/**
	 * `null` tant qu'aucune sonde n'a réussi.
	 */
	dernier_succes: Horodatage | null;
	/**
	 * La source passe en panne à 2.
	 */
	echecs_consecutifs: number;
	/**
	 * Cause courte du dernier échec (« HTTP 503 », « délai dépassé »…).
	 */
	motif: string | null;
}
/**
 * `conseils/import.json` : l'heure du dernier import réussi de chaque conseil, importé à part. C'est la
 * mémoire du cron et la base du badge de fraîcheur des sources `import`.
 */
export interface ImportConseils {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	/**
	 * Par clé de conseil (`body_key` en minuscules : `vd`, `5586`…), l'heure du dernier import réussi. Un conseil jamais importé n'y figure pas.
	 */
	conseils: {
		[k: string]: Horodatage;
	};
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
	/**
	 * Absente, la source n'a pas de Couverture : elle porte sur le canton (Grand Conseil) ou ses éléments n'appartiennent à aucune commune.
	 */
	couverture?: CouvertureDeclaree | null;
	/**
	 * Sans sonde, la source n'est pas surveillée.
	 */
	sonde?: Sonde | null;
	/**
	 * Le conseil que donne la source, importé par le cron.
	 */
	conseil?: Conseil | null;
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
 *
 * Une seule requête GET par passage, sans nouvel essai. La réponse doit être un objet JSON dont une clé
 * (`enregistrements`) liste les enregistrements ; elle doit donc rester légère (un enregistrement suffit).
 */
export interface Sonde {
	url: Lien;
	/**
	 * Délai de réponse en secondes.
	 */
	delai: number;
	/**
	 * Champs que doit porter chaque enregistrement renvoyé, lus dans `attributes` (JSON ArcGIS) ou `properties` (GeoJSON), sinon à plat dans l'enregistrement (OpenParlData).
	 */
	champs?: string[];
	/**
	 * Clé de la réponse qui liste les enregistrements : `features` (JSON ArcGIS, GeoJSON) ou `data` (OpenParlData).
	 */
	enregistrements?: string;
	/**
	 * Une réponse sans enregistrement compte comme un échec.
	 */
	jamais_vide?: boolean;
}
/**
 * Un conseil exposé par OpenParlData. Le cron importe chaque source qui a ce bloc.
 */
export interface Conseil {
	/**
	 * Clé du conseil dans OpenParlData : `VD` (Grand Conseil) ou le n° OFS de la commune. En minuscules, c'est la clé du conseil dans le dépôt de données.
	 */
	body_key: string;
	/**
	 * Ce que le conseil donne : ses Objets, ses Séances, ou les deux.
	 *
	 * @minItems 1
	 */
	donne: [DonneeConseil, ...DonneeConseil[]];
	/**
	 * `group_id` des Séances à importer : celui du Grand Conseil écarte les Séances du Conseil d'État.
	 */
	groupe?: number | null;
}
