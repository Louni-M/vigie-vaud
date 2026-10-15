import type { Codec, Couche } from '#lib/registre/types.js';
import type { Parametres } from './donnees.svelte.js';
import { NATURES, STATUTS, STATUTS_EN_COURS, STATUTS_ORDRE } from '#lib/labels.js';
import type { Statut } from '#lib/types.js';

/**
 * La couche Permis : dossiers CAMAC lus en direct sur le service du canton. Ses composants partagent
 * le module de données `donnees.svelte.ts`.
 */
export const couchePermis: Couche<Parametres> = {
	id: 'permis',
	nom: 'Permis',
	sources: ['camac-permis'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'P', couleur: STATUTS.enquete.couleur },
	codec: creerCodec(new Date().getFullYear()),
	cleElement: 'd',
	// Les n° CAMAC ont 5 ou 6 chiffres ; 4 chiffres sont plutôt un numéro postal.
	chercher(texte) {
		const n = texte.trim();
		return /^\d{5,6}$/.test(n) ? [{ couche: 'permis', element: n, libelle: `Dossier CAMAC n° ${n}` }] : [];
	},
	// Le module de données n'est importé qu'à la première ouverture d'un dossier : la description reste légère.
	async localiser(element) {
		if (!/^\d+$/.test(element)) return null;
		const { permis } = await import('./donnees.svelte.js');
		const d = await permis.fiche(Number(element));
		return d ? { commune: d.slug, position: [d.lon, d.lat] } : null;
	},
	introuvable: (element) => `Aucun dossier n° ${element}.`,
	titre: (element, commune) => `Dossier n° ${element} – ${commune} – Vigie Vaud`,
	resume: 'les permis de construire à l’enquête, en direct depuis le canton',
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte')
	}
};

/** Première année que le service du canton connaît. */
export const ANNEE_MIN = 1999;

/** Statuts proposés, et affichés par défaut : ceux des dossiers en cours, ou tous avec l'historique. */
export const statutsProposes = (historique: boolean): Statut[] => (historique ? STATUTS_ORDRE : STATUTS_EN_COURS);

const entier = (s: string | null) => (s && /^\d+$/.test(s) ? Number(s) : null);

/**
 * Codec des réglages Permis : `statuts`, `nature`, `historique`, `depuis` et `tri`, chacun écrit seulement
 * s'il diffère de sa valeur par défaut. Les statuts par défaut dépendent de l'historique.
 * `anneeCourante` borne le curseur et fixe l'année par défaut de l'historique (deux ans plus tôt).
 */
export function creerCodec(anneeCourante: number): Codec<Parametres> {
	const depuisParDefaut = anneeCourante - 2;
	const memes = (a: Statut[], b: Statut[]) => a.length === b.length && a.every((s) => b.includes(s));
	return {
		cles: ['statuts', 'nature', 'historique', 'depuis', 'tri'],
		lire(params) {
			const historique = params.get('historique') === '1';
			const proposes = statutsProposes(historique);
			const choisis = params.get('statuts')?.split(',');
			const nature = params.get('nature') ?? '';
			const depuis = entier(params.get('depuis')) ?? depuisParDefaut;
			return {
				statuts: choisis ? proposes.filter((s) => choisis.includes(s)) : [...proposes],
				nature: nature in NATURES ? nature : '',
				historique,
				depuis: Math.min(Math.max(depuis, ANNEE_MIN), anneeCourante),
				tri: params.get('tri') === 'fin' ? 'fin' : 'recent'
			};
		},
		ecrire(p) {
			const paires: [string, string][] = [];
			if (p.historique) paires.push(['historique', '1']);
			if (p.depuis !== depuisParDefaut) paires.push(['depuis', String(p.depuis)]);
			if (!memes(p.statuts, statutsProposes(p.historique)))
				paires.push(['statuts', STATUTS_ORDRE.filter((s) => p.statuts.includes(s)).join(',')]);
			if (p.nature) paires.push(['nature', p.nature]);
			if (p.tri !== 'recent') paires.push(['tri', p.tri]);
			return paires;
		}
	};
}
