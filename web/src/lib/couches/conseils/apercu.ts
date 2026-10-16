// Ce que dit l'aperçu d'un Objet ou d'une Séance, en bas de la carte sur téléphone : « Motion · Conseil communal de
// Lausanne · 29 sept. », puis le titre. Le composant ajoute « Lausanne · Voir la fiche › », le nom de la fiche où
// l'élément est ouvert.
import type { Objet, Seance } from '#lib/schema.js';
import { lireCle, nomConseil, nomElement } from './cles.js';
import { nomSeance } from './lignes.js';

export interface TexteApercu {
	meta: string;
	titre: string;
}

const jourMois = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short', timeZone: 'UTC' });
/** « 29 sept. » : un jour de Lausanne, sans fuseau, formaté tel quel. */
const date = (jour: string) => jourMois.format(new Date(`${jour.slice(0, 10)}T00:00:00Z`));

/** L'aperçu de l'élément de clé `cle`, lu dans son fichier d'archive (`null` : pas lu, la clé seule). */
export function apercuElement(cle: string, element: Objet | Seance | null): TexteApercu {
	const conseil = nomConseil(lireCle(cle)?.conseil ?? '') ?? '';
	if (!element) return { meta: conseil, titre: nomElement(cle) };
	if ('ordre_du_jour' in element) {
		return { meta: ['Séance', conseil, date(element.date)].filter(Boolean).join(' · '), titre: nomSeance(element.date) };
	}
	const jour = element.depose ?? element.etapes.at(-1)?.date ?? null;
	return {
		meta: [element.type, conseil, jour ? date(jour) : ''].filter(Boolean).join(' · '),
		titre: element.titre
	};
}
