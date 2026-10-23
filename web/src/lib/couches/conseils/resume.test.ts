import { describe, expect, it } from 'vitest';
import { resumeConseils } from './resume.js';
import { SOURCES } from '#lib/sources.js';
import { commune } from '#tests/faux-canton.js';
import { avecSources, sourceSite } from '#tests/faux-conseils.js';

// Les sources réelles de `sources.json` : la description pré-générée d'une commune en dépend.
const resume = resumeConseils(SOURCES);

describe('résumé de la couche Conseils pour la description d’une commune', () => {
	it('dit les objets et les séances du conseil communal quand il donne les deux (Lausanne)', () => {
		expect(resume(commune(5586, 'Lausanne', [6.58, 46.5, 6.72, 46.6]))).toBe(
			'les objets et les séances de son Conseil communal, et les objets du Grand Conseil qui la nomment'
		);
	});

	it('ne dit que les séances quand le conseil communal ne donne qu’elles (Yverdon-les-Bains)', () => {
		expect(resume(commune(5938, 'Yverdon-les-Bains', [6.6, 46.76, 6.68, 46.8]))).toBe(
			'les séances de son Conseil communal, et les objets du Grand Conseil qui la nomment'
		);
	});

	it.each([
		[['objets', 'seances'], 'les objets et les séances'],
		[['preavis', 'seances'], 'les préavis et les séances'],
		[['seances'], 'les séances']
	] as const)('suit le niveau d’une commune scrapée (%j)', (donne, dit) => {
		const sources = avecSources(SOURCES, sourceSite({ conseil: { body_key: '5643', donne: [...donne] } }));
		expect(resumeConseils(sources)(commune(5643, 'Préverenges', [6.51, 46.5, 6.54, 46.52]))).toBe(
			`${dit} de son Conseil communal, et les objets du Grand Conseil qui la nomment`
		);
	});

	it('ne dit que le Grand Conseil quand le conseil communal n’est pas couvert (Bussigny)', () => {
		expect(resume(commune(5624, 'Bussigny', [6.53, 46.54, 6.57, 46.57]))).toBe(
			'les objets du Grand Conseil qui la nomment'
		);
	});
});
