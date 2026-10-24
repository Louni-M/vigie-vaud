import { describe, expect, it } from 'vitest';
import { cercleDeBulle, rayonDeBulle, repliSousLaBulle } from './bulle.js';

const PERMIS = { largeur: 360, hauteur: 604 };
const HOTELS = { largeur: 360, hauteur: 300 };
const FIL = { largeur: 380, hauteur: 604 };

describe('cercle de la bulle d’un volet', () => {
	it('part du centre de l’icône, avec son rayon', () => {
		const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
		expect(c).toMatchObject({ x: -46, y: 46, r0: 17 });
	});
	it('finit assez grand pour couvrir le coin le plus éloigné du volet', () => {
		const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
		expect(c.r1).toBeCloseTo(Math.hypot(360 + 46, 604 - 46));
	});
	it('ramène dans la hauteur du volet une icône plus basse que lui', () => {
		const c = cercleDeBulle({ largeur: 360, hauteur: 222 }, { x: -46, y: 256, rayon: 17 });
		expect(c.y).toBe(222 - 28);
	});
	it('garde la hauteur de l’icône quand le volet descend jusqu’à elle', () => {
		expect(cercleDeBulle(HOTELS, { x: -46, y: 256, rayon: 17 }).y).toBe(256);
	});
});

describe('rayon de la bulle pendant l’ouverture', () => {
	const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
	it('va du rayon de l’icône au rayon final', () => {
		expect(rayonDeBulle(0, c)).toBeCloseTo(17);
		expect(rayonDeBulle(1, c)).toBeCloseTo(c.r1);
	});
	it('ne découvre jamais plus de 9 % du disque final d’une image à l’autre, à 30 images par seconde', () => {
		// 600 ms à 30 images par seconde : 18 images, comme dans le navigateur de Claude Desktop.
		const aire = (t: number) => rayonDeBulle(t, c) ** 2 / c.r1 ** 2;
		const pas = Array.from({ length: 18 }, (_, i) => aire((i + 1) / 18) - aire(i / 18));
		expect(Math.max(...pas)).toBeLessThan(0.09);
	});
});

describe('repli de l’ancien volet sous la nouvelle bulle', () => {
	it('ne bouge pas au départ', () => {
		expect(repliSousLaBulle(0, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 0 });
	});
	it('finit à la taille du nouveau volet, avant la fin', () => {
		expect(repliSousLaBulle(0.85, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 304 });
		expect(repliSousLaBulle(1, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 304 });
	});
	it('replie aussi par la droite le fil, plus large qu’un volet', () => {
		expect(repliSousLaBulle(1, FIL, PERMIS)).toEqual({ droite: 20, bas: 0 });
	});
	it('ne replie rien sous un volet plus grand', () => {
		expect(repliSousLaBulle(1, HOTELS, PERMIS)).toEqual({ droite: 0, bas: 0 });
	});
});
