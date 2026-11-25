import { describe, expect, it } from 'vitest';
import { cadreAutourDe } from './cadrage.js';

const versY = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));

describe('cadre autour de l’hôtel de ville', () => {
	// Une commune dont l'hôtel de ville est au sud-ouest de son emprise terrestre.
	const cadre: [number, number, number, number] = [6.6, 46.5, 6.7, 46.6];
	const hotel: [number, number] = [6.62, 46.52];
	const [ouest, sud, est, nord] = cadreAutourDe(cadre, hotel);

	it('contient toute la commune', () => {
		// À l'arrondi près des aller-retour en Mercator.
		const e = 1e-9;
		expect(ouest).toBeLessThanOrEqual(cadre[0] + e);
		expect(sud).toBeLessThanOrEqual(cadre[1] + e);
		expect(est).toBeGreaterThanOrEqual(cadre[2] - e);
		expect(nord).toBeGreaterThanOrEqual(cadre[3] - e);
	});

	it('a l’hôtel de ville en son milieu, sur la carte', () => {
		expect((ouest + est) / 2).toBeCloseTo(hotel[0], 10);
		expect((versY(sud) + versY(nord)) / 2).toBeCloseTo(versY(hotel[1]), 10);
	});

	it('ne s’étend que du côté le plus éloigné', () => {
		expect(est).toBeCloseTo(6.7, 10);
		expect(nord).toBeCloseTo(46.6, 10);
	});

	it('reste le cadre quand l’hôtel de ville en est le milieu', () => {
		const r = cadreAutourDe([6, 46, 7, 47], [6.5, 46.50182]);
		expect(r[0]).toBeCloseTo(6, 10);
		expect(r[2]).toBeCloseTo(7, 10);
	});
});
