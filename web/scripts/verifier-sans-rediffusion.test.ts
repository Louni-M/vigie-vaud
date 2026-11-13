import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';

/**
 * La garde contre la rediffusion (norme DCG 8401), lancée sur des sites construits fabriqués dans un dossier
 * temporaire : jamais sur `build`, ni avec des données réelles.
 */

const SCRIPT = fileURLToPath(new URL('../../.github/scripts/verifier-sans-rediffusion.sh', import.meta.url));

const sites: string[] = [];
afterEach(() => {
	for (const s of sites.splice(0)) rmSync(s, { recursive: true, force: true });
});

/** Un site construit minimal, plus les fichiers donnés (chemin relatif → contenu). */
function site(fichiers: Record<string, string> = {}): string {
	const racine = mkdtempSync(join(tmpdir(), 'site-construit-'));
	sites.push(racine);
	const tous: Record<string, string> = {
		'index.html': '<!doctype html><html lang="fr"><body>Vigie Vaud</body></html>',
		...fichiers
	};
	for (const [chemin, contenu] of Object.entries(tous)) {
		const complet = join(racine, chemin);
		mkdirSync(dirname(complet), { recursive: true });
		writeFileSync(complet, contenu);
	}
	return racine;
}

function verifier(racine: string) {
	const r = spawnSync('bash', [SCRIPT, racine], { encoding: 'utf8' });
	return { code: r.status, erreur: r.stderr };
}

describe('garde contre la rediffusion des données CAMAC et DGMR', () => {
	it('accepte un site sans donnée des sources', () => {
		expect(verifier(site()).code).toBe(0);
	});

	it('refuse un site qui contient un dossier data', () => {
		const r = verifier(site({ 'data/vide.txt': '' }));
		expect(r.code).toBe(1);
		expect(r.erreur).toContain('data');
	});

	it('refuse une entité CAMAC telle que la renvoie le canton, cachée ailleurs que dans data', () => {
		const camac = JSON.stringify({
			features: [{ attributes: { NO_CAMAC: 123456, DATE_ENQUETE: 'Du 19.09.2026 au 19.10.2026' } }]
		});
		const r = verifier(site({ '_app/immutable/assets/permis.json': camac }));
		expect(r.code).toBe(1);
		expect(r.erreur).toContain('_app/immutable/assets/permis.json');
		expect(r.erreur).toContain('CAMAC');
	});

	it('refuse une restriction DGMR en GeoJSON, quel que soit le fichier', () => {
		const dgmr = JSON.stringify({
			type: 'FeatureCollection',
			features: [{ type: 'Feature', properties: { OBJECTID: 1, NOM: 'Pully, Chemin des Exemples', RHRC: '701-B-P' } }]
		});
		const r = verifier(site({ 'commune/pully.html': `<html><body><pre>${dgmr}</pre></body></html>` }));
		expect(r.code).toBe(1);
		expect(r.erreur).toContain('commune/pully.html');
		expect(r.erreur).toContain('DGMR');
	});

	it('refuse des données inlinées dans un fichier JS, en objet littéral ou en JSON échappé', () => {
		expect(verifier(site({ '_app/immutable/chunks/a.js': 'const d=[{NO_CAMAC:123,NO_FAO:null}];' })).code).toBe(1);
		expect(verifier(site({ '_app/immutable/chunks/b.js': 'const d=JSON.parse("[{\\"WEEK_END\\":\\"Oui\\"}]");' })).code).toBe(1);
		expect(verifier(site({ 'index.html': '<div data-r="{&quot;HEURE_DEBUT&quot;: &quot;20:00&quot;}"></div>' })).code).toBe(1);
	});

	it('accepte le code du site qui interroge les deux sources en direct', () => {
		// Formes recopiées d'un site construit : listes de champs, URL des sondes, lectures d'attributs.
		const code = [
			'var D=300,O=`NO_CAMAC,NO_FAO,DATE_ENQUETE,NATURE,DESCRIPTION,DECISION_COMMUNALE,DATE_DECISION,URL,ETAT`;',
			'const s={delai:20,champs:[`NO_CAMAC`,`NO_FAO`,`DATE_ENQUETE`,`DECISION_COMMUNALE`,`DATE_DECISION`],jamais_vide:!0};',
			'const u=`/596/query?where=1%3D1&outFields=OBJECTID,NOM,RESTRICTION,RHRC,DATE_DEBUT,DATE_FIN,HEURE_DEBUT,HEURE_FIN,WEEK_END,TYPE,REMARQUE&f=json`;',
			'function p({attributes:e}){return{id:Number(e.NO_CAMAC),fao:S(e.NO_FAO),date_decision:x(e.DATE_DECISION)[0]}}',
			'function r(e){return{rhrc:M(e.RHRC),heureDebut:M(e.HEURE_DEBUT),weekEnd:M(e.WEEK_END),n:e.HEURE_FIN?e.HEURE_FIN:null}}',
			'const w=async e=>N(await h({where:`NO_CAMAC IN (${e.join(`,`)})`}));',
			'const v=`SUBSTRING(DATE_ENQUETE FROM 10 FOR 4)`;'
		].join('\n');
		expect(verifier(site({ '_app/immutable/nodes/0.js': code })).code).toBe(0);
	});
});
