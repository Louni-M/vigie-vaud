import { describe, expect, it } from 'vitest';
import {
	affichageApres,
	affichageArrivee,
	affichageDeLAdresse,
	affichageOuverture,
	decalageAuDessus,
	lireAffichage,
	recherchePleine,
	texteApresRecherche
} from './telephone.js';

const RIEN = { fiche: null, element: null };
const PULLY = { fiche: 'commune:pully', element: null };
const DOSSIER = { fiche: 'commune:lutry', element: 'permis:248845' };
const GRAND_CONSEIL = { fiche: 'fiche:grand-conseil', element: null };
const SEANCE = { fiche: 'fiche:grand-conseil', element: 'conseils:vd/2026-10-06' };

describe('vue affichée sur téléphone quand ce qui est ouvert change', () => {
	it('quitte la vue Fiche pour la vue d’où la fiche a été ouverte quand plus rien n’est ouvert', () => {
		expect(affichageApres('fiche', PULLY, RIEN, 'panneau')).toBe('panneau');
		expect(affichageApres('fiche', GRAND_CONSEIL, RIEN, 'carte')).toBe('carte');
	});
	it('passe du panneau à la carte quand on ouvre un élément depuis une liste, pour son aperçu', () => {
		expect(affichageApres('panneau', RIEN, DOSSIER, 'panneau')).toBe('carte');
		expect(affichageApres('panneau', PULLY, DOSSIER, 'panneau')).toBe('carte');
		expect(affichageApres('panneau', RIEN, SEANCE, 'panneau')).toBe('carte');
	});
	it('passe du panneau à la fiche quand on y ouvre une fiche, sans élément', () => {
		expect(affichageApres('panneau', RIEN, PULLY, 'panneau')).toBe('fiche');
		expect(affichageApres('panneau', RIEN, GRAND_CONSEIL, 'panneau')).toBe('fiche');
	});
	it('reste sur la fiche quand on y ouvre ou ferme un dossier, ou qu’on change de commune', () => {
		const pullyDossier = { fiche: 'commune:pully', element: 'permis:250001' };
		expect(affichageApres('fiche', PULLY, pullyDossier, 'carte')).toBe('fiche');
		expect(affichageApres('fiche', pullyDossier, PULLY, 'carte')).toBe('fiche');
		expect(affichageApres('fiche', PULLY, DOSSIER, 'carte')).toBe('fiche');
		expect(affichageApres('fiche', GRAND_CONSEIL, SEANCE, 'carte')).toBe('fiche');
	});
	it('reste sur la carte, où l’aperçu montre ce qu’on vient d’ouvrir, commune ou fiche du Grand Conseil', () => {
		expect(affichageApres('carte', RIEN, PULLY, 'carte')).toBe('carte');
		expect(affichageApres('carte', PULLY, DOSSIER, 'carte')).toBe('carte');
		expect(affichageApres('carte', RIEN, GRAND_CONSEIL, 'carte')).toBe('carte');
	});
	it('reste sur le panneau quand rien de nouveau ne s’ouvre', () => {
		expect(affichageApres('panneau', DOSSIER, { fiche: 'commune:lutry', element: null }, 'panneau')).toBe('panneau');
		expect(affichageApres('panneau', PULLY, RIEN, 'panneau')).toBe('panneau');
	});
});

describe('vue affichée à l’arrivée sur téléphone', () => {
	it('montre la fiche quand on arrive sur celle d’une commune ou sur /grand-conseil', () => {
		expect(affichageArrivee(PULLY, false)).toBe('fiche');
		expect(affichageArrivee(GRAND_CONSEIL, true)).toBe('fiche');
		expect(affichageArrivee(SEANCE, false)).toBe('fiche');
	});
	it('montre la carte quand l’adresse ouvre un élément ou nomme une vue de la carte', () => {
		expect(affichageArrivee({ fiche: null, element: 'permis:248845' }, false)).toBe('carte');
		expect(affichageArrivee(RIEN, true)).toBe('carte');
	});
	it('montre le panneau sinon', () => {
		expect(affichageArrivee(RIEN, false)).toBe('panneau');
	});
});

describe('vue affichée dès qu’on ouvre un élément', () => {
	it('passe du panneau à la carte, pour l’aperçu', () => {
		expect(affichageOuverture('panneau')).toBe('carte');
	});
	it('reste sur la carte ou la fiche', () => {
		expect(affichageOuverture('carte')).toBe('carte');
		expect(affichageOuverture('fiche')).toBe('fiche');
	});
});

describe('vue que donne l’adresse', () => {
	it('suit la requête (`affichage=panneau`)', () => {
		expect(affichageDeLAdresse('panneau', RIEN, true)).toBe('panneau');
		expect(affichageDeLAdresse('carte', PULLY, false)).toBe('carte');
	});
	it('prend celle de l’arrivée quand la requête n’en dit rien', () => {
		expect(affichageDeLAdresse(null, RIEN, false)).toBe('panneau');
		expect(affichageDeLAdresse(null, RIEN, true)).toBe('carte');
		expect(affichageDeLAdresse(null, PULLY, true)).toBe('fiche');
	});
	it('prend celle de l’arrivée pour « Fiche » sans fiche ouverte', () => {
		expect(affichageDeLAdresse('fiche', RIEN, false)).toBe('panneau');
		expect(affichageDeLAdresse('fiche', RIEN, true)).toBe('carte');
	});
});

describe('vue lue dans l’adresse', () => {
	it('lit les anciennes vues Fil et Couches comme le panneau', () => {
		expect(lireAffichage('fil')).toBe('panneau');
		expect(lireAffichage('couches')).toBe('panneau');
	});
	it('lit les vues connues, et rien pour une autre', () => {
		expect(lireAffichage('carte')).toBe('carte');
		expect(lireAffichage('panneau')).toBe('panneau');
		expect(lireAffichage('fiche')).toBe('fiche');
		expect(lireAffichage('plan')).toBeNull();
		expect(lireAffichage(null)).toBeNull();
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
	it('s’affiche par-dessus la vue Carte ou le panneau une fois ouverte', () => {
		expect(recherchePleine(true, 'carte', true)).toBe(true);
		expect(recherchePleine(true, 'panneau', true)).toBe(true);
		expect(recherchePleine(true, 'carte', false)).toBe(false);
	});
	it('ne s’ouvre pas depuis la vue Fiche, qui n’a pas de recherche', () => {
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
