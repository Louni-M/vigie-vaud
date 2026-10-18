import type { Contexte, Couche, Ouvert } from '#lib/registre/types.js';
import { SORTES } from './sortes.js';

/** Ce que le fil d'Ariane et le titre disent d'une restriction ouverte : jamais son `OBJECTID`, que l'on ne voit pas. */
const RESTRICTION = 'Restriction de circulation';

/**
 * La couche Routes : les restrictions de circulation de la DGMR, en cours et à venir, lues en direct sur le service
 * du canton pour tout le canton (sans emprise). Ses composants partagent le module de données `donnees.svelte.ts`,
 * que la description n'importe pas : elle reste légère.
 */
export const coucheRoutes: Couche<undefined> = {
	id: 'routes',
	nom: 'Routes',
	nomOnglet: 'Routes',
	sources: ['dgmr-restrictions'],
	permanente: false,
	activeParDefaut: true,
	icone: { signe: 'R', couleur: SORTES.fermeture.couleur },
	// `?r=<OBJECTID>` : seul l'élément ouvert va dans l'adresse, pas les puces du volet.
	cleElement: 'r',
	// Le module de données n'est importé qu'à la première ouverture d'une restriction. Elle s'ouvre dans la commune
	// où elle est la plus longue, sauf si la fiche du chemin est une de ses communes.
	async localiser(element) {
		if (!/^\d+$/.test(element)) return null;
		const { routes } = await import('./donnees.svelte.js');
		const r = await routes.restriction(Number(element));
		return r && { fiches: (r.communes ?? []).map((p) => ({ commune: p.commune.slug })), position: r.milieu };
	},
	// Sans numéro : il n'est jamais affiché. Levée, retrait ou renumérotation ne se distinguent pas.
	introuvable: () => 'Cette restriction de circulation n’est plus publiée par la DGMR : elle a pu être levée ou modifiée.',
	nonCherche: () => 'La restriction de circulation n’a pas pu être cherchée : vérifiez votre connexion, puis réessayez.',
	libelle: () => RESTRICTION,
	titre: (_, nomDeLaFiche) => `${RESTRICTION} – ${nomDeLaFiche} – Vigie Vaud`,
	// Une phrase fixe : la page de la commune est pré-générée, les restrictions lues en direct.
	resume: 'les restrictions de circulation en cours et à venir',
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
export const restrictionOuverte = (o: Ouvert | null) =>
	o?.couche === coucheRoutes.id && /^\d+$/.test(o.element) ? Number(o.element) : null;
