// Règles du registre pour l'onglet d'une couche dans la fiche commune, valables pour toute couche : les badges de
// fraîcheur sous son nom et le message « Non couvert » en tête (spec J1, « Couverture d'une couche »).
import type { Source } from '#lib/schema.js';
import type { Commune } from '#lib/types.js';
import type { CoucheInscrite, MessageNonCouvert, Ouvert } from './types.js';

/**
 * Les sources de la couche qui concernent la commune, pour les badges sous le nom de l'onglet : d'abord celles dont
 * la Couverture compte la commune (« canton » compris), puis celles qui n'ont pas de Couverture et portent sur le
 * canton (le Grand Conseil), chacune dans l'ordre de la couche. Une source que `sources` ne déclare pas est ignorée,
 * comme celle qui déclare la commune non couverte. Dans une fiche propre (`bfs` : `null`), seulement celles qui
 * portent sur tout le canton.
 */
export function sourcesDeLOnglet(couche: CoucheInscrite, sources: readonly Source[], bfs: number | null): Source[] {
	const declarees = couche.sources.flatMap((id) => sources.filter((s) => s.id === id));
	const couvrent = declarees.filter(
		({ couverture: c }) =>
			c && c.mode !== 'non_couvert' && (c.communes === 'canton' || (bfs !== null && c.communes.includes(bfs)))
	);
	const canton = declarees.filter((s) => !s.couverture);
	return [...couvrent, ...canton];
}

/**
 * Les onglets d'une fiche : un par couche qui a un `Onglet` pour une fiche commune, le seul de sa couche pour une
 * fiche propre (`propre` : la couche qui la déclare).
 */
export const ongletsDeLaFiche = (couches: readonly CoucheInscrite[], propre: CoucheInscrite | null): CoucheInscrite[] =>
	propre ? (propre.composants.Onglet ? [propre] : []) : couches.filter((c) => c.composants.Onglet);

/**
 * L'onglet montré : celui de la couche de l'élément ouvert quand il s'y affiche (elle a une `Fiche`), sinon l'onglet
 * choisi, sinon le premier.
 */
export function ongletCourant(
	onglets: readonly CoucheInscrite[],
	choisi: string | null,
	ouvert: Ouvert | null
): CoucheInscrite | undefined {
	const avecFiche = onglets.find((c) => c.id === ouvert?.couche && c.composants.Fiche);
	return avecFiche ?? onglets.find((c) => c.id === choisi) ?? onglets[0];
}

/**
 * Nom de l'onglet de la couche dans une fiche, et du fil d'Ariane de son élément ouvert (« Routes › … ») : celui de sa
 * rubrique, pour qu'un sujet porte le même nom partout. Dans une fiche propre (`fiche` : son identifiant), celui de la
 * rubrique qui l'ouvre ; dans une fiche commune, celui de sa rubrique à volet ; à défaut, le nom de la couche.
 */
export function nomOnglet(couche: Pick<CoucheInscrite, 'nom' | 'rubriques'>, fiche: string | null = null): string {
	const rubriques = couche.rubriques ?? [];
	return (fiche ? rubriques.find((r) => r.fiche === fiche) : rubriques.find((r) => !r.fiche))?.nom ?? couche.nom;
}

/**
 * En tête de l'onglet d'une commune que la couche ne couvre pas : « Pas encore de données Routes pour cette
 * commune. », suivi de l'explication de la couche quand elle en donne une, et de son lien s'il y en a un.
 */
export function messageNonCouvert(couche: CoucheInscrite, commune: Commune): MessageNonCouvert {
	const pasEncore = `Pas encore de données ${nomOnglet(couche)} pour cette commune`;
	const message = couche.nonCouvert?.(commune);
	if (message === undefined) return { texte: `${pasEncore}.` };
	const { texte, lien } = typeof message === 'string' ? { texte: message, lien: undefined } : message;
	return { texte: `${pasEncore}\u00a0: ${texte}`, ...(lien && { lien }) };
}
