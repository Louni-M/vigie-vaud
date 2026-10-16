import { describe, expect, it } from 'vitest';
import { corrigerChemin, fermeture, mouvement } from './navigation.js';
import type { Fiche, Ouvert } from './types.js';

const VUE = { lat: 46.5, lon: 6.6, zoom: 13 };
const DOSSIER = { couche: 'permis', element: '248845' };
const AUTRE = { couche: 'permis', element: '250001' };

const PROPRE: Fiche = { fiche: 'propre' };
/** La fiche d'une commune, par son slug ; `null` : aucune fiche. */
const f = (commune: string | null): Fiche | null => (commune === null ? null : { commune });
/** Ce que reflétait l'adresse précédente. */
const avant = (fiche: string | Fiche | null, ouvert: Ouvert | null = null) => ({
	fiche: typeof fiche === 'string' ? f(fiche) : fiche,
	ouvert
});
const DEPART = avant(null);
/** L'adresse nouvelle : sa fiche, sa vue et son élément. */
const apres = (fiche: string | Fiche | null, vue: typeof VUE | null, ouvert: Ouvert | null) => ({
	fiche: typeof fiche === 'string' ? f(fiche) : fiche,
	vue,
	ouvert
});

describe('mouvement de la carte quand l’adresse change', () => {
	describe('à l’arrivée sur le site', () => {
		it('rétablit la vue partagée, qui l’emporte sur la commune et sur l’élément', () => {
			expect(mouvement(DEPART, apres('pully', VUE, null), true)).toEqual({ aller: VUE });
			expect(mouvement(DEPART, apres('lutry', VUE, DOSSIER), true)).toEqual({ aller: VUE });
		});
		it('cadre la fiche de l’adresse quand il n’y a pas de vue : la commune, ou la fiche propre', () => {
			expect(mouvement(DEPART, apres('pully', null, null), true)).toEqual({ cadrer: { commune: 'pully' } });
			expect(mouvement(DEPART, apres(PROPRE, null, null), true)).toEqual({ cadrer: PROPRE });
		});
		it('montre l’élément de l’adresse quand il n’y a pas de vue', () => {
			expect(mouvement(DEPART, apres(null, null, DOSSIER), true)).toBe('element');
			expect(mouvement(DEPART, apres('lutry', null, DOSSIER), true)).toBe('element');
		});
		it('laisse la carte sur sa vue de départ à l’adresse nue', () => {
			expect(mouvement(DEPART, apres(null, null, null), true)).toBeNull();
		});
	});

	describe('pendant la navigation', () => {
		it('cadre la commune qu’on vient d’ouvrir', () => {
			expect(mouvement(DEPART, apres('pully', null, null), false)).toEqual({ cadrer: { commune: 'pully' } });
			expect(mouvement(avant('lutry'), apres('pully', null, null), false)).toEqual({
				cadrer: { commune: 'pully' }
			});
		});
		it('va vers la fiche propre qu’on vient d’ouvrir, depuis la carte seule ou une commune', () => {
			expect(mouvement(DEPART, apres(PROPRE, null, null), false)).toEqual({ cadrer: PROPRE });
			expect(mouvement(avant('lutry'), apres(PROPRE, null, null), false)).toEqual({ cadrer: PROPRE });
			expect(mouvement(avant(PROPRE), apres('lutry', null, null), false)).toEqual({ cadrer: { commune: 'lutry' } });
		});
		it('ne bouge pas quand on ferme la fiche propre : l’adresse « / » garde la vue de la carte', () => {
			expect(mouvement(avant(PROPRE), apres(null, VUE, null), false)).toEqual({ aller: VUE });
		});
		it('ne bouge pas quand la fiche propre reste la même', () => {
			expect(mouvement(avant(PROPRE), apres(PROPRE, null, null), false)).toBeNull();
		});
		it('ne bouge pas quand on ferme un élément pour revenir à la fiche propre', () => {
			expect(mouvement(avant(PROPRE, DOSSIER), apres(PROPRE, null, null), false)).toBeNull();
		});
		it('rétablit la vue de l’entrée d’historique retrouvée', () => {
			expect(mouvement(avant('pully'), apres('lutry', VUE, null), false)).toEqual({ aller: VUE });
			expect(mouvement(avant('pully'), apres(null, VUE, null), false)).toEqual({ aller: VUE });
		});
		it('revient au canton à l’adresse nue « / »', () => {
			expect(mouvement(avant('pully'), apres(null, null, null), false)).toBe('canton');
			expect(mouvement(DEPART, apres(null, null, null), false)).toBe('canton');
		});
		it('ne bouge pas quand la commune reste la même', () => {
			expect(mouvement(avant('pully'), apres('pully', null, null), false)).toBeNull();
		});
		it('montre l’élément retrouvé par le précédent ou le suivant du navigateur', () => {
			expect(mouvement(avant('lutry'), apres('lutry', null, DOSSIER), false)).toBe('element');
			expect(mouvement(avant('lutry', AUTRE), apres('lutry', null, DOSSIER), false)).toBe(
				'element'
			);
		});
		it('ne bouge pas quand seul le chemin de l’élément ouvert est corrigé', () => {
			expect(mouvement(avant(null, DOSSIER), apres('lutry', null, DOSSIER), false)).toBeNull();
			expect(mouvement(avant('pully', DOSSIER), apres('lutry', null, DOSSIER), false)).toBeNull();
		});
		it('ne bouge pas quand on ferme l’élément pour revenir à l’onglet de sa commune, même vers une autre vue', () => {
			expect(mouvement(avant('lutry', DOSSIER), apres('lutry', null, null), false)).toBeNull();
			expect(mouvement(avant('lutry', DOSSIER), apres('lutry', VUE, null), false)).toBeNull();
		});
	});
});

describe('correction du chemin d’un élément ouvert', () => {
	const LUTRY = { commune: 'lutry' };
	const PULLY = { commune: 'pully' };
	const PROPRE = { fiche: 'propre' };

	it('mène à la fiche de l’élément depuis l’adresse nue ou une autre commune', () => {
		expect(corrigerChemin(null, { fiches: [LUTRY] })).toEqual(LUTRY);
		expect(corrigerChemin(PULLY, { fiches: [LUTRY] })).toEqual(LUTRY);
	});
	it('garde le chemin qui porte déjà la fiche de l’élément', () => {
		expect(corrigerChemin(LUTRY, { fiches: [LUTRY] })).toBeNull();
	});
	it('garde la fiche du chemin quand elle fait partie de celles de l’élément, même après la première', () => {
		expect(corrigerChemin(PULLY, { fiches: [LUTRY, PULLY, PROPRE] })).toBeNull();
		expect(corrigerChemin(PROPRE, { fiches: [LUTRY, PULLY, PROPRE] })).toBeNull();
	});
	it('mène à la première fiche de l’élément quand celle du chemin n’en fait pas partie', () => {
		expect(corrigerChemin({ commune: 'morges' }, { fiches: [LUTRY, PULLY, PROPRE] })).toEqual(LUTRY);
		expect(corrigerChemin(null, { fiches: [PROPRE, LUTRY] })).toEqual(PROPRE);
		expect(corrigerChemin({ commune: 'propre' }, { fiches: [LUTRY, PROPRE] })).toEqual(LUTRY);
	});
	it('retire l’élément que la couche ne trouve pas', () => {
		expect(corrigerChemin(PULLY, null)).toBe('retirer');
		expect(corrigerChemin(null, null)).toBe('retirer');
		expect(corrigerChemin(null, { fiches: [] })).toBe('retirer');
	});
});

describe('correction du chemin d’un élément du Grand Conseil, fiche propre de la couche Conseils', () => {
	const GC = { fiche: 'grand-conseil' };
	const LUTRY = { commune: 'lutry' };
	const PULLY = { commune: 'pully' };
	/** Ce que `localiser` donne pour une Séance ou un Objet sans commune, et pour un Objet qui nomme Lutry et Pully. */
	const SEANCE = { fiches: [GC] };
	const RATTACHE = { fiches: [LUTRY, PULLY, GC] };

	it('mène /?c=vd/2026-10-06 à /grand-conseil', () => {
		expect(corrigerChemin(null, SEANCE)).toEqual(GC);
		expect(corrigerChemin(PULLY, SEANCE)).toEqual(GC);
	});
	it('garde /grand-conseil?c=… dans la fiche du Grand Conseil, même pour un Objet qui nomme des communes', () => {
		expect(corrigerChemin(GC, SEANCE)).toBeNull();
		expect(corrigerChemin(GC, RATTACHE)).toBeNull();
	});
	it('garde un Objet dans une commune qu’il nomme, et le mène sinon à la première', () => {
		expect(corrigerChemin(PULLY, RATTACHE)).toBeNull();
		expect(corrigerChemin({ commune: 'morges' }, RATTACHE)).toEqual(LUTRY);
		expect(corrigerChemin(null, RATTACHE)).toEqual(LUTRY);
	});
	it('mène un élément d’un conseil communal hors de la fiche du Grand Conseil', () => {
		expect(corrigerChemin(GC, { fiches: [{ commune: 'lausanne' }] })).toEqual({ commune: 'lausanne' });
	});
});

describe('fermeture d’un élément', () => {
	const LUTRY = { commune: 'lutry' };
	const PROPRE = { fiche: 'propre' };

	it('revient en arrière quand l’application a ouvert l’élément depuis la même fiche', () => {
		expect(fermeture({ element: { depuis: { commune: 'lutry' } } }, LUTRY)).toBe('retour');
		expect(fermeture({ element: { depuis: { fiche: 'propre' } } }, PROPRE)).toBe('retour');
	});
	it('remplace l’adresse pour un élément ouvert par un lien direct', () => {
		expect(fermeture({}, LUTRY)).toBe('remplacer');
	});
	it('remplace l’adresse quand l’entrée précédente est une autre fiche ou la carte seule', () => {
		// Revenir en arrière quitterait la fiche où l'élément est ouvert au lieu de revenir à son onglet.
		expect(fermeture({ element: { depuis: { commune: 'pully' } } }, LUTRY)).toBe('remplacer');
		expect(fermeture({ element: { depuis: PROPRE } }, LUTRY)).toBe('remplacer');
		expect(fermeture({ element: { depuis: { commune: 'propre' } } }, PROPRE)).toBe('remplacer');
		expect(fermeture({ element: { depuis: null } }, LUTRY)).toBe('remplacer');
	});
});
