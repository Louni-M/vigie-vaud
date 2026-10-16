import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { Source } from '../src/lib/schema.ts';
import { erreursSources } from './verifier-sources.ts';

const lire = (chemin: string) => JSON.parse(readFileSync(new URL(chemin, import.meta.url), 'utf8'));
const SCHEMA = lire('../../schema/sources.schema.json');
const COMMUNES = new Set((lire('../static/communes.json') as { bfs: number }[]).map((c) => c.bfs));

const conseil = (id: string, body_key: string, couverture?: Source['couverture']): Source => ({
	id,
	nom: `Conseil ${id}`,
	nom_court: id,
	attribution: { texte: 'Source: OpenParlData.ch', lien: 'https://openparldata.ch', licence: 'CC BY 4.0' },
	voie_acces: 'cron',
	fraicheur: 'import',
	...(couverture ? { couverture } : {}),
	conseil: { body_key, donne: ['objets', 'seances'] }
});

const erreurs = (...sources: Source[]) => erreursSources({ sources }, SCHEMA, COMMUNES);

describe('contrôle de sources.json à la construction', () => {
	it('accepte le sources.json du dépôt', () => {
		expect(erreursSources(lire('../../sources.json'), SCHEMA, COMMUNES)).toEqual([]);
	});

	it('accepte un conseil communal qui couvre exactement sa commune, et le Grand Conseil sans Couverture', () => {
		expect(erreurs(conseil('gc', 'VD'), conseil('lausanne', '5586', { communes: [5586], mode: 'api' }))).toEqual([]);
	});

	it('refuse un conseil communal qui ne couvre pas exactement sa commune', () => {
		expect(erreurs(conseil('a', '5586', { communes: [5586, 5590], mode: 'api' }))).toEqual([
			'a : un conseil communal couvre exactement sa commune (5586)'
		]);
		expect(erreurs(conseil('b', '5586', { communes: 'canton', mode: 'api' }))).toEqual([
			'b : un conseil communal couvre exactement sa commune (5586)'
		]);
		expect(erreurs(conseil('c', '5586'))).toEqual(['c : un conseil communal couvre exactement sa commune (5586)']);
	});

	it('refuse un Grand Conseil qui déclare une Couverture', () => {
		expect(erreurs(conseil('gc', 'VD', { communes: 'canton', mode: 'api' }))).toEqual([
			'gc : le Grand Conseil porte sur le canton et ne déclare pas de Couverture'
		]);
	});

	it('refuse un n° OFS qui n’est pas une commune actuelle', () => {
		expect(erreurs(conseil('x', '9999', { communes: [9999], mode: 'api' }))).toEqual([
			"x : le n° OFS 9999 n'est pas une commune actuelle"
		]);
	});
});
