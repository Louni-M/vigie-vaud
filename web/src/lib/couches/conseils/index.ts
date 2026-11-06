import type { Codec, Couche } from '#lib/registre/types.js';
import { SOURCES } from '#lib/sources.js';
import {
	FICHE_GRAND_CONSEIL,
	TYPE_OBJETS,
	TYPE_SEANCES,
	libelleElement,
	messageIntrouvable,
	titreElement
} from './cles.js';
import type { PuceObjets } from './lignes.js';
import { reconnaitreNumero } from './numeros.js';
import { resumeConseils } from './resume.js';
import { nonCouvertConseils, sourcesDeLaCouche } from './source.js';

/** Sarcelle : la couleur de la couche, de son marqueur et des pastilles de ses Objets et Séances. */
export const COULEUR_CONSEILS = '#0b7285';

/** Le Parlement vaudois, place du Château 6 à Lausanne (lon, lat) : le marqueur du Grand Conseil. */
export const PARLEMENT: [number, number] = [6.63596, 46.52358];

/** Les réglages de la couche Conseils qui vont dans l'adresse. */
export interface ParametresConseils {
	/** La puce choisie au-dessus des « Objets récents » de la fiche du Grand Conseil. */
	objets: PuceObjets;
}

/**
 * Codec des réglages Conseils : `communes=avec` (« Nomment une commune ») ou `communes=sans` (« Sans commune »),
 * rien pour « Tous », la valeur par défaut. Une seule clé pour toute la couche : seule la liste des Objets du Grand
 * Conseil a des puces (les Objets d'un conseil communal nomment tous leur commune), et c'est la puce qu'on partage
 * avec l'adresse de sa fiche.
 */
export const codecConseils: Codec<ParametresConseils> = {
	cles: ['communes'],
	lire(params) {
		const v = params.get('communes');
		return { objets: v === 'avec' || v === 'sans' ? v : 'tous' };
	},
	ecrire: (p) => (p.objets === 'tous' ? [] : [['communes', p.objets]])
};

/**
 * La couche Conseils : le Grand Conseil et les conseils communaux couverts, lus dans les fichiers que le cron publie
 * sur les Pages du dépôt de données (`donnees.ts`). Sur la carte, seulement le marqueur du Grand Conseil ; les
 * conseils communaux sont dans la fiche de leur commune. Une seule clé d'élément, `c`, pour les Objets comme pour
 * les Séances ; la puce des Objets du Grand Conseil va dans l'adresse (`codecConseils`).
 */
export const coucheConseils: Couche<ParametresConseils> = {
	id: 'conseils',
	nom: 'Conseils',
	nomOnglet: 'Conseil',
	sources: sourcesDeLaCouche(),
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'C', couleur: COULEUR_CONSEILS },
	// La fiche du Grand Conseil, au Parlement : son marqueur et sa carte dans le volet l'ouvrent.
	fiche: {
		id: FICHE_GRAND_CONSEIL,
		chemin: '/grand-conseil',
		nom: 'Grand Conseil',
		sousTitre: 'Parlement vaudois · place du Château 6, Lausanne',
		description:
			'Les objets et les séances du Grand Conseil vaudois, importés chaque jour depuis OpenParlData, et les communes qu’ils nomment.',
		position: PARLEMENT,
		alias: ['Parlement', 'GC']
	},
	cleElement: 'c',
	codec: codecConseils,
	// Un Objet ou une Séance ne s'ouvre qu'une fois son fichier d'archive lu : le module de données n'est importé
	// qu'à ce moment, et la description reste légère.
	async localiser(element) {
		const { conseils } = await import('./donnees.js');
		return conseils.localiser(element);
	},
	// La forme du numéro suffit : rien n'est lu avant l'ouverture, où `localiser` charge le fichier d'archive.
	chercher: (texte, communes) =>
		reconnaitreNumero(texte, SOURCES, communes).map(({ cle, numero, nom }) => ({
			couche: coucheConseils.id,
			element: cle,
			libelle: `Objet ${numero} · ${nom}`
		})),
	introuvable: (cle) => messageIntrouvable(cle),
	titre: titreElement,
	libelle: libelleElement,
	resume: resumeConseils(SOURCES),
	nonCouvert: (commune) => nonCouvertConseils(commune),
	// Les Objets déposés et les Séances, lus dans le seul `conseils/fil.json` ; sans position, une entrée est dans
	// la zone par les hôtels de ville de ses communes, et sans commune elle s'ouvre dans la fiche du Grand Conseil.
	fil: {
		types: [
			{ id: TYPE_OBJETS, nom: 'Objets', signe: '§', couleur: COULEUR_CONSEILS },
			{ id: TYPE_SEANCES, nom: 'Séances', signe: '◷', couleur: COULEUR_CONSEILS }
		],
		async entrees(depuis) {
			const { conseils } = await import('./donnees.js');
			return conseils.entreesFil(depuis);
		},
		sansCommune: 'Grand Conseil, sans commune nommée'
	},
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte'),
		Apercu: () => import('./Apercu.svelte')
	}
};
