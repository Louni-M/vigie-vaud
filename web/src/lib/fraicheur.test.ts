import { describe, expect, it } from 'vitest';
import { libelleBadge, messageEchec } from './fraicheur.js';

/** Horloge fixée : 15 octobre 2026, 10 h UTC. */
const maintenant = new Date('2026-10-15T10:00:00Z');
const ilYa = (minutes: number) => new Date(maintenant.getTime() - minutes * 60_000);

const camac = { fraicheur: 'requete', nom_court: 'CAMAC' } as const;
const dgmr = { fraicheur: 'donnee', nom_court: 'DGMR' } as const;
const ucv = { fraicheur: 'millesime', nom_court: 'UCV' } as const;
const gc = { fraicheur: 'import', nom_court: 'Grand Conseil' } as const;

describe('libellé du badge de fraîcheur', () => {
	it('donne l’heure de la requête pour une source consultée en direct', () => {
		expect(libelleBadge(camac, { derniere: ilYa(2), erreur: null }, maintenant)).toBe('consulté il y a 2 min · CAMAC');
	});

	it('donne l’âge de la donnée elle-même', () => {
		expect(libelleBadge(dgmr, { derniere: ilYa(4), erreur: null }, maintenant)).toBe('il y a 4 min · DGMR');
	});

	it('donne l’édition d’une source préparée', () => {
		expect(libelleBadge(ucv, { derniere: 2025, erreur: null }, maintenant)).toBe('édition 2025 · UCV');
	});

	it('donne l’âge du dernier import réussi d’un conseil', () => {
		expect(libelleBadge(gc, { derniere: ilYa(6 * 60 + 10), erreur: null }, maintenant)).toBe(
			'importé il y a 6 h · Grand Conseil'
		);
	});

	it('dit le dernier import inconnu tant que import.json manque ou ne cite pas le conseil', () => {
		expect(libelleBadge(gc, { derniere: null, erreur: null }, maintenant)).toBe('dernier import inconnu · Grand Conseil');
	});

	it('passe des minutes aux heures puis aux jours', () => {
		const libelle = (minutes: number) => libelleBadge(dgmr, { derniere: ilYa(minutes), erreur: null }, maintenant);
		expect(libelle(0.5)).toBe('à l’instant · DGMR');
		expect(libelle(59)).toBe('il y a 59 min · DGMR');
		expect(libelle(60)).toBe('il y a 1 h · DGMR');
		expect(libelle(23 * 60 + 59)).toBe('il y a 23 h · DGMR');
		expect(libelle(3 * 24 * 60)).toBe('il y a 3 j · DGMR');
	});

	it('dit qu’une source n’a pas encore été obtenue', () => {
		expect(libelleBadge(camac, { derniere: null, erreur: null }, maintenant)).toBe('pas encore consulté · CAMAC');
		expect(libelleBadge(dgmr, { derniere: null, erreur: null }, maintenant)).toBe('pas encore chargé · DGMR');
		expect(libelleBadge(ucv, { derniere: null, erreur: null }, maintenant)).toBe('édition inconnue · UCV');
	});

	it('passe en erreur, hors ligne ou service indisponible, même après un succès', () => {
		expect(libelleBadge(camac, { derniere: ilYa(2), erreur: 'hors_ligne' }, maintenant)).toBe('hors ligne · CAMAC');
		expect(libelleBadge(camac, { derniere: null, erreur: 'indisponible' }, maintenant)).toBe(
			'service indisponible · CAMAC'
		);
	});
});

describe('message d’échec d’une source Direct', () => {
	const PERMIS = 'Les permis n’ont pas pu être chargés';
	// 12 h UTC = 14 h à Lausanne en octobre (heure d'été).
	const panne = { etat: 'en_panne', depuis: '2026-10-12T12:00:00Z' } as const;

	it('dit la panne constatée par la surveillance, avec sa date', () => {
		expect(messageEchec(PERMIS, 'indisponible', panne)).toBe('Source en panne depuis le 12 oct., 14 h.');
		expect(messageEchec(PERMIS, 'indisponible', { etat: 'en_panne', depuis: null })).toBe('Source en panne.');
	});

	it('donne le message de la couche et la cause vue du navigateur quand la surveillance n’a pas constaté de panne', () => {
		expect(messageEchec(PERMIS, 'indisponible', { etat: 'disponible' })).toBe(
			'Les permis n’ont pas pu être chargés : le service est indisponible pour le moment.'
		);
		expect(messageEchec(PERMIS, 'hors_ligne', { etat: 'inconnu' })).toBe(
			'Les permis n’ont pas pu être chargés : vous semblez hors ligne.'
		);
		// Un état périmé ne dit plus rien de la source.
		expect(messageEchec(PERMIS, 'indisponible', { etat: 'surveillance_interrompue' })).toBe(
			'Les permis n’ont pas pu être chargés : le service est indisponible pour le moment.'
		);
	});

	it('ne dit rien quand le navigateur a obtenu les données, même si le cron déclare la panne', () => {
		expect(messageEchec(PERMIS, null, panne)).toBeNull();
	});
});
