import { describe, expect, it } from 'vitest';
import { chargerImports, dernierImport } from './imports-conseils.js';
import type { ImportConseils } from './schema.js';
import { source } from './sources.js';

const IMPORTS: ImportConseils = {
	version: 1,
	genere: '2026-10-16T05:12:00Z',
	conseils: { vd: '2026-10-16T05:10:00Z', '5586': '2026-10-15T05:11:00Z' }
};

const reponse = (corps: unknown, status = 200) =>
	new Response(typeof corps === 'string' ? corps : JSON.stringify(corps), { status });

describe('dernier import des conseils (conseils/import.json)', () => {
	it('lit conseils/import.json à la base du dépôt de données', async () => {
		const demandes: string[] = [];
		const f = async (url: RequestInfo | URL) => (demandes.push(String(url)), reponse(IMPORTS));
		expect(await chargerImports(f, 'https://donnees.exemple')).toEqual(IMPORTS);
		expect(demandes).toEqual(['https://donnees.exemple/conseils/import.json']);
	});

	it('donne l’heure du dernier import réussi de chaque conseil, par sa clé en minuscules', () => {
		expect(dernierImport(IMPORTS, source('openparldata-vd'))).toEqual(new Date('2026-10-16T05:10:00Z'));
		expect(dernierImport(IMPORTS, source('openparldata-5586'))).toEqual(new Date('2026-10-15T05:11:00Z'));
	});

	it('ne donne rien pour un conseil jamais importé, ni pour une source qui n’est pas un conseil', () => {
		expect(dernierImport(IMPORTS, source('openparldata-5938'))).toBeNull();
		expect(dernierImport(IMPORTS, source('camac-permis'))).toBeNull();
		expect(dernierImport(null, source('openparldata-vd'))).toBeNull();
	});

	it('donne null si le fichier manque, est illisible, injoignable ou d’une version inconnue', async () => {
		expect(await chargerImports(async () => reponse('Not found', 404), 'https://d')).toBeNull();
		expect(await chargerImports(async () => reponse('{', 200), 'https://d')).toBeNull();
		expect(await chargerImports(() => Promise.reject(new TypeError('réseau')), 'https://d')).toBeNull();
		expect(await chargerImports(async () => reponse({ ...IMPORTS, version: 2 }), 'https://d')).toBeNull();
	});
});
