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

/** L'élément ouvert : un seul à la fois, dans toute l'application. */
export interface Ouvert {
	couche: string;
	element: string;
}

/** Ce qu'on peut ouvrir : la fiche d'une commune, ou un élément d'une couche. */
export type Cible = { commune: string } | Ouvert;

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
	ouvrir(cible: Cible): void;
	fermer(): void;
}

/** Composant d'une couche, importé à la demande. */
export type Chargeur<P> = () => Promise<{ default: Component<{ ctx: Contexte<P> }> }>;

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
	/** Clé de requête de l'élément ouvert de cette couche (« d » pour un dossier). */
	cleElement?: string;
	localiser?(element: string): Promise<{ commune: string; position: [number, number] } | null>;
	/** Synchrone : la recherche du socle l'appelle à chaque frappe. */
	chercher?(texte: string): ResultatCouche[];
	titre?(element: string): string;
	/**
	 * Ce que la couche montre d'une commune, pour la description de la page de la commune
	 * (« les permis de construire à l’enquête, en direct depuis le canton »).
	 */
	resume?: string;
	/** Chargés à la demande, à l'activation de la couche ou à l'ouverture de son volet. */
	composants: {
		Carte: Chargeur<P>;
		Volet?: Chargeur<P>;
		Onglet?: Chargeur<P>;
		Fiche?: Chargeur<P>;
		Apercu?: Chargeur<P>;
	};
}

/**
 * Une couche du registre, quels que soient ses paramètres. Chaque couche ne voit que les siens,
 * typés dans sa description ; le registre les transporte sans les lire.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type CoucheInscrite = Couche<any>;
