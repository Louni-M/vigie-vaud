import { describe, expect, it } from 'vitest';
import { heureLocale } from '#tests/faux-dgmr.js';
import { echeance, heureSuisse, instant, leveeLeWeekEnd, ligneHoraires, periode } from './horaires.js';

/*
 * Chaque table a une date d'été et une d'hiver : la suite tourne à l'heure de Lausanne, si bien qu'une heure DGMR
 * (heure locale codée comme de l'UTC) lue par erreur en heure locale y décale de 2 h l'été et de 1 h l'hiver.
 */

/** Les champs de dates d'une restriction, tels que la DGMR les écrit. */
const dates = (debut: string, fin: string, heureDebut: string | null = null, heureFin: string | null = null) => ({
	dateDebut: heureLocale(debut),
	dateFin: heureLocale(fin),
	heureDebut,
	heureFin
});

describe('lecture des dates de la DGMR, telles qu’écrites', () => {
	it.each([
		{ saison: 'été', ecrite: '2026-07-15T07:30', jour: '2026-07-15', heure: '07:30' },
		{ saison: 'hiver', ecrite: '2026-01-20T07:30', jour: '2026-01-20', heure: '07:30' },
		{ saison: 'été, en fin de soirée', ecrite: '2026-07-15T23:59', jour: '2026-07-15', heure: '23:59' },
		{ saison: 'hiver, en fin de soirée', ecrite: '2026-01-20T23:30', jour: '2026-01-20', heure: '23:30' }
	])('lit le jour et l’heure par leurs composantes UTC ($saison)', ({ ecrite, jour, heure }) => {
		expect(instant(heureLocale(ecrite))).toEqual({ jour, heure });
	});

	it.each([
		{ saison: 'été', ecrite: '2026-07-15', jour: '2026-07-15' },
		{ saison: 'hiver', ecrite: '2026-01-20', jour: '2026-01-20' }
	])('tient 00:00 pour un jour entier, sans heure ni jour déduits ($saison)', ({ ecrite, jour }) => {
		expect(instant(heureLocale(ecrite))).toEqual({ jour, heure: null });
	});
});

describe('heures en notation suisse', () => {
	it.each([
		['07:00', '7 h'],
		['07:30', '7 h 30'],
		['19:30', '19 h 30'],
		['05:05', '5 h 05'],
		['00:30', '0 h 30'],
		['12:00', '12 h']
	])('écrit %s « %s »', (hhmm, attendu) => {
		expect(heureSuisse(hhmm)).toBe(attendu);
	});
});

describe('période', () => {
	it.each([
		{ saison: 'été', d: dates('2026-07-13', '2026-07-24'), attendu: 'Du lun. 13 juil. au ven. 24 juil.' },
		{ saison: 'hiver', d: dates('2026-01-12', '2026-01-23'), attendu: 'Du lun. 12 janv. au ven. 23 janv.' },
		{ saison: 'été', d: dates('2026-07-13T07:30', '2026-07-24T17:00'), attendu: 'Du lun. 13 juil. à 7 h 30 au ven. 24 juil. à 17 h' },
		{ saison: 'hiver', d: dates('2026-01-12T07:30', '2026-01-23T17:00'), attendu: 'Du lun. 12 janv. à 7 h 30 au ven. 23 janv. à 17 h' },
		{ saison: 'été', d: dates('2026-07-14', '2026-07-14'), attendu: 'Le mar. 14 juil.' }
	])('écrit les jours, et l’heure quand elle n’est pas 00:00 ($saison) : « $attendu »', ({ d, attendu }) => {
		expect(periode(d)).toBe(attendu);
	});

	it.each([
		{ saison: 'été', d: dates('2026-07-13', '2026-07-24'), attendu: 'Du lundi 13 juillet 2026 au vendredi 24 juillet 2026' },
		{ saison: 'hiver', d: dates('2026-01-12T07:00', '2026-01-23'), attendu: 'Du lundi 12 janvier 2026 à 7 h au vendredi 23 janvier 2026' }
	])('s’écrit en toutes lettres pour la fiche ($saison)', ({ d, attendu }) => {
		expect(periode(d, 'longue')).toBe(attendu);
	});

	it.each([
		{ saison: 'été', d: dates('2026-07-27T19:30', '2026-07-30T23:59', '19:30', '05:30'), attendu: 'Du lun. 27 juil. au jeu. 30 juil.' },
		{ saison: 'hiver', d: dates('2026-01-26T19:30', '2026-01-29T23:59', '19:30', '05:30'), attendu: 'Du lun. 26 janv. au jeu. 29 janv.' },
		{ saison: 'hiver, fin à 00:00', d: dates('2026-01-26', '2026-01-30', '20:00', '05:30'), attendu: 'Du lun. 26 janv. au ven. 30 janv.' }
	])('ne donne que les jours quand HEURE_* donnent la plage, même si DATE_FIN la contredit ($saison)', ({ d, attendu }) => {
		expect(periode(d)).toBe(attendu);
	});
});

describe('ligne d’horaires', () => {
	it.each([
		{ saison: 'été', d: dates('2026-07-13', '2026-07-24'), attendu: 'Jour et nuit' },
		{ saison: 'hiver', d: dates('2026-01-12T07:30', '2026-01-23T17:00'), attendu: 'Jour et nuit' },
		{ saison: 'été', d: dates('2026-07-27T19:30', '2026-07-30T05:30', '19:30', '05:30'), attendu: 'La nuit seulement, de 19 h 30 à 5 h 30' },
		{ saison: 'hiver', d: dates('2026-01-26T20:00', '2026-01-30T05:00', '20:00', '05:00'), attendu: 'La nuit seulement, de 20 h à 5 h' },
		{ saison: 'été', d: dates('2026-07-13', '2026-07-24', '08:00', '17:00'), attendu: 'Le jour seulement, de 8 h à 17 h' },
		{ saison: 'hiver', d: dates('2026-01-12', '2026-01-23', '19:30', null), attendu: 'Jour et nuit' }
	])('« $attendu » ($saison)', ({ d, attendu }) => {
		expect(ligneHoraires(d)).toBe(attendu);
	});

	it.each([
		{ saison: 'été', d: dates('2026-07-27T19:30', '2026-07-30T23:59', '19:30', '05:30') },
		{ saison: 'hiver', d: dates('2026-01-26T19:30', '2026-01-29T23:59', '19:30', '05:30') }
	])('prend la plage dans HEURE_* quand HEURE_FIN contredit l’heure de DATE_FIN ($saison)', ({ d }) => {
		expect(ligneHoraires(d)).toBe('La nuit seulement, de 19 h 30 à 5 h 30');
	});
});

describe('week-end', () => {
	it.each(['non', 'Non', 'NON'])('« Levée le week-end » pour « %s »', (weekEnd) => {
		expect(leveeLeWeekEnd(weekEnd)).toBe('Levée le week-end');
	});

	it.each(['Oui', 'oui', null])('rien pour « %s »', (weekEnd) => {
		expect(leveeLeWeekEnd(weekEnd)).toBeNull();
	});
});

describe('échéance', () => {
	it.each([
		{ saison: 'été', aujourdhui: '2026-07-20', fin: '2026-07-24', attendu: 'encore 4 jours' },
		{ saison: 'hiver', aujourdhui: '2026-01-19', fin: '2026-01-23T17:00', attendu: 'encore 4 jours' },
		{ saison: 'été', aujourdhui: '2026-07-23', fin: '2026-07-24', attendu: 'jusqu’à demain' },
		{ saison: 'hiver', aujourdhui: '2026-01-23', fin: '2026-01-23', attendu: 'dernier jour' }
	])('« $attendu » pour l’en cours, jusqu’à DATE_FIN ($saison)', ({ aujourdhui, fin, attendu }) => {
		expect(echeance({ etat: 'en_cours', ...dates('2026-01-01', fin) }, aujourdhui)).toBe(attendu);
	});

	it.each([
		{ saison: 'été', aujourdhui: '2026-07-17', debut: '2026-07-27T19:30', attendu: 'commence dans 10 jours' },
		{ saison: 'hiver', aujourdhui: '2026-01-16', debut: '2026-01-26', attendu: 'commence dans 10 jours' },
		// Hiver à été : le passage à l'heure d'été ne décale pas le compte des jours.
		{ saison: 'au passage à l’heure d’été', aujourdhui: '2026-03-25', debut: '2026-04-04', attendu: 'commence dans 10 jours' },
		{ saison: 'été', aujourdhui: '2026-07-26', debut: '2026-07-27T19:30', attendu: 'commence demain' },
		{ saison: 'hiver', aujourdhui: '2026-01-26', debut: '2026-01-26T20:00', attendu: 'commence aujourd’hui' }
	])('« $attendu » pour l’à venir, au jour près ($saison)', ({ aujourdhui, debut, attendu }) => {
		expect(echeance({ etat: 'a_venir', ...dates(debut, '2026-12-31') }, aujourdhui)).toBe(attendu);
	});
});
