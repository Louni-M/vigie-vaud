import { describe, expect, it } from 'vitest';
import type { Limites } from '#lib/socle/communes.js';
import { carre, commune } from '#tests/faux-canton.js';
import { rattacher, type CommuneLimitee } from './rattachement.js';
import type { Geometrie, Point } from './trace.js';

/*
 * Communes carrées fabriquées, côte à côte le long du parallèle 46,5° : sur ce parallèle, 0,01° de longitude font
 * environ 765 m (765,4 m sur une sphère de 6371 km), et 0,01° de latitude environ 1112 m (1111,9 m). Aucun jeu réel
 * (norme DCG 8401).
 */
const limitee = (bfs: number, nom: string, bbox: [number, number, number, number], limites?: Limites): CommuneLimitee => ({
	commune: commune(bfs, nom, bbox),
	limites: limites ?? carre(bbox)
});

const AVENCHES = limitee(1, 'Avenches', [6.6, 46.49, 6.61, 46.51]);
const BEX = limitee(2, 'Bex', [6.61, 46.49, 6.62, 46.51]);
const COPPET = limitee(3, 'Coppet', [6.62, 46.49, 6.63, 46.51]);

/** Mètres par 0,001° de longitude sur le parallèle 46,5°. */
const M = 76.54;

const ligne = (...points: Point[]): Geometrie => ({ type: 'LineString', coordinates: points });
const resume = (passages: ReturnType<typeof rattacher>) => passages.map((p) => [p.commune.nom, Math.round(p.metres)]);

describe('rattachement d’une restriction aux communes', () => {
	it('rattache à sa seule commune un tracé qui y reste', () => {
		const passages = rattacher(ligne([6.602, 46.5], [6.607, 46.5]), [AVENCHES, BEX]);
		expect(resume(passages)).toEqual([['Avenches', Math.round(5 * M)]]);
	});

	it('range deux communes de la plus grande longueur parcourue à la plus petite, avec leurs mètres', () => {
		const passages = rattacher(ligne([6.607, 46.5], [6.615, 46.5]), [AVENCHES, BEX, COPPET]);
		expect(resume(passages)).toEqual([
			['Bex', Math.round(5 * M)],
			['Avenches', Math.round(3 * M)]
		]);
	});

	it('écarte la voisine d’un tracé qui longe la limite et n’y entre que de quelques mètres', () => {
		// Une pointe de 0,0001° de longitude chez Bex, aller et retour : environ 16 m.
		const passages = rattacher(
			ligne([6.601, 46.5], [6.6099, 46.5], [6.6101, 46.50005], [6.6099, 46.5001], [6.601, 46.5001]),
			[AVENCHES, BEX]
		);
		expect(passages.map((p) => p.commune.nom)).toEqual(['Avenches']);
	});

	it('compte une commune dès 20 m parcourus, pas en deçà', () => {
		const fin = (m: number): Point => [6.61 + m / (M * 1000), 46.5];
		expect(rattacher(ligne([6.605, 46.5], fin(21)), [AVENCHES, BEX]).map((p) => p.commune.nom)).toEqual(['Avenches', 'Bex']);
		expect(rattacher(ligne([6.605, 46.5], fin(19)), [AVENCHES, BEX]).map((p) => p.commune.nom)).toEqual(['Avenches']);
	});

	it('rattache à celle qui en contient la plus grande part un tracé qui n’atteint 20 m nulle part', () => {
		// 15 m chez Bex, 8 m chez Avenches.
		const passages = rattacher(ligne([6.6099, 46.5], [6.6102, 46.5]), [AVENCHES, BEX]);
		expect(resume(passages)).toEqual([['Bex', 15]]);
	});

	it('ignore la part hors du canton', () => {
		const passages = rattacher(ligne([6.58, 46.5], [6.604, 46.5]), [AVENCHES, BEX]);
		expect(resume(passages)).toEqual([['Avenches', Math.round(4 * M)]]);
	});

	it('n’a aucune commune pour un tracé tout entier hors du canton', () => {
		expect(rattacher(ligne([6.5, 46.5], [6.55, 46.5]), [AVENCHES, BEX])).toEqual([]);
	});

	it('additionne les morceaux d’une MultiLineString, chacun dans sa commune', () => {
		const morceaux: Geometrie = {
			type: 'MultiLineString',
			coordinates: [
				[[6.601, 46.5], [6.603, 46.5]],
				[[6.612, 46.5], [6.618, 46.5]],
				[[6.605, 46.505], [6.607, 46.505]]
			]
		};
		expect(resume(rattacher(morceaux, [AVENCHES, BEX]))).toEqual([
			['Bex', Math.round(6 * M)],
			['Avenches', Math.round(4 * M)]
		]);
	});

	it('ne compte pas dans une commune trouée la part qui traverse son trou, qui revient à l’enclave', () => {
		const trou: Point[] = [[6.604, 46.495], [6.606, 46.495], [6.606, 46.505], [6.604, 46.505], [6.604, 46.495]];
		const [exterieur] = carre(AVENCHES.commune.bbox)[0];
		const trouee = { ...AVENCHES, limites: [[exterieur, trou]] };
		const enclave = limitee(4, 'Dully', [6.604, 46.495, 6.606, 46.505]);
		expect(resume(rattacher(ligne([6.601, 46.5], [6.609, 46.5]), [trouee, enclave]))).toEqual([
			['Avenches', Math.round(6 * M)],
			['Dully', Math.round(2 * M)]
		]);
	});

	it('additionne les morceaux d’une commune en plusieurs morceaux, sans le vide entre eux', () => {
		const deux = limitee(5, 'Échallens', [6.6, 46.49, 6.63, 46.51], [
			...carre([6.6, 46.49, 6.605, 46.51]),
			...carre([6.62, 46.49, 6.63, 46.51])
		]);
		expect(resume(rattacher(ligne([6.601, 46.5], [6.625, 46.5]), [deux]))).toEqual([['Échallens', Math.round(9 * M)]]);
	});

	it.each([
		{ sens: 'un parallèle', trace: ligne([6.601, 46.5], [6.609, 46.5]), attendu: 612.3 },
		{ sens: 'un méridien', trace: ligne([6.605, 46.491], [6.605, 46.509]), attendu: 2001.5 },
		{ sens: 'une diagonale', trace: ligne([6.601, 46.491], [6.609, 46.509]), attendu: 2093.1 }
	])('mesure à 1 % près la longueur parcourue le long d’$sens', ({ trace, attendu }) => {
		const [{ metres }] = rattacher(trace, [AVENCHES]);
		expect(Math.abs(metres - attendu) / attendu).toBeLessThan(0.01);
	});
});
