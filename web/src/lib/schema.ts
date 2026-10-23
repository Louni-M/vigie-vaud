/* Fichier généré par `pnpm schema` depuis pipeline/schema.py : ne pas modifier.
 * Pour changer le schéma commun, modifier les modèles Pydantic puis relancer `pnpm schema`. */

export type DocumentCommun =
	| Corrections
	| Enveloppe
	| EtatSources
	| FilConseils
	| ImportConseils
	| IndexConseils
	| ListeObjets
	| ListeSeances
	| Objet
	| RattachementsCommune
	| Seance
	| FichierSources;
export type NumeroOfs = number;
/**
 * `corrections.json`, à la racine du dépôt de données : les corrections de rattachement, écrites à la main et
 * appliquées à chaque import comme au rattrapage. Sans enveloppe : le cron ne l'écrit jamais.
 */
export type Corrections = Correction[];
export type EtatSonde = 'disponible' | 'en_panne';
export type Horodatage = string;
export type CleElement = string;
export type CleConseil = string;
export type SorteElement = 'objet' | 'seance';
export type DonneeConseil = 'objets' | 'seances';
export type DateSeance = string;
export type SorteContributeur = 'personne' | 'groupe';
export type Lien = string;
export type VoieAcces = 'direct' | 'cron' | 'worker' | 'preparee';
export type SorteFraicheur = 'donnee' | 'requete' | 'millesime' | 'import';
export type ModeCouverture = 'api' | 'scrape';

/**
 * Une correction de rattachement écrite à la main dans `corrections.json` (ADR 0016).
 */
export interface Correction {
	/**
	 * Clé de l'Objet corrigé (`vd/26_INT_140`).
	 */
	objet: string;
	/**
	 * Communes à retirer du rattachement par le nom.
	 */
	retirer?: NumeroOfs[];
	/**
	 * Communes à ajouter, en fin de liste, avec l'origine `correction`.
	 */
	ajouter?: NumeroOfs[];
	/**
	 * La raison de la correction, pour qui la relit.
	 */
	note: string;
}
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
 * `conseils/fil.json` : les Objets et les Séances de tous les conseils datés des 21 derniers jours (heure de
 * Suisse, marge pour des imports manqués) ou après, donc toutes les Séances à venir, du plus récent au plus ancien.
 * Le site filtre lui-même sur sa fenêtre.
 */
export interface FilConseils {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	entrees: EntreeFil[];
}
/**
 * Un Objet ou une Séance, à la forme d'une entrée du fil cantonal.
 */
export interface EntreeFil {
	cle: CleElement;
	conseil: CleConseil;
	sorte: SorteElement;
	/**
	 * Objet : son type brut. Séance : `null`.
	 */
	type: string | null;
	/**
	 * Objet : jour de dépôt, sinon de sa première étape datée. Séance : son jour, avec l'heure quand la source la donne.
	 */
	date: string;
	/**
	 * Objet : son titre masqué. Séance : son nom brut (le site compose le sien).
	 */
	titre: string;
	/**
	 * Conseil communal : sa commune. Grand Conseil : les communes rattachées à l'Objet, dans l'ordre du rattachement ; aucune pour une Séance.
	 */
	communes: NumeroOfs[];
	/**
	 * Séance : nombre de points de l'ordre du jour. Objet : `null`.
	 */
	points: number | null;
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
 * `conseils/index.json` : chaque conseil importé, dans l'ordre de `sources.json`, et le nombre d'Objets du
 * Grand Conseil rattachés à chaque commune.
 */
export interface IndexConseils {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	conseils: ConseilIndexe[];
	/**
	 * Par n° OFS de commune (« 5586 »), le nombre d'Objets du Grand Conseil qui lui sont rattachés. Une commune absente n'en a aucun : « Au Grand Conseil » est vide sans autre requête.
	 */
	communes: {
		[k: string]: number;
	};
}
/**
 * Un conseil dans l'index : de quoi remplir le volet et les compteurs sans autre requête.
 */
export interface ConseilIndexe {
	cle: CleConseil;
	/**
	 * La source qui donne le conseil, dans `sources.json`.
	 */
	source: string;
	/**
	 * Nom du conseil, tiré du nom de sa source (« Conseil communal de Lausanne »).
	 */
	nom: string;
	/**
	 * La commune d'un conseil communal ; `null` pour le Grand Conseil.
	 */
	commune: NumeroOfs | null;
	donne: DonneeConseil[];
	/**
	 * Nombre d'Objets listés, toutes années confondues.
	 */
	objets: number;
	/**
	 * Nombre d'Objets par année (« 2026 »), une par fichier `objets-<année>.json`.
	 */
	objets_par_annee: {
		[k: string]: number;
	};
	/**
	 * Les Objets des 14 derniers jours (date de dépôt, sinon de la première étape datée), du plus récent au plus ancien.
	 */
	recents: LigneObjet[];
	/**
	 * Nombre de Séances.
	 */
	seances: number;
	/**
	 * La première Séance du jour du passage ou après.
	 */
	prochaine_seance: CleElement | null;
	/**
	 * La dernière Séance avant le jour du passage.
	 */
	derniere_seance: CleElement | null;
}
/**
 * Un Objet en ligne légère, commune aux listes par année, à « Au Grand Conseil » et à l'index : de quoi
 * l'afficher dans une liste. Le détail est dans son fichier d'archive.
 */
export interface LigneObjet {
	/**
	 * `<conseil>/<numéro>` : le fichier d'archive de l'Objet.
	 */
	cle: string;
	numero: string;
	type: string;
	depose: string | null;
	titre: string;
	/**
	 * Les deux premiers contributeurs, dans l'ordre de la source.
	 */
	auteurs: Auteur[];
	/**
	 * Nombre de tous les contributeurs.
	 */
	nombre_auteurs: number;
	statut: Statut | null;
	/**
	 * Date de la dernière étape datée.
	 */
	derniere_etape: string | null;
	/**
	 * Grand Conseil : les communes rattachées, dans l'ordre du rattachement. Vide pour un conseil communal, dont les Objets n'appartiennent qu'à sa commune.
	 */
	communes: CommuneRattachee[];
}
export interface Auteur {
	nom: string;
	parti: string | null;
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
/**
 * Une commune rattachée à un Objet du Grand Conseil (ADR 0016), avec l'origine du rattachement.
 */
export interface CommuneRattachee {
	ofs: NumeroOfs;
	/**
	 * `titre` : nommée dans le titre ; `document` : citée dans un document ; `correction` : ajoutée à la main par `corrections.json`.
	 */
	origine: 'titre' | 'document' | 'correction';
}
/**
 * `conseils/<conseil>/objets-<année>.json` : les Objets du conseil déposés cette année-là, du plus récent au
 * plus ancien. Un Objet sans date de dépôt est classé à l'année de sa première étape datée ; sans aucune date, il
 * n'est dans aucune liste (son fichier d'archive reste ouvrable).
 */
export interface ListeObjets {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	conseil: CleConseil;
	annee: number;
	objets: LigneObjet[];
}
/**
 * `conseils/<conseil>/seances.json` : toutes les Séances du conseil, de la plus récente à la plus ancienne.
 */
export interface ListeSeances {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	conseil: CleConseil;
	seances: LigneSeance[];
}
/**
 * Une Séance en ligne légère : de quoi l'afficher dans une liste, sans son ordre du jour.
 */
export interface LigneSeance {
	/**
	 * `<conseil>/<jour>` : le fichier d'archive de la Séance.
	 */
	cle: string;
	date: DateSeance;
	/**
	 * Nombre de points de l'ordre du jour.
	 */
	points: number;
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
	 * Identifiant de l'Objet dans OpenParlData ; `null` pour un Objet scrapé.
	 */
	id: number | null;
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
	/**
	 * Grand Conseil : les communes rattachées par le nom (ADR 0016), dans l'ordre du rattachement (titre, puis documents de la plus à la moins citée, puis corrections), `corrections.json` appliqué. Vide pour un conseil communal, dont les Objets n'appartiennent qu'à leur commune.
	 */
	communes: CommuneRattachee[];
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
 * `conseils/communes/<ofs>.json` (« Au Grand Conseil ») : les Objets du Grand Conseil rattachés à la commune,
 * par date de dernière étape décroissante. Écrit seulement s'il y en a au moins un.
 */
export interface RattachementsCommune {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	commune: NumeroOfs;
	objets: LigneObjet[];
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
	 * Identifiant de la Séance dans OpenParlData ; `null` pour une Séance scrapée.
	 */
	id: number | null;
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
	/**
	 * Documents de la Séance (ordre du jour, procès-verbal…), titres masqués. Absent quand il n'y en a pas : Lausanne et Yverdon n'en ont pas.
	 */
	documents?: DocumentObjet[];
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
	 * Ce que la source ne publie pas toujours dans les communes qu'elle couvre : une phrase qui complète « La DGMR publie … ». Reprise par la page Couverture et par l'onglet de la couche ; ne change ni le mode ni l'état.
	 */
	limites?: string | null;
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
