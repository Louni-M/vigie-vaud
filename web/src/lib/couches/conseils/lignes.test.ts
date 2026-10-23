import { describe, expect, it } from 'vitest';
import {
	auteursObjet,
	contenuTete,
	dateObjet,
	detailSeance,
	filtrerObjets,
	nomSeance,
	PUCES_OBJETS, ordreDuJour,
	seancesPassees,
	siteDuLien,
	teteSeance
} from './lignes.js';
import { conseilLausanne, conseilYverdon, ligneObjet, seance } from '#tests/faux-conseils.js';
import type { LigneSeance } from '#lib/schema.js';

describe('nom composé d’une Séance', () => {
	it('se compose de sa date : « Séance du mardi 6 octobre 2026 »', () => {
		expect(nomSeance('2026-10-06')).toBe('Séance du mardi 6 octobre 2026');
	});

	it('donne l’heure quand elle est connue, et le premier du mois en toutes lettres', () => {
		expect(nomSeance('2026-10-01T20:00')).toBe('Séance du jeudi 1er octobre 2026 à 20 h');
		expect(nomSeance('2026-10-06T19:30')).toBe('Séance du mardi 6 octobre 2026 à 19 h 30');
	});
});

describe('ligne d’Objet', () => {
	it('donne les auteur·e·s avec leur parti', () => {
		expect(auteursObjet(ligneObjet())).toBe('Alice Martin (PS)');
	});

	it('en donne deux, puis « et al. »', () => {
		const ligne = ligneObjet({
			auteurs: [
				{ nom: 'Alice Martin', parti: 'PS' },
				{ nom: 'Bruno Favre', parti: null }
			],
			nombre_auteurs: 5
		});
		expect(auteursObjet(ligne)).toBe('Alice Martin (PS), Bruno Favre et al.');
	});

	it('ne donne personne pour une pétition', () => {
		expect(auteursObjet(ligneObjet({ auteurs: [], nombre_auteurs: 0 }))).toBe('');
	});

	it('date l’Objet de son dépôt, sinon de sa dernière étape', () => {
		expect(dateObjet(ligneObjet({ depose: '2026-10-06' }))).toBe('6 oct. 2026');
		expect(dateObjet(ligneObjet({ depose: null, derniere_etape: '2025-03-01' }))).toBe('1 mars 2025');
		expect(dateObjet(ligneObjet({ depose: null, derniere_etape: null }))).toBe('');
	});
});

describe('en-tête de séance', () => {
	it('montre la prochaine Séance si elle est annoncée', () => {
		expect(teteSeance(conseilLausanne())).toEqual({ cle: '5586/2026-10-20', prochaine: true });
	});

	it('sinon la dernière', () => {
		expect(teteSeance(conseilYverdon())).toEqual({ cle: '5938/2026-10-01', prochaine: false });
	});

	it('rien pour un conseil sans Séance connue', () => {
		expect(teteSeance(conseilYverdon({ derniere_seance: null }))).toBeNull();
	});
});

describe('ligne d’une Séance', () => {
	const odj = { titre: 'Ordre du jour', date: '2026-10-01', lien: 'https://www.bussigny.ch/odj.pdf' };
	const pv = { titre: null, date: null, lien: 'https://www.bussigny.ch/pv.pdf' };

	it('donne son nombre de points après sa date', () => {
		expect(detailSeance({ cle: '5586/2026-10-06', date: '2026-10-06', points: 1 })).toEqual({ points: '1 point' });
		expect(detailSeance({ cle: '5586/2026-10-06', date: '2026-10-06', points: 12 })).toEqual({ points: '12 points' });
	});

	it('sans points, montre ses documents en lien à la place du nombre de points', () => {
		const ligne: LigneSeance = { cle: '5624/2026-11-03', date: '2026-11-03', points: 0, documents: [odj, pv] };
		expect(detailSeance(ligne)).toEqual({
			documents: [
				{ texte: 'Ordre du jour', lien: 'https://www.bussigny.ch/odj.pdf' },
				{ texte: 'Document', lien: 'https://www.bussigny.ch/pv.pdf' }
			]
		});
	});

	it('sans points ni documents, reste à « 0 points »', () => {
		expect(detailSeance({ cle: '5938/2026-10-01', date: '2026-10-01', points: 0 })).toEqual({ points: '0 points' });
	});
});

describe('contenu de l’en-tête de séance', () => {
	const odj = { titre: 'Ordre du jour', date: '2026-10-01', lien: 'https://www.bussigny.ch/odj.pdf' };

	it('donne les 5 premiers points de l’ordre du jour, et leur nombre', () => {
		const points = Array.from({ length: 7 }, (_, i) => ({
			numero: String(i + 1),
			titre: `Point ${i + 1}`,
			categorie: null,
			resultat: null,
			objet: null
		}));
		const contenu = contenuTete(seance({ ordre_du_jour: points, documents: [odj] }));
		expect(contenu).toEqual({ points: points.slice(0, 5), total: 7 });
	});

	it('sans points, montre les documents de la Séance en lien', () => {
		expect(contenuTete(seance({ ordre_du_jour: [], documents: [odj] }))).toEqual({
			documents: [{ texte: 'Ordre du jour', lien: 'https://www.bussigny.ch/odj.pdf' }]
		});
	});

	it('sans points ni documents, rien : l’ordre du jour n’est pas encore publié', () => {
		expect(contenuTete(seance({ ordre_du_jour: [] }))).toBeNull();
	});
});

describe('Séances passées', () => {
	const ligne = (date: string): LigneSeance => ({ cle: `5586/${date.slice(0, 10)}`, date, points: 3 });

	it('garde celles d’avant aujourd’hui, de la plus récente à la plus ancienne', () => {
		const seances = [ligne('2026-11-03'), ligne('2026-10-20T19:30'), ligne('2026-10-16'), ligne('2026-10-06T19:30')];
		expect(seancesPassees(seances, '2026-10-16').map((s) => s.cle)).toEqual(['5586/2026-10-06']);
	});
});

describe('ordre du jour d’une Séance', () => {
	const point = (titre: string, categorie: string | null) => ({
		numero: null,
		titre,
		categorie,
		resultat: null,
		objet: null
	});

	it('regroupe les points qui se suivent sous leur catégorie, dans l’ordre de la source', () => {
		const groupes = ordreDuJour([
			point('Communications', null),
			point('Postulat A', 'Postulats'),
			point('Postulat B', 'Postulats'),
			point('Interpellation C', 'Interpellations'),
			point('Postulat D', 'Postulats')
		]);

		expect(groupes.map((g) => [g.categorie, g.points.map((p) => p.titre)])).toEqual([
			[null, ['Communications']],
			['Postulats', ['Postulat A', 'Postulat B']],
			['Interpellations', ['Interpellation C']],
			['Postulats', ['Postulat D']]
		]);
	});
});

describe('lien vers le site du conseil', () => {
	it('nomme le site par son hôte, sans « www. » : « Voir sur lausanne.ch › »', () => {
		expect(siteDuLien('https://www.lausanne.ch/officiel/conseil-communal/objet.html')).toBe('lausanne.ch');
		expect(siteDuLien('https://www.vd.ch/gc/objet?id=1')).toBe('vd.ch');
	});
});

describe('puces des Objets récents du Grand Conseil', () => {
	const sans = ligneObjet({ cle: 'vd/26_INT_140' });
	const lutry = ligneObjet({ cle: 'vd/26_MOT_12', communes: [{ ofs: 5606, origine: 'titre' }] });
	const pully = ligneObjet({ cle: 'vd/26_POS_3', communes: [{ ofs: 5590, origine: 'document' }] });
	const objets = [sans, lutry, pully];

	it('s’appellent « Tous · Nomment une commune · Sans commune »', () => {
		expect(PUCES_OBJETS.map((p) => p.nom)).toEqual(['Tous', 'Nomment une commune', 'Sans commune']);
	});
	it('filtrent les Objets par leurs communes rattachées, dans leur ordre', () => {
		expect(filtrerObjets(objets, 'tous')).toEqual([sans, lutry, pully]);
		expect(filtrerObjets(objets, 'avec')).toEqual([lutry, pully]);
		expect(filtrerObjets(objets, 'sans')).toEqual([sans]);
	});
});
