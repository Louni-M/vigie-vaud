import type { ConseilIndexe } from '#lib/schema.js';
import { libelleDonneVisiteur } from '#lib/sources.js';
import type { Commune, Zone } from '#lib/types.js';
import type { EtatCompte } from '#lib/registre/types.js';

const jour = new Intl.DateTimeFormat('fr-CH', { weekday: 'short', day: 'numeric', month: 'short' });

/** Jour d'une Séance, tiré de sa clé (`5586/2026-10-20`) : « mar. 20 oct. ». */
const jourDe = (cle: string) => jour.format(new Date(`${cle.split('/')[1].slice(0, 10)}T00:00:00`));

/** « prochaine séance mar. 20 oct. », sinon la dernière ; `null` si aucune n'est connue. */
function seanceDuConseil({ prochaine_seance: prochaine, derniere_seance: derniere }: ConseilIndexe): string | null {
	if (prochaine) return `prochaine séance ${jourDe(prochaine)}`;
	return derniere ? `dernière séance ${jourDe(derniere)}` : null;
}

/** Une ligne de la liste des communes suivies : la commune, puis ce que donne son conseil et sa Séance. */
export interface LigneConseil {
	cle: string;
	/** Nom de la commune (« Villeneuve »), qui suffit dans la liste des conseils communaux. */
	commune: string;
	slug: string;
	/** « textes déposés et séances · prochaine séance jeu. 10 déc. ». */
	detail: string;
}

/**
 * Les conseils communaux du volet dont l'hôtel de ville est dans la zone affichée (tous tant que la carte n'a rien
 * affiché), une ligne chacun, par nom de commune. Le Grand Conseil n'y est pas : il a sa propre rubrique.
 */
export function lignesConseils(
	conseils: readonly ConseilIndexe[],
	communes: readonly Commune[],
	zone: Zone | null
): LigneConseil[] {
	const parNumero = new Map(communes.map((c) => [c.bfs, c]));
	const dans = ([lon, lat]: [number, number]) =>
		!zone || (lon >= zone[0] && lon <= zone[2] && lat >= zone[1] && lat <= zone[3]);
	return conseils
		.flatMap((conseil) => {
			const commune = conseil.commune === null ? undefined : parNumero.get(conseil.commune);
			if (!commune || !dans(commune.hotel)) return [];
			const detail = [libelleDonneVisiteur(conseil), seanceDuConseil(conseil)].filter(Boolean).join(' · ');
			return [{ cle: conseil.cle, commune: commune.nom, slug: commune.slug, detail }];
		})
		.sort((a, b) => a.commune.localeCompare(b.commune, 'fr'));
}

/** Le nombre de la rubrique Conseils communaux : les communes suivies de la zone, une par ligne de la liste. */
export const compteConseils = (
	conseils: readonly ConseilIndexe[],
	communes: readonly Commune[],
	zone: Zone | null
): EtatCompte => ({ etat: 'nombre', nombre: lignesConseils(conseils, communes, zone).length });

/**
 * Le nombre de la rubrique Grand Conseil : tous ses Objets, toutes années confondues, ceux que sa fiche liste sous
 * « Tous les objets », pour tout le canton.
 */
export function compteGrandConseil(conseils: readonly ConseilIndexe[]): EtatCompte {
	const gc = conseils.find((c) => c.commune === null);
	return gc ? { etat: 'nombre', nombre: gc.objets } : { etat: 'indisponible' };
}

/** La phrase sous les communes suivies, sur les communes grisées tant que la rubrique est ouverte. */
export const noteAutresCommunes = (autres: number): string =>
	`Les ${autres} autres communes : pas de conseil suivi, grisées sur la carte. Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.`;
