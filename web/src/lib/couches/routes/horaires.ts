import type { EtatRestriction } from './etats.js';

/**
 * Dates et heures d'une restriction de circulation, fonctions pures. `DATE_DEBUT` et `DATE_FIN` portent l'heure
 * locale codée comme de l'UTC : elles sont lues par leurs composantes UTC, comme une heure de Lausanne, sans
 * conversion de fuseau. Une heure 00:00 veut dire « jour entier » : rien n'en est déduit.
 */

/** Les champs de dates d'une restriction, tels que la DGMR les écrit. */
export interface Dates {
	dateDebut: number;
	dateFin: number;
	heureDebut: string | null;
	heureFin: string | null;
}

/** Un instant de la DGMR : son jour (AAAA-MM-JJ) et son heure (« HH:MM »), sans heure à 00:00. */
export interface Instant {
	jour: string;
	heure: string | null;
}

export function instant(ms: number): Instant {
	const iso = new Date(ms).toISOString();
	const heure = iso.slice(11, 16);
	return { jour: iso.slice(0, 10), heure: heure === '00:00' ? null : heure };
}

/** « 07:30 » → « 7 h 30 », « 19:00 » → « 19 h ». */
export function heureSuisse(hhmm: string): string {
	const [h, m] = hhmm.split(':');
	return m === '00' ? `${Number(h)} h` : `${Number(h)} h ${m}`;
}

/** La plage quotidienne, quand `HEURE_DEBUT` et `HEURE_FIN` sont remplies toutes deux. */
const plage = ({ heureDebut: a, heureFin: b }: Dates) => (a && b ? { debut: a, fin: b } : null);

// Les jours sont formatés en UTC : ce sont les composantes écrites par la DGMR.
const COURT = new Intl.DateTimeFormat('fr-CH', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
const SEMAINE = new Intl.DateTimeFormat('fr-CH', { weekday: 'long', timeZone: 'UTC' });
const LONG = new Intl.DateTimeFormat('fr-CH', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
const midi = (jour: string) => Date.parse(`${jour}T12:00:00Z`);
const jourCourt = (jour: string) => COURT.format(midi(jour));
const jourLong = (jour: string) => `${SEMAINE.format(midi(jour))} ${LONG.format(midi(jour))}`;

/**
 * « Du lun. 12 oct. à 7 h 30 au ven. 23 oct. », ou en toutes lettres pour la fiche (« Du lundi 12 octobre 2026 … »).
 * L'heure n'est écrite que si elle n'est pas 00:00, et jamais quand `HEURE_*` donnent la plage quotidienne : la
 * période ne dit alors que les jours (l'heure de `DATE_FIN` contredit parfois `HEURE_FIN`).
 */
export function periode(d: Dates, forme: 'courte' | 'longue' = 'courte'): string {
	const jour = forme === 'longue' ? jourLong : jourCourt;
	const [debut, fin] = [instant(d.dateDebut), instant(d.dateFin)];
	const avecHeure = !plage(d);
	const texte = (i: Instant) => (avecHeure && i.heure ? `${jour(i.jour)} à ${heureSuisse(i.heure)}` : jour(i.jour));
	if (debut.jour === fin.jour && (!avecHeure || (!debut.heure && !fin.heure))) return `Le ${jour(debut.jour)}`;
	return `Du ${texte(debut)} au ${texte(fin)}`;
}

/**
 * « Jour et nuit », ou la plage quotidienne de `HEURE_*` : « La nuit seulement, de 19 h 30 à 5 h 30 » quand elle
 * passe minuit, « Le jour seulement, de 8 h à 17 h » sinon.
 */
export function ligneHoraires(d: Dates): string {
	const p = plage(d);
	if (!p) return 'Jour et nuit';
	const quand = p.fin < p.debut ? 'La nuit seulement' : 'Le jour seulement';
	return `${quand}, de ${heureSuisse(p.debut)} à ${heureSuisse(p.fin)}`;
}

/** « Levée le week-end » quand `WEEK_END` vaut « non » (en casse libre) ; rien pour « oui » ou vide. */
export const leveeLeWeekEnd = (weekEnd: string | null): string | null =>
	weekEnd?.trim().toLowerCase() === 'non' ? 'Levée le week-end' : null;

/** Jours entre deux jours AAAA-MM-JJ. */
const joursEntre = (de: string, a: string) => Math.round((midi(a) - midi(de)) / 86_400_000);

/**
 * L'échéance, au jour près depuis `aujourdhui` (AAAA-MM-JJ, à Lausanne) : jusqu'à `DATE_FIN` pour l'en cours
 * (« encore 4 jours »), jusqu'à `DATE_DEBUT` pour l'à venir (« commence dans 10 jours »).
 */
export function echeance(r: Pick<Dates, 'dateDebut' | 'dateFin'> & { etat: EtatRestriction }, aujourdhui: string): string {
	if (r.etat === 'a_venir') {
		const n = joursEntre(aujourdhui, instant(r.dateDebut).jour);
		return n <= 0 ? 'commence aujourd’hui' : n === 1 ? 'commence demain' : `commence dans ${n} jours`;
	}
	const n = joursEntre(aujourdhui, instant(r.dateFin).jour);
	return n <= 0 ? 'dernier jour' : n === 1 ? 'jusqu’à demain' : `encore ${n} jours`;
}
