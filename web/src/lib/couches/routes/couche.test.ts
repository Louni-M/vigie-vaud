import { describe, expect, it } from 'vitest';
import { COUCHES } from '#lib/registre/couches.js';
import { teteCommune } from '#lib/registre/tete.js';
import { commune } from '#tests/faux-canton.js';

describe('couche Routes au registre', () => {
	it('est inscrite après Conseils et avant Hôtels de ville, dessinée au-dessus de tout', () => {
		expect(COUCHES.map((c) => c.id)).toEqual(['permis', 'conseils', 'routes', 'hotels-de-ville']);
	});

	it('nomme les restrictions de circulation dans la description de chaque commune, sans nombre', () => {
		const lutry = commune(5606, 'Lutry', [6.7, 46.49, 6.75, 46.52]);
		expect(teteCommune(lutry, COUCHES).description).toContain('les restrictions de circulation en cours et à venir');
	});
});
