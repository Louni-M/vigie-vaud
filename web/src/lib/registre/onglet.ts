// Règles du registre pour l'onglet d'une couche dans la fiche commune, valables pour toute couche : les badges de
// fraîcheur sous son nom et le message « Non couvert » en tête (spec J1, « Couverture d'une couche »).
import type { Source } from '#lib/schema.js';
import type { Commune } from '#lib/types.js';
import type { CoucheInscrite } from './types.js';

/**
 * Les sources de la couche qui concernent la commune, pour les badges sous le nom de l'onglet : d'abord celles dont
 * la Couverture compte la commune (« canton » compris), puis celles qui n'ont pas de Couverture et portent sur le
 * canton (le Grand Conseil), chacune dans l'ordre de la couche. Une source que `sources` ne déclare pas est ignorée.
 * Dans une fiche propre (`bfs` : `null`), seulement celles qui portent sur tout le canton.
 */
export function sourcesDeLOnglet(couche: CoucheInscrite, sources: readonly Source[], bfs: number | null): Source[] {
	const declarees = couche.sources.flatMap((id) => sources.filter((s) => s.id === id));
	const couvrent = declarees.filter(
		({ couverture: c }) => c && (c.communes === 'canton' || (bfs !== null && c.communes.includes(bfs)))
	);
	const canton = declarees.filter((s) => !s.couverture);
	return [...couvrent, ...canton];
}

/** Nom de l'onglet de la couche dans une fiche, et du fil d'Ariane de son élément ouvert (« Conseil › … »). */
export const nomOnglet = (couche: Pick<CoucheInscrite, 'nom' | 'nomOnglet'>) => couche.nomOnglet ?? couche.nom;

/** Ce qui suit « Non couvert : » en tête de l'onglet d'une commune que la couche ne couvre pas. */
export function messageNonCouvert(couche: CoucheInscrite, commune: Commune): string {
	return couche.nonCouvert?.(commune) ?? `la couche ${couche.nom} n’a pas de source pour ${commune.nom}.`;
}
