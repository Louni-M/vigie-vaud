import { describe, expect, it } from 'vitest';
import { insecables } from './typographie.js';

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
