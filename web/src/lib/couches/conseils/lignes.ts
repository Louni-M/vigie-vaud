// Ce que montrent les lignes d'Objet et de Séance et l'en-tête de séance de l'onglet Conseil, tiré des fichiers de
// lecture sans autre requête. Les dates des conseils sont des jours (et heures) de Lausanne, sans fuseau : elles
// sont formatées telles quelles, en UTC, pour ne jamais glisser d'un jour.
import type { ConseilIndexe, LigneObjet, LigneSeance } from '#lib/schema.js';

const jourLong = new Intl.DateTimeFormat('fr-CH', {
	weekday: 'long',
	day: 'numeric',
	month: 'long',
	year: 'numeric',
	timeZone: 'UTC'
});
const jourCourt = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

const jour = (date: string) => new Date(`${date.slice(0, 10)}T00:00:00Z`);

/**
 * Le nom composé d'une Séance, à partir de sa date (`2026-10-06` ou `2026-10-01T20:00`) : « Séance du mardi
 * 6 octobre 2026 », « Séance du jeudi 1er octobre 2026 à 20 h ». Le nom brut de la source n'est jamais affiché.
 */
export function nomSeance(date: string): string {
	const d = jour(date);
	// Sans la virgule que l'ICU met après le jour de la semaine (« mardi, 6 octobre »).
	const texte = jourLong
		.formatToParts(d)
		.filter((p) => p.type !== 'literal')
		.map((p) => (p.type === 'day' && p.value === '1' ? '1er' : p.value))
		.join(' ');
	const [h, m] = date.length > 10 ? date.slice(11, 16).split(':').map(Number) : [];
	const heure = h === undefined ? '' : ` à ${h} h${m ? ` ${String(m).padStart(2, '0')}` : ''}`;
	return `Séance du ${texte}${heure}`;
}

/** Les auteur·e·s d'un Objet avec leur parti : les deux premiers, puis « et al. » ; vide pour une pétition. */
export function auteursObjet(ligne: Pick<LigneObjet, 'auteurs' | 'nombre_auteurs'>): string {
	const noms = ligne.auteurs.slice(0, 2).map((a) => (a.parti ? `${a.nom} (${a.parti})` : a.nom));
	return `${noms.join(', ')}${ligne.nombre_auteurs > 2 ? ' et al.' : ''}`;
}

/** La date d'un Objet, celle de son dépôt, sinon de sa dernière étape : « 6 oct. 2026 » ; vide s'il n'en a pas. */
export function dateObjet(ligne: Pick<LigneObjet, 'depose' | 'derniere_etape'>): string {
	const date = ligne.depose ?? ligne.derniere_etape;
	return date ? jourCourt.format(jour(date)) : '';
}

/** La date courte d'une Séance : « 6 oct. 2026 ». */
export const dateSeance = (date: string) => jourCourt.format(jour(date));

/** La Séance de l'en-tête : la prochaine si elle est annoncée, sinon la dernière ; `null` si aucune n'est connue. */
export function teteSeance(conseil: ConseilIndexe): { cle: string; prochaine: boolean } | null {
	if (conseil.prochaine_seance) return { cle: conseil.prochaine_seance, prochaine: true };
	if (conseil.derniere_seance) return { cle: conseil.derniere_seance, prochaine: false };
	return null;
}

/** Les Séances d'avant `aujourdhui` (AAAA-MM-JJ, à Lausanne), dans l'ordre de la liste : la plus récente d'abord. */
export function seancesPassees(seances: readonly LigneSeance[], aujourdhui: string): LigneSeance[] {
	return seances.filter((s) => s.date.slice(0, 10) < aujourdhui);
}
