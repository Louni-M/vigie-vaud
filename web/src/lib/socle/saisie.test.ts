import { describe, expect, it } from 'vitest';
import { saisieDe } from './saisie.js';

describe('saisie que trahit un évènement', () => {
	it('distingue le doigt du pointeur', () => {
		expect(saisieDe({ type: 'pointerdown', pointerType: 'touch' })).toBe('toucher');
		expect(saisieDe({ type: 'pointerdown', pointerType: 'mouse' })).toBe('pointeur');
		expect(saisieDe({ type: 'pointerdown', pointerType: 'pen' })).toBe('pointeur');
	});

	it('reconnaît un vrai clavier à ses touches nommées', () => {
		expect(saisieDe({ type: 'keydown', key: 'Escape' })).toBe('clavier');
		expect(saisieDe({ type: 'keydown', key: 'p' })).toBe('clavier');
	});

	it('laisse au toucher les touches sans nom d’un clavier à l’écran', () => {
		expect(saisieDe({ type: 'keydown', key: 'Unidentified' })).toBeNull();
		expect(saisieDe({ type: 'keydown', key: 'Process' })).toBeNull();
	});
});
