import { describe, expect, it } from 'vitest';
import { lignesDe, longueur, milieu, type Point } from './trace.js';

/*
 * Les cas suivent un méridien ou un parallèle : la mi-longueur s'y lit sur les degrés, sans calcul de distance.
 */
describe('milieu du tracé', () => {
	const cas: { nom: string; lignes: Point[][]; attendu: Point }[] = [
		{
			nom: 'un segment : son milieu',
			lignes: [[[6.6, 46.5], [6.7, 46.5]]],
			attendu: [6.65, 46.5]
		},
		{
			nom: 'à mi-longueur, pas au sommet du milieu',
			lignes: [[[6.6, 46.5], [6.6, 46.51], [6.6, 46.52], [6.6, 46.53], [6.6, 46.9]]],
			attendu: [6.6, 46.7]
		},
		{
			nom: 'sur un sommet quand il tombe à mi-longueur',
			lignes: [[[6.6, 46.5], [6.6, 46.6], [6.6, 46.7]]],
			attendu: [6.6, 46.6]
		},
		{
			nom: 'MultiLineString : dans le morceau où tombe la mi-longueur, sans compter les sauts entre morceaux',
			lignes: [
				[[6.6, 46.5], [6.6, 46.6]],
				[[6.7, 46.5], [6.7, 46.8]]
			],
			attendu: [6.7, 46.6]
		},
		{
			nom: 'MultiLineString : dans le premier morceau quand il est le plus long',
			lignes: [
				[[6.6, 46.5], [6.6, 46.9]],
				[[6.8, 46.5], [6.8, 46.6]],
				[[6.9, 46.5], [6.9, 46.6]]
			],
			attendu: [6.6, 46.8]
		},
		{
			nom: 'un tracé réduit à un point : ce point',
			lignes: [[[6.6, 46.5], [6.6, 46.5]]],
			attendu: [6.6, 46.5]
		}
	];

	it.each(cas)('$nom', ({ lignes, attendu }) => {
		const [lon, lat] = milieu(lignes);
		expect(lon).toBeCloseTo(attendu[0], 9);
		expect(lat).toBeCloseTo(attendu[1], 9);
	});
});

describe('longueur du tracé', () => {
	it('compte un degré de latitude pour environ 111,2 km, et les morceaux bout à bout', () => {
		expect(longueur([[[6.6, 46.5], [6.6, 46.6]]])).toBeCloseTo(11_119.5, 0);
		expect(
			longueur([
				[[6.6, 46.5], [6.6, 46.6]],
				[[6.7, 46.5], [6.7, 46.6]]
			])
		).toBeCloseTo(22_239, 0);
	});

	it('raccourcit un degré de longitude selon la latitude', () => {
		// cos(46,5°) × 111,195 km par degré, sur 0,1°.
		expect(longueur([[[6.6, 46.5], [6.7, 46.5]]])).toBeCloseTo(7_654, 0);
	});
});

describe('lignes d’une géométrie', () => {
	it('lit une LineString comme une seule ligne, et une MultiLineString telle quelle', () => {
		const a: Point[] = [[6.6, 46.5], [6.7, 46.5]];
		const b: Point[] = [[6.8, 46.5], [6.9, 46.5]];
		expect(lignesDe({ type: 'LineString', coordinates: a })).toEqual([a]);
		expect(lignesDe({ type: 'MultiLineString', coordinates: [a, b] })).toEqual([a, b]);
	});
});
