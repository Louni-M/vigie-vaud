// Les clés des éléments de la couche Conseils (`?c=`) et ce qu'on en tire sans lire aucune donnée : la sorte de
// l'élément, son numéro à la forme canonique, le titre du document. Une clé est `<conseil>/<nom>` : `vd/26_INT_140`
// et `5586/POS25-115` pour un Objet (la barre oblique du numéro devenue `-`, un espace `_`), `5586/2026-10-06` pour
// une Séance. Le conseil est la clé du conseil dans le dépôt de données : `vd`, ou le n° OFS de la commune.
import type { Source } from '#lib/schema.js';
import { SOURCES, cleConseil, nomDuConseil } from '#lib/sources.js';
import { dateLongue } from './lignes.js';

/** Clé du Grand Conseil dans le dépôt de données. */
export const CLE_GRAND_CONSEIL = 'vd';

/** Identifiant de la fiche propre du Grand Conseil, que déclare la couche (`/grand-conseil`). */
export const FICHE_GRAND_CONSEIL = 'grand-conseil';

/** Les types d'entrées que la couche déclare au fil cantonal : ses Objets et ses Séances. */
export const TYPE_OBJETS = 'objets';
export const TYPE_SEANCES = 'seances';

export interface CleLue {
	conseil: string;
	sorte: 'objet' | 'seance';
	/** Le nom du fichier d'archive, sans `.json` : le numéro transformé, ou le jour de la Séance. */
	nom: string;
}

/** La clé d'un élément, décomposée ; `null` si ce n'est pas une clé d'élément d'un conseil. */
export function lireCle(cle: string): CleLue | null {
	const m = /^([a-z0-9]+)\/([^/\s]+)$/.exec(cle);
	if (!m || m[2] === '.' || m[2] === '..') return null;
	const [, conseil, nom] = m;
	return { conseil, sorte: /^\d{4}-\d{2}-\d{2}$/.test(nom) ? 'seance' : 'objet', nom };
}

/**
 * Le numéro d'un Objet à la forme canonique de son conseil, tiré de sa clé : celle du Grand Conseil telle quelle
 * (`26_INT_140`), celle d'un conseil communal avec sa barre oblique (`POS25-115` → `POS25/115`). L'inverse de
 * `cleObjet` n'est exact que pour les formes de `FORMES_NUMEROS` (ni espace, ni tiret d'origine) : ailleurs
 * (`vd/V_1.9.2026` pour `V 1.9.2026`) le numéro est approché, et l'Objet ouvert montre le sien (`objet.numero`).
 */
export function numeroObjet({ conseil, nom }: CleLue): string {
	return conseil === CLE_GRAND_CONSEIL ? nom : nom.replace(/-/g, '/');
}

/** Ce que le fil d'Ariane dit de l'élément ouvert : son numéro (« POS25/115 »), ou « Séance du 6 octobre 2026 ». */
export function libelleElement(cle: string): string {
	const lue = lireCle(cle);
	if (!lue) return cle;
	return lue.sorte === 'seance' ? `Séance du ${dateLongue(lue.nom)}` : numeroObjet(lue);
}

/** Ce que le titre dit de l'élément : « Objet POS25/115 », « Séance du 6 octobre 2026 ». */
export function nomElement(cle: string): string {
	const lue = lireCle(cle);
	return lue?.sorte === 'objet' ? `Objet ${numeroObjet(lue)}` : libelleElement(cle);
}

/** Titre du document, tiré de la clé seule : « Objet POS25/115 – Lausanne – Vigie Vaud ». */
export const titreElement = (cle: string, nomDeLaFiche: string) => `${nomElement(cle)} – ${nomDeLaFiche} – Vigie Vaud`;

/** La source qui donne ce conseil (`vd`, `5586`), dans `sources.json`. */
export const sourceDuConseil = (conseil: string, sources: readonly Source[] = SOURCES) =>
	sources.find((s) => s.conseil && cleConseil(s.conseil) === conseil);

/** Nom du conseil, tiré du nom de sa source par la règle de l'index : « Conseil communal de Lausanne ». */
export function nomConseil(conseil: string, sources: readonly Source[] = SOURCES): string | null {
	const source = sourceDuConseil(conseil, sources);
	return source ? nomDuConseil(source.nom) : null;
}

/**
 * Message près de la recherche quand la clé ne mène à rien : « Aucun objet n° POS25/999 au Conseil communal de
 * Lausanne dans les données d’OpenParlData. » Le trou peut venir de la source : le message le dit.
 */
export function messageIntrouvable(cle: string): string {
	const lue = lireCle(cle);
	const conseil = lue && nomConseil(lue.conseil);
	if (!lue || !conseil) return `Aucun objet n° ${cle} dans les données d’OpenParlData.`;
	const quoi = lue.sorte === 'seance' ? `Aucune séance le ${dateLongue(lue.nom)}` : `Aucun objet n° ${numeroObjet(lue)}`;
	return `${quoi} au ${conseil} dans les données d’OpenParlData.`;
}
