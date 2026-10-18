import { communesTexte, longueurTexte, ordreListe } from './cartes.js';
import type { Restriction } from './donnees.svelte.js';
import { ETATS, type EtatRestriction } from './etats.js';
import { echeance, leveeLeWeekEnd, ligneHoraires, periode } from './horaires.js';
import { pastille, type Pastille } from './sortes.js';

/**
 * Ce que montre la fiche d'une restriction de circulation : la route en clair, les autres restrictions de ses
 * travaux, et le reste de la fiche dans son ordre. Fonctions pures. Ni `OBJECTID`, ni `ENTITE`, ni `ARRDT`.
 */

const RESEAUX: Record<string, string> = { B: 'réseau de base', C: 'réseau complémentaire', IL: 'intérêt local' };
const CLASSES: Record<string, string> = { P: 'principale', S: 'secondaire' };

/**
 * La route en clair depuis le `RHRC` (« <n°>-<B/C/IL>-<P/S> ») : « Route cantonale 626 (réseau de base,
 * principale) ». Une valeur qui ne suit pas la forme est donnée telle quelle. C'est la route des travaux, pas
 * forcément celle sous le tracé : le libellé n'en dit pas plus.
 */
export function routeEnClair(rhrc: string | null): string | null {
	if (!rhrc) return null;
	const m = /^(\d+)\s*-\s*(B|C|IL)\s*-\s*(P|S)$/i.exec(rhrc.trim());
	if (!m) return rhrc;
	const [, numero, reseau, classe] = m;
	return `Route cantonale ${numero} (${RESEAUX[reseau.toUpperCase()]}, ${CLASSES[classe.toUpperCase()]})`;
}

/**
 * Les autres restrictions des travaux de `r` : même `RHRC` et même `NOM`, en cours et à venir ensemble, dans l'ordre
 * des listes. Deux `NOM` différents font deux travaux, même au même endroit. Une restriction sans nom n'a pas de
 * travaux : rien ne la relie aux autres.
 */
export function memesTravaux(r: Restriction, restrictions: readonly Restriction[]): Restriction[] {
	if (!r.nom) return [];
	return restrictions.filter((x) => x.id !== r.id && x.nom === r.nom && x.rhrc === r.rhrc).sort(ordreListe);
}

/** Une commune traversée, dans la fiche : son nom, de quoi ouvrir son onglet Routes, et les mètres parcourus. */
export interface CommuneTraversee {
	slug: string;
	nom: string;
	longueur: string;
}

/** Ce que montre la fiche d'une restriction, dans l'ordre de la fiche. */
export interface FicheRestriction extends Pastille {
	/** 1. La pastille (sorte telle que publiée), l'état, l'échéance, puis le `NOM`. */
	etat: (typeof ETATS)[EtatRestriction]['nom'];
	echeance: string;
	nom: string;
	/** 2. La période en toutes lettres, la ligne d'horaires, et « Levée le week-end » s'il y a lieu. */
	periode: string;
	horaires: string;
	weekEnd: string | null;
	/** 3. La route en clair, le genre de travaux (`TYPE`), la remarque et la longueur du tracé. */
	route: string | null;
	travaux: string | null;
	remarque: string | null;
	longueur: string;
	/** 4. Les communes, de la plus grande longueur parcourue à la plus petite ; `null` avant le rattachement. */
	communes: CommuneTraversee[] | null;
}

/** La fiche d'une restriction ; `aujourdhui` (AAAA-MM-JJ à Lausanne) date l'échéance. */
export function ficheRestriction(r: Restriction, { aujourdhui }: { aujourdhui: string }): FicheRestriction {
	return {
		...pastille(r),
		etat: ETATS[r.etat].nom,
		echeance: echeance(r, aujourdhui),
		nom: r.nom,
		periode: periode(r, 'longue'),
		horaires: ligneHoraires(r),
		weekEnd: leveeLeWeekEnd(r.weekEnd),
		route: routeEnClair(r.rhrc),
		travaux: r.travaux,
		remarque: r.remarque,
		longueur: longueurTexte(r.longueur),
		communes:
			r.communes?.map((p) => ({ slug: p.commune.slug, nom: p.commune.nom, longueur: longueurTexte(p.metres) })) ?? null
	};
}

/** Une autre restriction des mêmes travaux, en une ligne : « Déviation · Lutry, Pully et 1 autre ». */
export function ligneMemesTravaux(r: Restriction): Pastille & { detail: string } {
	const etat = ETATS[r.etat].minuscules;
	return {
		...pastille(r),
		detail: [etat, r.communes ? communesTexte(r.communes) : null, longueurTexte(r.longueur)].filter(Boolean).join(' · ')
	};
}
