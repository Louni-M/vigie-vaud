import { describe, expect, it } from 'vitest';
import { champDeSaisie, saisieDe } from './saisie.js';

const BOUTON = { tagName: 'BUTTON' };
const RECHERCHE = { tagName: 'INPUT', type: 'search' };

describe('saisie que trahit un évènement', () => {
	it('distingue le doigt du pointeur', () => {
		expect(saisieDe({ type: 'pointerdown', pointerType: 'touch' })).toBe('toucher');
		expect(saisieDe({ type: 'pointerdown', pointerType: 'mouse' })).toBe('pointeur');
		expect(saisieDe({ type: 'pointerdown', pointerType: 'pen' })).toBe('pointeur');
	});

	it('reconnaît un vrai clavier à une touche hors d’un champ de saisie', () => {
		expect(saisieDe({ type: 'keydown', cible: BOUTON })).toBe('clavier');
		expect(saisieDe({ type: 'keydown', cible: { tagName: 'INPUT', type: 'checkbox' } })).toBe('clavier');
		expect(saisieDe({ type: 'keydown', cible: null })).toBe('clavier');
	});

	it('ne tire rien d’une touche tapée dans un champ, qui peut venir du clavier de l’écran', () => {
		expect(saisieDe({ type: 'keydown', cible: RECHERCHE })).toBeNull();
		expect(saisieDe({ type: 'keydown', cible: { tagName: 'TEXTAREA' } })).toBeNull();
		expect(saisieDe({ type: 'keydown', cible: { tagName: 'DIV', isContentEditable: true } })).toBeNull();
	});
});

describe('champ de saisie', () => {
	it('reçoit du texte tapé : texte, recherche, et un <input> sans type', () => {
		expect(champDeSaisie(RECHERCHE)).toBe(true);
		expect(champDeSaisie({ tagName: 'INPUT' })).toBe(true);
		expect(champDeSaisie({ tagName: 'INPUT', type: 'email' })).toBe(true);
	});

	it('n’est ni un bouton, ni une case, ni un curseur', () => {
		expect(champDeSaisie(BOUTON)).toBe(false);
		expect(champDeSaisie({ tagName: 'INPUT', type: 'radio' })).toBe(false);
		expect(champDeSaisie({ tagName: 'INPUT', type: 'range' })).toBe(false);
		expect(champDeSaisie(null)).toBe(false);
	});
});
