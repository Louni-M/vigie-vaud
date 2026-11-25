import type { Codec, Contexte, Couche, Ouvert } from '#lib/registre/types.js';
import { compteRoutes, FILTRES_INITIAUX, type Filtres } from './volet.js';

export { FILTRES_INITIAUX };

/** Ce que le fil d'Ariane et le titre disent d'une restriction ouverte : jamais son `OBJECTID`, que l'on ne voit pas. */
const RESTRICTION = 'Restriction de circulation';

/** L'`OBJECTID` que porte un élément `?r=`, ou `null` s'il n'en est pas un. */
const idRestriction = (element: string) => (/^\d+$/.test(element) ? Number(element) : null);

/** Les valeurs de `toutes` que nomme la liste `texte` (« fermeture,feux »), dans l'ordre de `toutes` ; sans liste, toutes. */
function choisies<T extends string>(texte: string | null, toutes: readonly T[]): T[] {
	const noms = texte?.split(',');
	return noms ? toutes.filter((x) => noms.includes(x)) : [...toutes];
}

/** La liste à écrire pour `choisies`, dans l'ordre de `toutes`, ou `null` si elles y sont toutes (la valeur par défaut). */
function liste<T extends string>(choisies: readonly T[], toutes: readonly T[]): string | null {
	return toutes.every((x) => choisies.includes(x)) ? null : toutes.filter((x) => choisies.includes(x)).join(',');
}

/**
 * Codec des réglages du volet Routes : les puces, qui filtrent la carte comme la liste, `sortes` (« fermeture,feux »)
 * et `etats` (« a_venir »), chacune écrite seulement si une puce est éteinte, vide (`sortes=`) quand toutes le sont ;
 * puis l'ordre de la liste, `ordre=recent` (la clé `tri` est celle des Permis). Une valeur inconnue est ignorée.
 */
export const codecRoutes: Codec<Filtres> = {
	cles: ['sortes', 'etats', 'ordre'],
	lire: (params) => ({
		sortes: choisies(params.get('sortes'), FILTRES_INITIAUX.sortes),
		etats: choisies(params.get('etats'), FILTRES_INITIAUX.etats),
		ordre: params.get('ordre') === 'recent' ? 'recent' : FILTRES_INITIAUX.ordre
	}),
	ecrire(p) {
		const paires: [string, string][] = [];
		const sortes = liste(p.sortes, FILTRES_INITIAUX.sortes);
		const etats = liste(p.etats, FILTRES_INITIAUX.etats);
		if (sortes !== null) paires.push(['sortes', sortes]);
		if (etats !== null) paires.push(['etats', etats]);
		if (p.ordre !== FILTRES_INITIAUX.ordre) paires.push(['ordre', p.ordre]);
		return paires;
	}
};

/**
 * La couche Routes : les restrictions de circulation de la DGMR, en cours et à venir, lues en direct sur le service
 * du canton pour tout le canton (sans emprise). Ses composants partagent le module de données `donnees.svelte.ts`,
 * que la description n'importe pas : elle reste légère. Les puces du volet sont ses réglages, dans l'adresse
 * (`codecRoutes`).
 */
export const coucheRoutes: Couche<Filtres> = {
	id: 'routes',
	nom: 'Routes',
	sources: ['dgmr-restrictions'],
	permanente: false,
	// `?r=<OBJECTID>` : l'élément ouvert, à côté des puces du volet (`?sortes=`, `?etats=`).
	cleElement: 'r',
	codec: codecRoutes,
	// Le module de données n'est importé qu'à la première ouverture d'une restriction. Elle s'ouvre dans la commune
	// où elle est la plus longue, sauf si la fiche du chemin est une de ses communes.
	async localiser(element) {
		const id = idRestriction(element);
		if (id === null) return null;
		const { routes } = await import('./donnees.svelte.js');
		const r = await routes.restriction(id);
		return r && { fiches: (r.communes ?? []).map((p) => ({ commune: p.commune.slug })), position: r.milieu };
	},
	// Sans numéro : il n'est jamais affiché. Levée, retrait ou renumérotation ne se distinguent pas.
	introuvable: () => 'Cette restriction de circulation n’est plus publiée par la DGMR : elle a pu être levée ou modifiée.',
	nonCherche: () => 'La restriction de circulation n’a pas pu être cherchée : vérifiez votre connexion, puis réessayez.',
	libelle: () => RESTRICTION,
	titre: (_, nomDeLaFiche) => `${RESTRICTION} – ${nomDeLaFiche} – Vigie Vaud`,
	// Une phrase fixe : la page de la commune est pré-générée, les restrictions lues en direct.
	resume: 'les restrictions de circulation en cours et à venir',
	// Les sortes que publie la DGMR ; « Autres » n'a sa puce dans la rubrique que si une restriction en est.
	// Son nombre est celui de sa liste à l'ouverture : toutes les puces allumées, dans la zone de la carte.
	rubriques: [
		{
			id: 'routes',
			nom: 'Routes',
			phrase: 'Fermetures, déviations et feux, en cours ou à venir.',
			rang: 20,
			unite: { un: 'restriction de circulation', plusieurs: 'restrictions de circulation', feminin: true },
			portee: 'zone',
			async compteur() {
				const { routes } = await import('./donnees.svelte.js');
				routes.charger().catch(() => {});
				return (zone) => compteRoutes(routes, zone);
			}
		}
	],
	composants: {
		Carte: () => import('./Carte.svelte'),
		Volet: () => import('./Volet.svelte'),
		Onglet: () => import('./Onglet.svelte'),
		Fiche: () => import('./Fiche.svelte'),
		Apercu: () => import('./Apercu.svelte')
	}
};

/**
 * Ouvre une restriction par le registre, dans la fiche de sa première commune (ou dans celle du chemin, si elle en
 * fait partie) ; la carte vole tout de suite vers le milieu de son tracé.
 */
export function ouvrirRestriction(ctx: Pick<Contexte, 'ouvrir'>, r: { id: number; milieu: [number, number] }) {
	ctx.ouvrir({ couche: coucheRoutes.id, element: String(r.id), position: r.milieu });
}

/** `OBJECTID` de la restriction ouverte, ou `null` si ce qui est ouvert n'en est pas une. */
export const restrictionOuverte = (o: Ouvert | null) => (o?.couche === coucheRoutes.id ? idRestriction(o.element) : null);
