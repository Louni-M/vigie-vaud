import { describe, expect, it } from 'vitest';
import { affichageApres, affichageArrivee, decalageAuDessus, recherchePleine, texteApresRecherche } from './telephone.js';

const RIEN = { fiche: null, element: null };
const PULLY = { fiche: 'commune:pully', element: null };
const DOSSIER = { fiche: 'commune:lutry', element: 'permis:248845' };
const GRAND_CONSEIL = { fiche: 'fiche:grand-conseil', element: null };
const SEANCE = { fiche: 'fiche:grand-conseil', element: 'conseils:vd/2026-10-06' };

describe('vue affichée sur téléphone quand ce qui est ouvert change', () => {
	it('quitte la vue Fiche pour la carte quand plus rien n’est ouvert', () => {
		expect(affichageApres('fiche', PULLY, RIEN)).toBe('carte');
		expect(affichageApres('fiche', GRAND_CONSEIL, RIEN)).toBe('carte');
	});
	it('revient à la carte quand on ouvre un dossier depuis la liste de la vue Couches, pour son aperçu', () => {
		expect(affichageApres('couches', RIEN, DOSSIER)).toBe('carte');
		expect(affichageApres('couches', PULLY, DOSSIER)).toBe('carte');
	});
	it('revient à la carte quand on ouvre une entrée depuis la vue Fil, pour son aperçu', () => {
		expect(affichageApres('fil', RIEN, DOSSIER)).toBe('carte');
		expect(affichageApres('fil', RIEN, SEANCE)).toBe('carte');
	});
	it('reste sur la fiche quand on y ouvre ou ferme un dossier, ou qu’on change de commune', () => {
		const pullyDossier = { fiche: 'commune:pully', element: 'permis:250001' };
		expect(affichageApres('fiche', PULLY, pullyDossier)).toBe('fiche');
		expect(affichageApres('fiche', pullyDossier, PULLY)).toBe('fiche');
		expect(affichageApres('fiche', PULLY, DOSSIER)).toBe('fiche');
		expect(affichageApres('fiche', GRAND_CONSEIL, SEANCE)).toBe('fiche');
	});
	it('reste sur la carte, où l’aperçu montre ce qu’on vient d’ouvrir, commune ou fiche du Grand Conseil', () => {
		expect(affichageApres('carte', RIEN, PULLY)).toBe('carte');
		expect(affichageApres('carte', PULLY, DOSSIER)).toBe('carte');
		expect(affichageApres('carte', RIEN, GRAND_CONSEIL)).toBe('carte');
	});
	it('reste sur la vue Couches ou Fil quand rien de nouveau ne s’ouvre', () => {
		expect(affichageApres('couches', DOSSIER, { fiche: 'commune:lutry', element: null })).toBe('couches');
		expect(affichageApres('couches', PULLY, RIEN)).toBe('couches');
		expect(affichageApres('fil', PULLY, RIEN)).toBe('fil');
	});
});

describe('vue affichée à l’arrivée sur téléphone', () => {
	it('montre la fiche quand on arrive sur celle d’une commune ou sur /grand-conseil', () => {
		expect(affichageArrivee(PULLY)).toBe('fiche');
		expect(affichageArrivee(GRAND_CONSEIL)).toBe('fiche');
		expect(affichageArrivee(SEANCE)).toBe('fiche');
	});
	it('montre la carte quand on arrive sur la carte seule', () => {
		expect(affichageArrivee(RIEN)).toBe('carte');
	});
});

describe('décalage d’un dossier vers lequel la carte vole sur téléphone', () => {
	it('le remonte au milieu de la bande libre entre la recherche et l’aperçu', () => {
		// Recherche sur les 60 px du haut, aperçu sur les 180 px du bas : la bande libre est centrée 60 px plus haut.
		expect(decalageAuDessus(60, 180)).toBe(60);
	});
	it('ne le décale pas quand le haut et le bas sont couverts autant l’un que l’autre', () => {
		expect(decalageAuDessus(80, 80)).toBe(0);
	});
});

describe('Recherche plein écran sur téléphone', () => {
	it('s’affiche par-dessus la vue Carte une fois ouverte', () => {
		expect(recherchePleine(true, 'carte', true)).toBe(true);
		expect(recherchePleine(true, 'carte', false)).toBe(false);
	});
	it('ne s’ouvre que depuis la vue Carte', () => {
		expect(recherchePleine(true, 'fil', true)).toBe(false);
		expect(recherchePleine(true, 'couches', true)).toBe(false);
		expect(recherchePleine(true, 'fiche', true)).toBe(false);
	});
	it('ne s’ouvre jamais sur bureau, ni au-delà de 760 px de large', () => {
		expect(recherchePleine(false, 'carte', true)).toBe(false);
	});
});

describe('texte du champ de la carte quand la Recherche se referme', () => {
	it('« Annuler » et le retour arrière effacent ce qu’on a tapé et rendent le champ d’avant l’ouverture', () => {
		expect(texteApresRecherche('annuler', '', 'pull')).toBe('');
		expect(texteApresRecherche('retour', '', 'pull')).toBe('');
		expect(texteApresRecherche('annuler', 'Pully', 'Lutry')).toBe('Pully');
		expect(texteApresRecherche('retour', 'Pully', '')).toBe('Pully');
	});
	it('choisir un résultat laisse son nom dans le champ, comme sur bureau', () => {
		expect(texteApresRecherche('choix', '', 'Bourg-en-Lavaux')).toBe('Bourg-en-Lavaux');
		expect(texteApresRecherche('choix', 'Pully', 'Avenue de Lavaux 1, 1009 Pully')).toBe(
			'Avenue de Lavaux 1, 1009 Pully'
		);
	});
});
