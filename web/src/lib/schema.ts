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
	| MembresConseil
	| Objet
	| RattachementsCommune
	| Retraits
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
export type DonneeConseil = 'objets' | 'preavis' | 'seances';
export type DateSeance = string;
export type SorteContributeur = 'personne' | 'groupe';
export type Lien = string;
/**
 * `retraits.json`, à la racine du dépôt de données : les corrections par élément des retraits, écrites à la
 * main et appliquées après le masquage, à chaque import comme au rattrapage, pour tous les conseils. Sans
 * enveloppe : le cron ne l'écrit jamais.
 */
export type Retraits = Retrait[];
export type VoieAcces = 'direct' | 'cron' | 'worker' | 'preparee';
export type SorteFraicheur = 'donnee' | 'requete' | 'millesime' | 'import';
export type ModeCouverture = 'api' | 'scrape' | 'non_couvert';
export type RaisonNonCouvert = 'preavis_seuls' | 'rien_en_ligne' | 'demande_commune' | 'refus_robots' | 'nouveau_site';

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
	 * Les sources qui ont un bloc `sonde`, et les sources communales sondées (bloc `site` et conseil), qui y figurent dès leur première sonde, faite une fois par jour juste avant leur import.
	 */
	sources: {
		[k: string]: EtatSource;
	};
	/**
	 * Les réseaux (/24) bloqués pour le robot communal et pas encore testés de nouveau ; absent quand il n'y en a aucun.
	 */
	reseaux?: {
		[k: string]: EtatReseau;
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
	 * Cause courte du dernier échec (« HTTP 503 », « délai dépassé », « marqueur absent »…).
	 */
	motif: string | null;
}
/**
 * Un réseau que le robot communal a cessé de lire après une 429, une 503, une connexion refusée ou un délai
 * dépassé. Au passage suivant (ou après `jusqu_a`), une seule sonde le teste avant les autres.
 */
export interface EtatReseau {
	/**
	 * Heure du blocage.
	 */
	depuis: string;
	/**
	 * Fin du blocage demandée par `Retry-After` ; `null` : la fin du passage du blocage.
	 */
	jusqu_a: Horodatage | null;
	/**
	 * Ce qui a bloqué le réseau (« HTTP 429 », « délai dépassé »…).
	 */
	motif: string;
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
	/**
	 * Par clé de conseil scrapé, l'heure de son premier import réussi : l'issue `a-verifier` compte 9 mois depuis ce jour tant que l'archive du conseil n'a aucune Séance. Absent quand il n'y en a pas : les conseils d'OpenParlData n'y figurent pas.
	 */
	premiers?: {
		[k: string]: Horodatage;
	};
	/**
	 * Par clé de conseil, l'heure de son dernier rattrapage réussi (relecture de tout l'historique, lancée à la main : rattrapage ciblé d'une plateforme ou d'une commune scrapée, ou rattrapage d'OpenParlData). Un conseil jamais rattrapé n'y figure pas ; absent quand il n'y en a aucun.
	 */
	rattrapages?: {
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
	/**
	 * Les documents d'une Séance sans points, que sa ligne montre à la place du nombre de points. Absent pour une Séance avec points ou sans documents.
	 */
	documents?: DocumentObjet[];
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
 * `conseils/<conseil>/membres.json` : les élu·e·s connu·e·s d'un conseil scrapé, que le masquage épargne
 * (ADR 0007) : vu·e·s sur la page des membres du conseil ou comme contributeur·rice·s d'un Objet autre qu'une
 * pétition. La liste ne fait que s'allonger : un nom qui disparaît de la page y reste. Publique, en clair, sans
 * limite de durée. Les conseils d'OpenParlData n'en ont pas : leurs élu·e·s connu·e·s sont tiré·e·s de l'archive.
 */
export interface MembresConseil {
	/**
	 * Version 1.
	 */
	version: 1;
	/**
	 * Heure du passage du cron qui a écrit le fichier (ISO 8601, UTC en Z).
	 */
	genere: string;
	/**
	 * Le conseil (`body_key` en minuscules : le n° OFS de la commune).
	 */
	conseil: string;
	/**
	 * Noms complets, « Prénom Nom », triés sans tenir compte des accents ni de la casse.
	 */
	membres: string[];
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
 * Une correction par élément (ADR 0007), écrite à la main dans `retraits.json` pour un retrait : le texte
 * corrigé d'un champ d'un élément de l'archive, que le cron réapplique à chaque import et à chaque rattrapage. Le
 * nom retiré n'y figure jamais.
 */
export interface Retrait {
	/**
	 * Clé de l'Objet (`5586/POS25-115`) ou de la Séance (`5586/2026-10-20`).
	 */
	element: string;
	/**
	 * Le champ corrigé : `titre` (d'un Objet), `nom` (d'une Séance), `point:<n>` (titre du n-ième point de l'ordre du jour d'une Séance, à partir de 1) ou `document:<lien>` (titre du document qui a ce lien).
	 */
	cible: string;
	/**
	 * Le texte qui remplace celui de la source, sans le nom retiré.
	 */
	texte: string;
	/**
	 * Jour du retrait.
	 */
	date: string;
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
	/**
	 * Les plateformes retenues, que citent les blocs `site` des sources communales.
	 */
	plateformes?: Plateforme[];
	/**
	 * Les réseaux ralentis à la main pour le robot communal.
	 */
	reseaux?: ReseauRalenti[];
	sources: Source[];
}
/**
 * Une plateforme retenue : le logiciel d'un éditeur sur lequel tournent les sites de plusieurs communes.
 */
export interface Plateforme {
	/**
	 * Identifiant cité par le bloc `site` des sources (`i-web`).
	 */
	id: string;
	/**
	 * Nom affiché par la page Couverture et l'À propos.
	 */
	nom: string;
	editeur: string;
	/**
	 * @minItems 1
	 */
	variantes: [Variante, ...Variante[]];
}
export interface Variante {
	/**
	 * Identifiant de la variante dans sa plateforme (`seances`).
	 */
	id: string;
	/**
	 * Marqueur que la sonde cherche sur la page de liste des Séances d'une commune.
	 */
	marqueur: string;
	/**
	 * Les niveaux que la variante permet : chacun est un `conseil.donne` qu'une commune de cette variante peut déclarer (`["seances"]` : séances seulement ; `["preavis", "seances"]` : séances et préavis).
	 *
	 * @minItems 1
	 */
	niveaux: [[DonneeConseil, ...DonneeConseil[]], ...[DonneeConseil, ...DonneeConseil[]][]];
}
/**
 * Un réseau que le robot communal lit plus lentement que 5 s par requête : un ralentissement décidé à la main,
 * après un blocage. Rien ne s'adapte tout seul.
 */
export interface ReseauRalenti {
	/**
	 * Le /24 (IPv6 : /64) des sites concernés, « 195.65.10.0/24 ».
	 */
	reseau: string;
	/**
	 * Secondes, au moins, entre deux requêtes vers ce réseau (5 s ailleurs, ou le `Crawl-delay` d'un site s'il est plus grand).
	 */
	intervalle: number;
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
	/**
	 * Le site d'une commune scrapée. Avec un bloc `conseil`, le cron lit le conseil sur ce site au lieu d'OpenParlData. Une commune non couverte d'une plateforme retenue y déclare sa plateforme.
	 */
	site?: Site | null;
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
	 * « canton » (les 300 communes) ou la liste des n° OFS des communes couvertes ; en `non_couvert`, la commune d'une plateforme retenue que Vigie Vaud ne lit pas.
	 */
	communes: 'canton' | [NumeroOfs, ...NumeroOfs[]];
	mode: ModeCouverture;
	/**
	 * Pourquoi une commune d'une plateforme retenue n'est pas couverte : obligatoire en `non_couvert`, interdite ailleurs. Les phrases de la Couverture et de l'onglet ne s'écrivent que côté site.
	 */
	raison?: RaisonNonCouvert | null;
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
 * Un conseil importé par le cron : exposé par OpenParlData, ou lu sur le site de sa commune quand la source a un
 * bloc `site`. Le cron importe chaque source qui a ce bloc.
 */
export interface Conseil {
	/**
	 * Clé du conseil dans OpenParlData : `VD` (Grand Conseil) ou le n° OFS de la commune. En minuscules, c'est la clé du conseil dans le dépôt de données.
	 */
	body_key: string;
	/**
	 * Ce que le conseil donne : ses Objets, ses Séances, ou les deux ; `preavis` : ses préavis seulement, parmi ses Objets. Pour une commune scrapée, c'est son niveau, déclaré d'après sa variante, jamais déduit de l'import : `objets` + `seances` (« objets et séances »), `preavis` + `seances` (« séances et préavis ») ou `seances` (« séances seulement »).
	 *
	 * @minItems 1
	 */
	donne: [DonneeConseil, ...DonneeConseil[]];
	/**
	 * Page du conseil sur le site de sa commune, vers laquelle renvoie la note de niveau d'un conseil qui ne donne pas tout et n'a pas de bloc `site` (Yverdon) ; une commune scrapée renvoie à `site.seances`.
	 */
	page?: Lien | null;
	/**
	 * `group_id` des Séances à importer : celui du Grand Conseil écarte les Séances du Conseil d'État.
	 */
	groupe?: number | null;
}
/**
 * Le site d'une commune scrapée : sa plateforme, sa variante et ses pages. Le cron le lit par le robot communal.
 * Une commune non couverte d'une plateforme retenue n'y déclare que sa plateforme.
 */
export interface Site {
	/**
	 * Identifiant de la plateforme, déclarée dans `plateformes`.
	 */
	plateforme: string;
	/**
	 * Identifiant de la variante, déclarée dans sa plateforme ; obligatoire avec un bloc `conseil`.
	 */
	variante?: string | null;
	/**
	 * Page de liste des Séances, relue en entier à chaque import ; c'est aussi la page sondée. Obligatoire avec un bloc `conseil`.
	 */
	seances?: Lien | null;
	/**
	 * Page de liste des Objets ou des préavis, selon la variante.
	 */
	objets?: Lien | null;
	/**
	 * Page des membres du conseil, en HTML ; absente si le site n'en a pas.
	 */
	membres?: Lien | null;
}
