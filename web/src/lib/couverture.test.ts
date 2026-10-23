import { describe, expect, it } from 'vitest';
import {
	deduireCouverture,
	libelleCellule,
	libelleCommunes,
	libelleEtat,
	libelleLimites,
	libellePaire
} from './couverture.js';
import { chargerEtatSources, lienPannes, lireEtatSources } from './etat-sources.js';
import type { CoucheInscrite } from './registre/types.js';
import { COUCHES } from './registre/couches.js';
import type { EtatSource, EtatSources, RaisonNonCouvert, Source } from './schema.js';
import { SOURCES } from './sources.js';
import communesJ0 from '../../static/communes.json';
import { sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';

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

	it("ne donne une Couverture qu'aux sources des couches qui en ont une, dans l'ordre du registre", () => {
		const c = deduireCouverture({
			sources: [
				source('ucv', null, false),
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

	it("ne donne aucune commune à une source sans Couverture : la couche est couverte par l'union des autres", () => {
		const c = deduireCouverture({
			sources: [
				source('canton', null),
				source('ouest', { communes: [5586], mode: 'api' }),
				source('est', { communes: [5889], mode: 'api' })
			],
			etat: etat({ canton: disponible, ouest: disponible, est: disponible }),
			couches: [couche('conseils', ['canton', 'ouest', 'est'])],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(COMMUNES.map((x) => c.mode('canton', x.bfs))).toEqual(['non_couvert', 'non_couvert', 'non_couvert']);
		expect(c.paire('canton', 5586)).toEqual({ mode: 'non_couvert', etat: null });
		expect(COMMUNES.map((x) => c.couvre('conseils', x.bfs))).toEqual([true, false, true]);
		expect(c.grisees('conseils')).toEqual([5590]);
	});

	it('couvre toutes les communes par une couche dont aucune source n’a de Couverture, et ne grise rien', () => {
		const c = deduireCouverture({
			sources: [source('canton', null), source('presse', undefined)],
			etat: etat({}),
			couches: [couche('presse', ['canton', 'presse'])],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(COMMUNES.map((x) => c.couvre('presse', x.bfs))).toEqual([true, true, true]);
		expect(c.grisees('presse')).toEqual([]);
	});

	it("refuse un état des sources d'une version inconnue, et dit alors l'état inconnu", () => {
		const v2 = { ...etat({ camac: disponible }), version: 2 };
		expect(deduire(lireEtatSources(v2)).etat('camac')).toEqual({ etat: 'inconnu' });
		expect(deduire(lireEtatSources('<html>')).etat('camac')).toEqual({ etat: 'inconnu' });
		expect(deduire(lireEtatSources(etat({ camac: disponible }))).etat('camac')).toEqual({ etat: 'disponible' });
	});
});

describe('grisage de la carte', () => {
	const panne: EtatSource = { ...disponible, etat: 'en_panne', depuis: '2026-10-12T12:17:00Z', motif: 'HTTP 503' };
	const deduire = (e: EtatSources | null) =>
		deduireCouverture({
			sources: [
				source('camac', { communes: 'canton', mode: 'api' }),
				source('ouest', { communes: [5586], mode: 'api' }),
				source('est', { communes: [5889], mode: 'scrape' }),
				source('ucv', null, false)
			],
			etat: e,
			couches: [
				couche('permis', ['camac']),
				couche('conseils', ['ouest', 'est']),
				couche('fond', ['ucv'], false),
				couche('ecoles', ['ouest'], false)
			],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});

	it('grise les communes que la couche du volet ouvert ne couvre pas', () => {
		expect(deduire(etat({})).grisees('conseils')).toEqual([5590]);
	});

	it('ne grise rien sans volet ouvert', () => {
		expect(deduire(etat({})).grisees(null)).toEqual([]);
	});

	it('ne grise rien pour une couche cantonale, ni pour une couche dont aucune source n’a de Couverture', () => {
		expect(deduire(etat({})).grisees('permis')).toEqual([]);
		expect(deduire(etat({})).grisees('fond')).toEqual([]);
	});

	it("grise selon les Couvertures de ses sources une couche sans onglet : la règle ne dépend pas de l'onglet", () => {
		expect(deduire(etat({})).grisees('ecoles')).toEqual([5590, 5889]);
	});

	it('ne grise rien de plus pour une panne', () => {
		const c = deduire(etat({ camac: panne, ouest: panne, est: panne }));
		expect(c.grisees('permis')).toEqual([]);
		expect(c.grisees('conseils')).toEqual([5590]);
	});

	it('grise, avec les couches inscrites, toutes les communes sauf Lausanne et Yverdon au volet Conseils, et rien ailleurs', () => {
		const c = deduireCouverture({
			sources: SOURCES,
			etat: etat({ 'camac-permis': panne, 'openparldata-5586': panne }),
			couches: COUCHES,
			communes: communesJ0,
			maintenant: MAINTENANT
		});
		expect(communesJ0).toHaveLength(300);
		const grisees = c.grisees('conseils');
		expect(grisees).toHaveLength(298);
		expect(grisees).not.toContain(5586);
		expect(grisees).not.toContain(5938);
		expect(grisees).toContain(5624); // Bussigny
		expect(c.grisees('permis')).toEqual([]);
		expect(c.grisees('routes')).toEqual([]);
		expect(c.grisees('hotels-de-ville')).toEqual([]);
	});
});

describe('Couverture des conseils déclarés dans sources.json', () => {
	const conseils = SOURCES.filter((s) => s.conseil);
	const c = deduireCouverture({
		sources: SOURCES,
		etat: null,
		couches: [couche('conseils', conseils.map((s) => s.id))],
		communes: communesJ0,
		maintenant: MAINTENANT
	});
	const couvertes = (id: string) => communesJ0.filter((x) => c.mode(id, x.bfs) !== 'non_couvert').map((x) => x.bfs);

	it('donne à chaque conseil communal exactement sa commune, par API', () => {
		expect(couvertes('openparldata-5586')).toEqual([5586]);
		expect(couvertes('openparldata-5938')).toEqual([5938]);
		expect(c.mode('openparldata-5586', 5586)).toBe('api');
	});

	it("ne donne pas de Couverture au Grand Conseil, qui porte sur le canton", () => {
		expect(SOURCES.find((s) => s.id === 'openparldata-vd')?.couverture).toBeUndefined();
		expect(couvertes('openparldata-vd')).toEqual([]);
	});

	it('couvre Lausanne et Yverdon par une couche des trois conseils, et grise toutes les autres communes', () => {
		expect(conseils.map((s) => s.id)).toEqual(['openparldata-vd', 'openparldata-5586', 'openparldata-5938']);
		expect(c.couvre('conseils', 5586)).toBe(true);
		expect(c.couvre('conseils', 5938)).toBe(true);
		expect(c.couvre('conseils', 5590)).toBe(false);
		expect(c.grisees('conseils')).toHaveLength(298);
	});
});

describe('tableau de la page Couverture : une colonne par couche', () => {
	const tous = Object.fromEntries(SOURCES.map((s) => [s.id, disponible]));
	const c = deduireCouverture({
		sources: SOURCES,
		etat: etat(tous),
		couches: COUCHES,
		communes: communesJ0,
		maintenant: MAINTENANT
	});
	const cellule = (couche: string, bfs: number, charge = true) => libelleCellule(c.cellule(couche, bfs), charge);

	it('a une colonne par couche qui a une Couverture, dans l’ordre du registre : Permis, Conseils et Routes', () => {
		expect(c.colonnes.map((x) => x.nom)).toEqual(['Permis', 'Conseils', 'Routes']);
	});

	it('donne pour Conseils la paire du conseil communal à Lausanne et à Yverdon, « Non couvert » à Bussigny', () => {
		expect(cellule('conseils', 5586)).toEqual(['API · disponible']);
		expect(cellule('conseils', 5938)).toEqual(['API · séances seulement · disponible']);
		expect(cellule('conseils', 5624)).toEqual(['Non couvert']);
	});

	describe('commune scrapée : son site est sondé par le cron, sans bloc sonde', () => {
		const site = sourceSite();
		const avecSite = (sources: Record<string, EtatSource>) =>
			deduireCouverture({
				sources: [...SOURCES, site],
				etat: etat(sources),
				couches: COUCHES.map((x) => (x.id === 'conseils' ? { ...x, sources: [...x.sources, site.id] } : x)),
				communes: communesJ0,
				maintenant: MAINTENANT
			});

		it('donne « Scrapé · séances seulement · disponible » à une commune sondée avec succès', () => {
			const d = avecSite({ ...tous, 'site-5643': disponible });
			expect(libelleCellule(d.cellule('conseils', 5643))).toEqual(['Scrapé · séances seulement · disponible']);
		});

		it('dit depuis quand une commune dont la sonde échoue est en panne', () => {
			const panne: EtatSource = {
				etat: 'en_panne',
				depuis: '2026-10-12T05:17:00Z',
				derniere_sonde: '2026-10-12T05:47:00Z',
				dernier_succes: '2026-10-11T05:17:00Z',
				echecs_consecutifs: 2,
				motif: 'marqueur absent'
			};
			const d = avecSite({ ...tous, 'site-5643': panne });
			expect(libelleCellule(d.cellule('conseils', 5643))).toEqual([
				'Scrapé · séances seulement · en panne depuis le 12 oct., 7 h 17'
			]);
			expect(d.sources.find((s) => s.source.id === 'site-5643')?.sonde).toEqual(panne);
			// Une panne ne grise rien.
			expect(d.couvre('conseils', 5643)).toBe(true);
		});

		it("dit l'état inconnu d'une commune pas encore sondée", () => {
			expect(libelleCellule(avecSite(tous).cellule('conseils', 5643))).toEqual([
				'Scrapé · séances seulement · inconnu'
			]);
		});

		it("ne surveille pas une source communale sans conseil (commune non couverte d'une plateforme retenue)", () => {
			const d = deduireCouverture({
				sources: [sourceSite({ conseil: null })],
				etat: etat({}),
				couches: [couche('conseils', ['site-5643'])],
				communes: COMMUNES,
				maintenant: MAINTENANT
			});
			expect(d.etat('site-5643')).toEqual({ etat: 'non_surveillee' });
		});
	});

	describe('commune non couverte d’une plateforme retenue', () => {
		const d = (raison: RaisonNonCouvert = 'preavis_seuls') => {
			const nonCouverte = sourceNonCouverte(raison);
			return deduireCouverture({
				sources: [...SOURCES, nonCouverte],
				etat: etat(tous),
				couches: COUCHES.map((x) => (x.id === 'conseils' ? { ...x, sources: [...x.sources, nonCouverte.id] } : x)),
				communes: communesJ0,
				maintenant: MAINTENANT
			});
		};

		it.each([
			['preavis_seuls', 'Non couvert · préavis seuls'],
			['rien_en_ligne', 'Non couvert · rien en ligne'],
			['demande_commune', 'Non couvert · à la demande de la commune'],
			['refus_robots', 'Non couvert · le site refuse les robots'],
			['nouveau_site', 'Non couvert · nouveau site pas encore lu']
		] as const)('donne sa raison dans la cellule (%s), les autres restent « Non couvert »', (raison, libelle) => {
			expect(libelleCellule(d(raison).cellule('conseils', 5568))).toEqual([libelle]);
			expect(libelleCellule(d(raison).cellule('conseils', 5624))).toEqual(['Non couvert']);
		});

		it('ne couvre pas sa commune : elle est grisée au volet Conseils, et sans encart de source', () => {
			const c = d();
			expect(c.couvre('conseils', 5568)).toBe(false);
			expect(c.grisees('conseils')).toContain(5568);
			expect(c.grisees('conseils')).toHaveLength(298);
			expect(c.sources.map((s) => s.source.id)).not.toContain('site-5568');
		});
	});

	it('donne pour Permis la paire de la CAMAC partout', () => {
		expect(cellule('permis', 5586)).toEqual(['API · disponible']);
		expect(cellule('permis', 5624)).toEqual(['API · disponible']);
	});

	it('donne pour Routes la paire de la DGMR partout', () => {
		expect(cellule('routes', 5586)).toEqual(['API · disponible']);
		expect(cellule('routes', 5624)).toEqual(['API · disponible']);
	});

	it("liste chacune des sources qui couvrent la commune, et ne dit l'état qu'une fois chargé", () => {
		const d = deduireCouverture({
			sources: [source('ouest', { communes: [5586], mode: 'api' }), source('presse', { communes: 'canton', mode: 'scrape' })],
			etat: etat({ ouest: disponible }),
			couches: [couche('presse', ['ouest', 'presse'])],
			communes: COMMUNES,
			maintenant: MAINTENANT
		});
		expect(libelleCellule(d.cellule('presse', 5586))).toEqual(['API · disponible', 'Scrapé · inconnu']);
		expect(libelleCellule(d.cellule('presse', 5590))).toEqual(['Scrapé · inconnu']);
		expect(libelleCellule(d.cellule('presse', 5586), false)).toEqual(['API · …', 'Scrapé · …']);
	});
});

describe('encarts de la page Couverture : un par source', () => {
	const c = deduireCouverture({ sources: SOURCES, etat: null, couches: COUCHES, communes: communesJ0, maintenant: MAINTENANT });
	const encart = (id: string) => c.sources.find((s) => s.source.id === id)!;

	it('a un encart par source des couches Permis, Conseils et Routes, Grand Conseil compris', () => {
		expect(c.sources.map((s) => s.source.id)).toEqual([
			'camac-permis',
			'openparldata-vd',
			'openparldata-5586',
			'openparldata-5938',
			'dgmr-restrictions'
		]);
	});

	it('donne à l’encart de la DGMR tout le canton et sa ligne Limites', () => {
		expect(libelleCommunes(encart('dgmr-restrictions'), 300)).toBe('300 communes sur 300');
		expect(libelleLimites(encart('dgmr-restrictions').source)).toBe(
			'Publie surtout les routes cantonales ; les routes communales n’y figurent pas toujours.'
		);
	});

	it('dit « Porte sur le canton » pour une source sans Couverture, et le nombre de communes sinon', () => {
		expect(libelleCommunes(encart('openparldata-vd'), 300)).toBe('Porte sur le canton');
		expect(libelleCommunes(encart('openparldata-5586'), 300)).toBe('1 commune sur 300');
		expect(libelleCommunes(encart('camac-permis'), 300)).toBe('300 communes sur 300');
	});

	it('donne une ligne Limites à une source qui en déclare, et aucune sinon', () => {
		const limitee = { ...source('limitee', { communes: 'canton', mode: 'api' }), limites: 'surtout les rues principales' };
		expect(libelleLimites(limitee)).toBe('Publie surtout les rues principales.');
		expect(libelleLimites(source('entiere', { communes: 'canton', mode: 'api' }))).toBeNull();
	});

	it('reprend les limites de la DGMR déclarées dans sources.json, et aucune pour la CAMAC', () => {
		expect(libelleLimites(SOURCES.find((s) => s.id === 'dgmr-restrictions')!)).toBe(
			'Publie surtout les routes cantonales ; les routes communales n’y figurent pas toujours.'
		);
		expect(libelleLimites(SOURCES.find((s) => s.id === 'camac-permis')!)).toBeNull();
	});
});

describe('source DGMR déclarée dans sources.json', () => {
	const dgmr = SOURCES.find((s) => s.id === 'dgmr-restrictions')!;
	const c = deduireCouverture({
		sources: SOURCES,
		etat: etat({ 'dgmr-restrictions': disponible }),
		couches: [couche('routes', ['dgmr-restrictions'])],
		communes: communesJ0,
		maintenant: MAINTENANT
	});

	it('couvre le canton en mode API, sans griser aucune commune', () => {
		expect(dgmr.couverture).toEqual({ communes: 'canton', mode: 'api' });
		expect(libelleCellule(c.cellule('routes', 5586))).toEqual(['API · disponible']);
		expect(libelleCellule(c.cellule('routes', 5624))).toEqual(['API · disponible']);
		expect(c.grisees('routes')).toEqual([]);
	});

	it('ne change ni le mode ni l’état par ses limites', () => {
		const sans = deduireCouverture({
			sources: [{ ...dgmr, limites: null }],
			etat: etat({ 'dgmr-restrictions': disponible }),
			couches: [couche('routes', ['dgmr-restrictions'])],
			communes: communesJ0,
			maintenant: MAINTENANT
		});
		expect(c.paire('dgmr-restrictions', 5586)).toEqual(sans.paire('dgmr-restrictions', 5586));
		expect(c.sources).toHaveLength(1);
		expect(c.sources[0].communes).toBe(300);
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

	it("mène à l'issue panne-source de sa plateforme pour une commune scrapée", () => {
		const url = new URL(lienPannes(sourceSite()));
		expect(url.searchParams.get('q')).toBe('is:issue is:open label:panne-source in:title "Panne : i-web"');
	});

	it('donne null si le fichier est absent, illisible ou injoignable', async () => {
		expect(await chargerEtatSources(async () => reponse('Not found', 404), 'https://d')).toBeNull();
		expect(await chargerEtatSources(async () => reponse('{', 200), 'https://d')).toBeNull();
		expect(await chargerEtatSources(() => Promise.reject(new TypeError('réseau')), 'https://d')).toBeNull();
	});
});
