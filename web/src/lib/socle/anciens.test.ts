import { describe, expect, it } from 'vitest';
import { ancienneAdresse } from './anciens.js';
import { commune } from '#lib/couches/permis/faux-canton.js';
import type { Commune } from '#lib/types.js';

const BEL: Commune = {
	...commune(5613, 'Bourg-en-Lavaux', [6.68, 46.44, 6.76, 46.52]),
	slug: 'bourg-en-lavaux',
	anciens: [
		{ nom: 'Cully', slug: 'cully', type: 'Ancienne commune', annee: 2011 },
		{ nom: 'Villette (Lavaux)', slug: 'villette-lavaux', type: 'Ancienne commune', annee: 2011 }
	]
};
const COMMUNES = [commune(5590, 'Pully', [6.62, 46.49, 6.69, 46.53]), BEL];

describe('404 d’une ancienne commune', () => {
	it('reconnaît le chemin d’une ancienne commune et dit de quelle commune elle fait partie', () => {
		expect(ancienneAdresse(COMMUNES, '/commune/cully')).toEqual({
			phrase: 'Cully fait partie de Bourg-en-Lavaux depuis 2011',
			commune: BEL
		});
	});

	it('dit d’un ancien nom comment la commune s’appelle aujourd’hui', () => {
		const yverdon: Commune = {
			...commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]),
			anciens: [{ nom: 'Yverdon', slug: 'yverdon', type: 'Ancien nom', annee: 1982 }]
		};
		expect(ancienneAdresse([yverdon], '/commune/yverdon/')?.phrase).toBe('Yverdon s’appelle Yverdon-les-Bains depuis 1982');
	});

	it('ne reconnaît rien d’autre', () => {
		expect(ancienneAdresse(COMMUNES, '/commune/inconnue')).toBeNull();
		expect(ancienneAdresse(COMMUNES, '/cully')).toBeNull();
		expect(ancienneAdresse(COMMUNES, '/commune/cully/plan')).toBeNull();
		expect(ancienneAdresse(COMMUNES, '/commune/')).toBeNull();
	});
});
