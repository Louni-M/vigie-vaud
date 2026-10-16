import type { Component } from 'svelte';
import type { Map as MlMap } from 'maplibre-gl';
import type { Commune, Zone } from '#lib/types.js';

/** Lecture des paramètres de requête (un `URLSearchParams` suffit). */
export type Lecteur = Pick<URLSearchParams, 'get' | 'has'>;

/**
 * Paramètres de requête propres à une couche. Le registre les décode et les passe à ses composants ;
 * seules les valeurs différentes des valeurs par défaut sont écrites.
 */
export interface Codec<P> {
	/** Clés de requête que le codec lit et écrit, et lui seul. */
	readonly cles: readonly string[];
	/** Paramètres décodés ; une clé absente ou invalide donne la valeur par défaut. */
	lire(params: Lecteur): P;
	/** Paires clé-valeur à écrire, sans les valeurs par défaut. */
	ecrire(parametres: P): [string, string][];
}

/**
 * Une fiche de la colonne : celle d'une commune (son slug), ou la fiche propre d'une couche (son identifiant). La
 * fiche ouverte est l'une ou l'autre, jamais les deux.
 */
export type Fiche = { commune: string } | { fiche: string };

/**
 * La fiche propre d'une couche (celle du Grand Conseil pour Conseils), rendue en colonne à la place d'une fiche
 * commune, avec le seul onglet de sa couche. Une couche en déclare au plus une.
 */
export interface FichePropre {
	/** Ce que porte `{ fiche }` dans `Fiche`, `Lieu.fiches` et `Cible`. */
	id: string;
	/** Chemin de sa page, relatif à la base du site, d'un seul segment (« /grand-conseil »). */
	chemin: string;
	/** En tête de la fiche et dans le titre du document. */
	nom: string;
	/** Sous le nom, à la place de l'adresse de l'hôtel de ville d'une commune. */
	sousTitre: string;
	/** Description de sa page pré-générée, pour l'aperçu d'un lien partagé et les moteurs de recherche. */
	description: string;
	/** Point (lon, lat) vers lequel vole la carte à l'ouverture de la fiche. */
	position: [number, number];
	/** Autres noms par lesquels la recherche la trouve. */
	alias?: string[];
}

/** Ce que `localiser` sait d'un élément : ses fiches, dans l'ordre, et sa position (lon, lat) s'il en a une. */
export interface Lieu {
	/** Fiches où l'élément peut s'ouvrir ; il s'ouvre dans la première, sauf si celle du chemin en fait partie. */
	fiches: Fiche[];
	position?: [number, number];
}

/** L'élément ouvert : un seul à la fois, dans toute l'application. */
export interface Ouvert {
	couche: string;
	element: string;
}

/**
 * Ce qu'on peut ouvrir : la fiche d'une commune, une fiche propre (son identifiant), ou un élément d'une couche. Le registre ouvre l'élément dans
 * l'une de ses fiches, qu'il trouve par `localiser`. Quand celui qui l'ouvre connaît déjà sa `position` (clic sur
 * la carte, liste), la carte vole vers lui tout de suite, sans attendre `localiser`. Une fiche commune peut
 * s'ouvrir sur l'onglet d'une couche (`onglet` : son id), sinon sur l'onglet déjà choisi.
 */
export type Cible =
	| { commune: string; onglet?: string }
	| { fiche: string }
	| (Ouvert & { position?: [number, number] });

/** Résultat qu'une couche fournit à la recherche du socle. */
export interface ResultatCouche {
	couche: string;
	element: string;
	libelle: string;
}

/** Contexte passé aux composants d'une couche. Toutes ses valeurs suivent l'état du registre. */
export interface Contexte<P = unknown> {
	/** Carte MapLibre du socle ; les composants ne sont montés qu'une fois la carte prête. */
	readonly map: MlMap;
	/** Calque sous lequel la couche ajoute les siens : l'ordre du registre est l'ordre de dessin. */
	readonly avant: string;
	/** Emprise visible, `null` tant que la carte n'a rien affiché. */
	readonly zone: Zone | null;
	readonly parametres: P;
	/** Change une partie des paramètres ; l'adresse est remplacée, sans nouvelle entrée d'historique. */
	regler(partiel: Partial<P>): void;
	/** La couche est activée : sa `Carte` reste montée quand on la désactive, pour le fondu. */
	readonly active: boolean;
	readonly ouvert: Ouvert | null;
	/** Commune dont la fiche est ouverte (celle que montre l'`Onglet`), ou `null`. */
	readonly commune: Commune | null;
	/** Fiche propre ouverte, où l'`Onglet` de sa couche est rendu à la place d'une commune, ou `null`. */
	readonly fiche: FichePropre | null;
	/** Index des communes actuelles, connu dès le rendu de la page. */
	readonly communes: readonly Commune[];
	/**
	 * Une couche dessinée au-dessus montre quelque chose sous ce point de la carte (pixels) : c'est elle qui reçoit
	 * le clic. Une couche qui ouvre ses éléments par un clic à quelques pixels près s'abstient alors.
	 */
	recouvert(point: [number, number]): boolean;
	ouvrir(cible: Cible): void;
	fermer(): void;
}

/** Un type d'entrée du fil cantonal (« Nouveaux dossiers ») : une puce et la pastille de ses entrées. */
export interface TypeFil {
	id: string;
	nom: string;
	signe: string;
	couleur: string;
}

/** Une entrée du fil cantonal, toute faite par sa couche. */
export interface EntreeFil {
	/** Ce que reçoit `ouvrir()`. */
	element: string;
	/** Un des types déclarés par la couche. */
	type: string;
	/** AAAA-MM-JJ ; « À venir » si elle est dans le futur. */
	date: string;
	/** « Construction nouvelle », « Motion ». */
	sorte: string;
	/** « Lutry », « Conseil communal de Lausanne ». */
	qui: string;
	titre: string;
	/** Slugs dans l'ordre du rattachement ; vide : sans commune. */
	communes: string[];
	/** Sinon, les hôtels de ville de ses communes. */
	position?: [number, number];
}

/** Ce qu'une couche apporte au fil cantonal. */
export interface Fil {
	/** Statiques : les puces s'affichent avant les données. */
	types: TypeFil[];
	/** Import dynamique, comme `localiser`. Rejette en cas d'échec. `depuis` : AAAA-MM-JJ, premier jour du fil. */
	entrees(depuis: string): Promise<EntreeFil[]>;
}

/** Composant d'une couche, importé à la demande ; `Props` s'ajoute au contexte. */
export type Chargeur<P, Props = object> = () => Promise<{ default: Component<{ ctx: Contexte<P> } & Props> }>;

/** Description légère d'une couche, inscrite au registre. */
export interface Couche<P = unknown> {
	id: string;
	nom: string;
	/** Identifiants de `sources.json`. */
	sources: string[];
	/** Toujours affichée, sans interrupteur. */
	permanente: boolean;
	activeParDefaut: boolean;
	/** Pastille du rail : un signe et sa couleur. */
	icone: { signe: string; couleur: string };
	codec?: Codec<P>;
	/** Sa fiche propre, avec sa page (« /grand-conseil ») ; seul son `Onglet` y est rendu. */
	fiche?: FichePropre;
	/** Clé de requête de l'élément ouvert de cette couche (« d » pour un dossier). */
	cleElement?: string;
	/** Fiches et position d'un élément, ou `null` si la couche ne le trouve pas. Rejette si elle n'a pas pu chercher. */
	localiser?(element: string): Promise<Lieu | null>;
	/** Message affiché près de la recherche quand `localiser` ne trouve pas l'élément (« Aucun dossier n° … »). */
	introuvable?(element: string): string;
	/** Synchrone : la recherche du socle l'appelle à chaque frappe. */
	chercher?(texte: string): ResultatCouche[];
	/** Ce que le fil d'Ariane dit de l'élément ouvert (« Permis › n° 248845 ») ; sinon « n° <élément> ». */
	libelle?(element: string): string;
	/** Titre du document quand l'élément est ouvert ; `nomDeLaFiche` est le nom de la fiche où il est ouvert. */
	titre?(element: string, nomDeLaFiche: string): string;
	/**
	 * Ce que la couche montre d'une commune, pour la description de la page de la commune
	 * (« les permis de construire à l’enquête, en direct depuis le canton »). Une fonction quand cela dépend de la
	 * commune (Conseils : son conseil communal est couvert ou non) ; elle doit être connue à la construction.
	 */
	resume?: string | ((commune: Commune) => string);
	/**
	 * Ce qui suit « Non couvert : » en tête de l'onglet d'une commune que la couche ne couvre pas, une phrase
	 * (« OpenParlData ne donne pas le conseil communal de Bussigny. ») ; sinon, le message commun du registre.
	 */
	nonCouvert?(commune: Commune): string;
	/** Ce que la couche apporte au fil cantonal, quelle que soit son activation. */
	fil?: Fil;
	/** Chargés à la demande, à l'activation de la couche ou à l'ouverture de son volet. */
	composants: {
		Carte: Chargeur<P>;
		Volet?: Chargeur<P>;
		Onglet?: Chargeur<P>;
		Fiche?: Chargeur<P>;
		/** Aperçu de l'élément ouvert, en bas de la carte sur téléphone ; `voir` montre la fiche. */
		Apercu?: Chargeur<P, { voir: () => void }>;
	};
}

/**
 * Une couche du registre, quels que soient ses paramètres. Chaque couche ne voit que les siens,
 * typés dans sa description ; le registre les transporte sans les lire.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type CoucheInscrite = Couche<any>;
