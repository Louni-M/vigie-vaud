import { describe, expect, it } from 'vitest';
import { insecables, typographier } from './typographie.js';

describe('insecables', () => {
	it('colle à leur mot ; : ? ! et les guillemets français', () => {
		expect(insecables('cantonales ; les routes : « oui » ? non !')).toBe(
			'cantonales ; les routes : « oui » ? non !'
		);
	});

	it('ne touche pas aux deux-points sans espace, comme dans une heure ou une adresse', () => {
		expect(insecables('https://openparldata.ch, 16:14')).toBe('https://openparldata.ch, 16:14');
	});
});

describe('typographier', () => {
	const nb = '\u00a0';
	it('ajoute aux insécables de ponctuation celles de « n° », des heures et des unités', () => {
		expect(typographier('Séance du 26 octobre à 18 h 30 : bâtiment ECA n° 769, forage 180 m ?')).toBe(
			`Séance du 26 octobre à 18${nb}h${nb}30${nb}: bâtiment ECA n°${nb}769, forage 180${nb}m${nb}?`
		);
		expect(typographier('de 7 h à 19 h, encore 14 jours, 2 mètres')).toBe(
			`de 7${nb}h à 19${nb}h, encore 14${nb}jours, 2${nb}mètres`
		);
	});

	it('remplace trois points par des points de suspension', () => {
		expect(typographier('un sport à l’APEMS... et après ?')).toBe(`un sport à l’APEMS… et après${nb}?`);
	});

	it('laisse les mots qui commencent comme une unité, et les nombres suivis d’un autre mot', () => {
		expect(typographier('5 maisons, 3 hangars, 12 tonnes, 2 années')).toBe('5 maisons, 3 hangars, 12 tonnes, 2 années');
	});

	it('ne change rien à un texte déjà soigné', () => {
		const soigne = `Objet n°${nb}12${nb}: 18${nb}h${nb}30`;
		expect(typographier(soigne)).toBe(soigne);
	});
});
