import { describe, expect, it } from 'vitest';
import { deduireCouverture, libelleEtat, libellePaire } from './couverture.js';
import { chargerEtatSources, lienPannes, lireEtatSources } from './etat-sources.js';
import type { CoucheInscrite } from './registre/types.js';
import type { EtatSource, EtatSources, Source } from './schema.js';

const MAINTENANT = new Date('2026-10-12T14:30:00Z');
const COMMUNES = [{ bfs: 5586 }, { bfs: 5590 }, { bfs: 5889 }];

const source = (id: string, couverture: Source['couverture'], sonde = true): Source => ({
	id,
	nom: `Source ${id}`,
	nom_court: id,
	attribution: { texte: id, lien: `https://exemple.ch/${id}`, licence: 'libre' },
	voie_acces: 'direct',
	fraicheur: 'requete',
	couverture,
	sonde: sonde ? { url: `https://exemple.ch/${id}/sonde`, delai: 20 } : null
});

const charger = () => Promise.reject(new Error('non chargé'));
const couche = (id: string, sources: string[], onglet = true): CoucheInscrite => ({
	id,
	nom: id,
	sources,
	permanente: !onglet,
	activeParDefaut: true,
	icone: { signe: id, couleur: '#000' },
	composants: onglet ? { Carte: charger, Onglet: charger } : { Carte: charger }
});

const disponible: EtatSource = {
	etat: 'disponible',
	depuis: '2026-10-10T08:17:00Z',
	derniere_sonde: '2026-10-12T14:17:00Z',
	dernier_succes: '2026-10-12T14:17:00Z',
	echecs_consecutifs: 0,
	motif: null
};

const etat = (sources: Record<string, EtatSource>, genere = '2026-10-12T14:17:00Z'): EtatSources => ({
	version: 1,
	genere,
	sources
});

describe('Couverture déduite', () => {
	it('donne le mode de chaque paire (source, commune) : API, scrapé ou non couvert', () => {
		const c = deduireCouverture({
			sources: [
				source('canton', { communes: 'canton', mode: 'api' }),
				source('liste', { communes: [5586, 5889], mode: 'scrape' })
			],
			etat: etat({ canton: disponible, liste: disponible }),
			couches: [couche('a', ['canton', 'liste'])],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(c.mode('canton', 5590)).toBe('api');
		expect(c.mode('liste', 5586)).toBe('scrape');
		expect(c.mode('liste', 5590)).toBe('non_couvert');
	});

	const camac = source('camac', { communes: [5586, 5889], mode: 'api' });
	const deduire = (e: EtatSources | null, maintenant = MAINTENANT, sources = [camac]) =>
		deduireCouverture({ sources, etat: e, couches: [couche('a', sources.map((s) => s.id))], communes: COMMUNES, maintenant });

	it("donne l'état de la source à chaque commune qu'elle couvre, et aucun à celles qu'elle ne couvre pas", () => {
		const c = deduire(etat({ camac: disponible }));
		expect(c.paire('camac', 5586)).toEqual({ mode: 'api', etat: { etat: 'disponible' } });
		expect(c.paire('camac', 5889)).toEqual({ mode: 'api', etat: { etat: 'disponible' } });
		expect(c.paire('camac', 5590)).toEqual({ mode: 'non_couvert', etat: null });
	});

	it('date une panne de la première sonde en échec', () => {
		const panne: EtatSource = {
			etat: 'en_panne',
			depuis: '2026-10-12T12:17:00Z',
			derniere_sonde: '2026-10-12T14:17:00Z',
			dernier_succes: '2026-10-12T11:47:00Z',
			echecs_consecutifs: 5,
			motif: 'HTTP 503'
		};
		expect(deduire(etat({ camac: panne })).etat('camac')).toEqual({ etat: 'en_panne', depuis: '2026-10-12T12:17:00Z' });
	});

	it("dit la surveillance interrompue quand le dernier passage du cron date de plus de 2 h", () => {
		const e = etat({ camac: disponible }, '2026-10-12T12:30:00Z');
		expect(deduire(e, new Date('2026-10-12T14:30:00Z')).etat('camac')).toEqual({ etat: 'disponible' });
		expect(deduire(e, new Date('2026-10-12T14:30:01Z')).etat('camac')).toEqual({ etat: 'surveillance_interrompue' });
	});

	it("dit non surveillée une source sans bloc sonde, même sans état lisible", () => {
		const fond = source('fond', { communes: 'canton', mode: 'api' }, false);
		expect(deduire(etat({}), MAINTENANT, [fond]).etat('fond')).toEqual({ etat: 'non_surveillee' });
		expect(deduire(null, MAINTENANT, [fond]).etat('fond')).toEqual({ etat: 'non_surveillee' });
	});

	it("dit inconnu l'état d'une source sondée quand l'état des sources est illisible ou ne la cite pas", () => {
		expect(deduire(null).paire('camac', 5586)).toEqual({ mode: 'api', etat: { etat: 'inconnu' } });
		expect(deduire(etat({})).etat('camac')).toEqual({ etat: 'inconnu' });
	});

	it("dit qu'une couche couvre une commune dès qu'une de ses sources la couvre", () => {
		const c = deduireCouverture({
			sources: [
				source('ouest', { communes: [5586], mode: 'api' }),
				source('est', { communes: [5889], mode: 'scrape' })
			],
			etat: null,
			couches: [couche('conseils', ['ouest', 'est'])],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(c.couvre('conseils', 5586)).toBe(true);
		expect(c.couvre('conseils', 5889)).toBe(true);
		expect(c.couvre('conseils', 5590)).toBe(false);
	});

	it("ne donne une Couverture qu'aux sources des couches qui ont un onglet, dans l'ordre du registre", () => {
		const c = deduireCouverture({
			sources: [
				source('ucv', { communes: 'canton', mode: 'api' }, false),
				source('camac', { communes: 'canton', mode: 'api' }),
				source('presse', { communes: [5586, 5590], mode: 'scrape' }),
				source('fond', { communes: 'canton', mode: 'api' }, false)
			],
			etat: etat({ camac: disponible }),
			couches: [
				couche('permis', ['camac']),
				couche('presse', ['presse', 'camac']),
				couche('hotels-de-ville', ['ucv'], false)
			],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(c.sources.map((s) => [s.source.id, s.communes])).toEqual([
			['camac', 3],
			['presse', 2]
		]);
		expect(c.sources[0].etat).toEqual({ etat: 'disponible' });
		expect(c.sources[0].sonde).toEqual(disponible);
		expect(c.sources[1].sonde).toBeNull();
		// Sans Couverture, une couche ne laisse aucune commune « non couverte ».
		expect(c.couvre('hotels-de-ville', 5889)).toBe(true);
	});

	it("refuse un état des sources d'une version inconnue, et dit alors l'état inconnu", () => {
		const v2 = { ...etat({ camac: disponible }), version: 2 };
		expect(deduire(lireEtatSources(v2)).etat('camac')).toEqual({ etat: 'inconnu' });
		expect(deduire(lireEtatSources('<html>')).etat('camac')).toEqual({ etat: 'inconnu' });
		expect(deduire(lireEtatSources(etat({ camac: disponible }))).etat('camac')).toEqual({ etat: 'disponible' });
	});
});

describe("libellé d'une paire (source, commune)", () => {
	it('suit les formats « API · disponible », « Scrapé · en panne depuis le … » et « Non couvert »', () => {
		expect(libellePaire({ mode: 'api', etat: { etat: 'disponible' } })).toBe('API · disponible');
		// 12 h UTC = 14 h à Lausanne en octobre (heure d'été).
		expect(libellePaire({ mode: 'scrape', etat: { etat: 'en_panne', depuis: '2026-10-12T12:00:00Z' } })).toBe(
			'Scrapé · en panne depuis le 12 oct., 14 h'
		);
		expect(libellePaire({ mode: 'non_couvert', etat: null })).toBe('Non couvert');
	});

	it('nomme chacun des autres états, et donne les minutes de la panne quand il y en a', () => {
		expect(libelleEtat({ etat: 'en_panne', depuis: '2026-12-01T07:47:00Z' })).toBe('en panne depuis le 1 déc., 8 h 47');
		expect(libelleEtat({ etat: 'en_panne', depuis: null })).toBe('en panne');
		expect(libelleEtat({ etat: 'surveillance_interrompue' })).toBe('surveillance interrompue');
		expect(libelleEtat({ etat: 'non_surveillee' })).toBe('non surveillée');
		expect(libelleEtat({ etat: 'inconnu' })).toBe('inconnu');
	});
});

describe("chargement de l'état des sources", () => {
	const reponse = (corps: unknown, status = 200) =>
		new Response(typeof corps === 'string' ? corps : JSON.stringify(corps), { status });

	it('lit etat-sources.json à la base du dépôt de données', async () => {
		const demandes: string[] = [];
		const f = async (url: RequestInfo | URL) => (demandes.push(String(url)), reponse(etat({ camac: disponible })));
		expect(await chargerEtatSources(f, 'https://donnees.exemple')).toEqual(etat({ camac: disponible }));
		expect(demandes).toEqual(['https://donnees.exemple/etat-sources.json']);
	});

	it("mène aux issues panne-source ouvertes de la source, dans le dépôt de données", () => {
		const url = new URL(lienPannes(source('camac', { communes: 'canton', mode: 'api' })));
		expect(url.origin + url.pathname).toBe('https://github.com/Louni-M/vigie-vaud-donnees/issues');
		expect(url.searchParams.get('q')).toBe('is:issue is:open label:panne-source in:title "Panne : Source camac"');
	});

	it('donne null si le fichier est absent, illisible ou injoignable', async () => {
		expect(await chargerEtatSources(async () => reponse('Not found', 404), 'https://d')).toBeNull();
		expect(await chargerEtatSources(async () => reponse('{', 200), 'https://d')).toBeNull();
		expect(await chargerEtatSources(() => Promise.reject(new TypeError('réseau')), 'https://d')).toBeNull();
	});
});
