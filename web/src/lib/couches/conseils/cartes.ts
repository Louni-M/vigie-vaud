import type { ConseilIndexe } from '#lib/schema.js';
import { donneDesObjets, libelleDonne } from '#lib/sources.js';
import type { Commune, Zone } from '#lib/types.js';

/** Ce que montre la carte d'un conseil couvert, dans le volet Conseils. */
export interface CarteConseil {
	/** Nom du conseil tel que la source le donne (« Conseil communal de Lausanne »). */
	nom: string;
	/** « objets et séances », « séances seulement ». */
	donne: string;
	/** « 3 objets récents » (les 14 derniers jours) ; `null` pour un conseil qui ne donne pas ses Objets. */
	recents: string | null;
	/** « Prochaine séance : mar. 20 oct. », sinon la dernière ; `null` si aucune n'est connue. */
	seance: string | null;
	/** Slug de la commune d'un conseil communal ; `null` pour le Grand Conseil. */
	commune: string | null;
}

const jour = new Intl.DateTimeFormat('fr-CH', { weekday: 'short', day: 'numeric', month: 'short' });

/** Jour d'une Séance, tiré de sa clé (`5586/2026-10-20`) : « mar. 20 oct. ». */
const jourDe = (cle: string) => jour.format(new Date(`${cle.split('/')[1].slice(0, 10)}T00:00:00`));

function recents(n: number): string {
	return n === 0 ? 'aucun objet récent' : n === 1 ? '1 objet récent' : `${n} objets récents`;
}

/** La carte d'un conseil de `conseils/index.json` ; sa commune est traduite en slug par l'index des communes. */
export function carteConseil(conseil: ConseilIndexe, communes: readonly Commune[]): CarteConseil {
	const { prochaine_seance: prochaine, derniere_seance: derniere } = conseil;
	return {
		nom: conseil.nom,
		donne: libelleDonne(conseil),
		recents: donneDesObjets(conseil) ? recents(conseil.recents.length) : null,
		seance: prochaine
			? `Prochaine séance : ${jourDe(prochaine)}`
			: derniere
				? `Dernière séance : ${jourDe(derniere)}`
				: null,
		commune: conseil.commune === null ? null : (communes.find((c) => c.bfs === conseil.commune)?.slug ?? null)
	};
}

/** Une ligne de la liste des conseils communaux du volet : la commune, puis ce que donne son conseil. */
export interface LigneConseil {
	cle: string;
	/** Nom de la commune (« Villeneuve »), qui suffit dans la liste des conseils communaux. */
	commune: string;
	slug: string;
	/** « séances seulement · prochaine séance jeu. 10 déc. ». */
	detail: string;
}

/**
 * Les conseils communaux du volet dont l'hôtel de ville est dans la zone affichée (tous tant que la carte n'a rien
 * affiché), une ligne chacun, par nom de commune. Le Grand Conseil n'y est pas : il garde sa carte.
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
			const { seance } = carteConseil(conseil, communes);
			const detail = [libelleDonne(conseil), seance && seance.charAt(0).toLowerCase() + seance.slice(1).replace(' :', '')]
				.filter(Boolean)
				.join(' · ');
			return [{ cle: conseil.cle, commune: commune.nom, slug: commune.slug, detail }];
		})
		.sort((a, b) => a.commune.localeCompare(b.commune, 'fr'));
}

/**
 * La phrase sous les conseils couverts, sur les communes grisées : sur bureau, le grisage suit le volet
 * ouvert ; sur téléphone, il suit « Voir sur la carte » (`grisage-mobile`).
 */
export function noteAutresCommunes(autres: number, telephone: boolean): string {
	const quand = telephone ? 'sur la carte par « Voir sur la carte »' : 'tant que ce volet est ouvert';
	return `Les ${autres} autres communes : pas de conseil couvert, grisées ${quand}. Leur onglet Conseil montre ce que le Grand Conseil dit d’elles.`;
}
