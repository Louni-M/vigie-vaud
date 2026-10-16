/* Fichier généré par `pnpm schema` depuis pipeline/schema.py : ne pas modifier.
 * Pour changer le schéma commun, modifier les modèles Pydantic puis relancer `pnpm schema`. */

export type DocumentCommun = Enveloppe | EtatSources | ImportConseils | Objet | Seance | FichierSources;
export type EtatSonde = 'disponible' | 'en_panne';
export type Horodatage = string;
export type SorteContributeur = 'personne' | 'groupe';
export type Lien = string;
export type CleElement = string;
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
 * `conseils/<conseil>/objets/<numéro>.json` : un Objet d'un conseil, normalisé depuis OpenParlData. Sa clé est
 * `<conseil>/<numéro>`, la barre oblique du numéro devenant `-` (`vd/26_INT_140`, `5586/POS25-115`).
 */
export interface Objet {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	/**
	 * Identifiant de l'Objet dans OpenParlData.
	 */
	id: number;
	/**
	 * Numéro que lui donne le conseil (`26_INT_140`, `POS25/115`).
	 */
	numero: string;
	/**
	 * Type brut de la source (`type_name`).
	 */
	type: string;
	statut: Statut | null;
	/**
	 * Date de dépôt (`begin_date`).
	 */
	depose: string | null;
	/**
	 * `title.fr` de la source, noms de particuliers masqués (« [particulier] », ADR 0007).
	 */
	titre: string;
	/**
	 * Dans l'ordre de la source ; vide pour une pétition.
	 */
	contributeurs: Contributeur[];
	/**
	 * Étapes datées, de la plus ancienne à la plus récente.
	 */
	etapes: Etape[];
	documents: DocumentObjet[];
	/**
	 * Page de l'Objet chez le conseil (`url_external`).
	 */
	lien: Lien | null;
}
export interface Statut {
	/**
	 * Le `state_name` brut de la source quand il existe, sinon le libellé de la dernière étape datée.
	 */
	libelle: string;
	/**
	 * Date de la dernière étape datée ; `null` si aucune étape n'est datée.
	 */
	date: string | null;
}
export interface Contributeur {
	nom: string;
	/**
	 * Abréviation du parti, telle que la source la donne.
	 */
	parti: string | null;
	/**
	 * Rôle brut (« Auteur », « Cosignataires », « Federführung »…).
	 */
	role: string | null;
	sorte: SorteContributeur;
}
export interface Etape {
	date: string;
	/**
	 * `title.fr` de la source, sinon `title_harmonized.fr`, brut.
	 */
	libelle: string;
}
export interface DocumentObjet {
	/**
	 * Nom du document, sinon sa catégorie.
	 */
	titre: string | null;
	date: string | null;
	/**
	 * Le document chez la source (PDF, page ou vidéo).
	 */
	lien: string;
}
/**
 * `conseils/<conseil>/seances/<AAAA-MM-JJ>.json` : une Séance d'un conseil. Sa clé est `<conseil>/<jour>`.
 */
export interface Seance {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	/**
	 * Identifiant de la Séance dans OpenParlData.
	 */
	id: number;
	/**
	 * Jour, heure locale comprise quand la source la donne (`2026-10-01T20:00`).
	 */
	date: string;
	/**
	 * Nom brut de la source ; le site affiche un nom composé à partir de la date.
	 */
	nom: string;
	lien: Lien | null;
	ordre_du_jour: PointOrdreDuJour[];
}
export interface PointOrdreDuJour {
	/**
	 * Numéro du point tel que la source l'affiche.
	 */
	numero: string | null;
	/**
	 * `item_title` de la source, noms de particuliers masqués (« [particulier] », ADR 0007).
	 */
	titre: string;
	categorie: string | null;
	/**
	 * Résultat brut (« Transmise au CE », « Renvoi en Municipalité »…).
	 */
	resultat: string | null;
	/**
	 * Clé de l'Objet du point, quand il est dans l'archive.
	 */
	objet: CleElement | null;
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
