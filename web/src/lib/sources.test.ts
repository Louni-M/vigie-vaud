import { describe, expect, it } from 'vitest';
import { sourceNonCouverte, sourceSite } from '#tests/faux-conseils.js';
import { sourcesDeLaCouche } from '#lib/couches/conseils/source.js';
import {
	cleConseil,
	communeDuConseil,
	conseilsCouverts,
	grouperSources,
	phraseSitesLus,
	listerConseils,
	nomDuConseil
} from './sources.js';
import type { Conseil, Plateforme, Source } from './schema.js';

const source = (id: string): Source => ({
	id,
	nom: `Source ${id}`,
	nom_court: id,
	attribution: { texte: id, lien: `https://exemple.ch/${id}`, licence: 'libre' },
	voie_acces: 'direct',
	fraicheur: 'requete',
	couverture: { communes: 'canton', mode: 'api' }
});

const SOURCES = ['fond', 'permis', 'recherche', 'ucv', 'limites'].map(source);

/** Groupes réduits à leur titre et aux identifiants de leurs sources, pour la lecture. */
const ids = (groupes: ReturnType<typeof grouperSources>) =>
	groupes.map((g) => [g.titre, g.sources.map((s) => s.id)]);

describe('liste Sources d’À propos', () => {
	it('groupe les sources par couche, dans l’ordre du registre, puis les autres sous « Carte et communes »', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis'] },
			{ nom: 'Hôtels de ville', sources: ['ucv'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis']],
			['Hôtels de ville', ['ucv']],
			['Carte et communes', ['fond', 'recherche', 'limites']]
		]);
	});

	it('cite une source partagée sous chaque couche qui la déclare', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis', 'limites'] },
			{ nom: 'Hôtels de ville', sources: ['ucv', 'limites'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis', 'limites']],
			['Hôtels de ville', ['ucv', 'limites']],
			['Carte et communes', ['fond', 'recherche']]
		]);
	});

	it('n’affiche pas de groupe vide', () => {
		const couches = [
			{ nom: 'Permis', sources: ['permis'] },
			{ nom: 'Sans source', sources: [] },
			{ nom: 'Tout le reste', sources: ['fond', 'recherche', 'ucv', 'limites'] }
		];
		expect(ids(grouperSources(couches, SOURCES))).toEqual([
			['Permis', ['permis']],
			['Tout le reste', ['fond', 'recherche', 'ucv', 'limites']]
		]);
	});
});

describe('conseils couverts, pour À propos', () => {
	const conseil = (id: string, nom: string, donne: Source['conseil']): Source => ({ ...source(id), nom, conseil: donne });
	const sources = [
		source('permis'),
		conseil('gc', 'Grand Conseil (OpenParlData)', { body_key: 'VD', donne: ['objets', 'seances'], groupe: 1965 }),
		source('fond'),
		conseil('yverdon', 'Conseil communal d’Yverdon-les-Bains (OpenParlData)', { body_key: '5938', donne: ['seances'] }),
		conseil('objets', 'Conseil qui ne donne que ses objets', { body_key: '1', donne: ['objets'] })
	];

	it('liste les sources qui ont un bloc conseil, dans l’ordre de sources.json, avec ce que chacune donne', () => {
		expect(listerConseils(sources).map((c) => [c.source.id, c.donne])).toEqual([
			['gc', 'objets et séances'],
			['yverdon', 'séances seulement'],
			['objets', 'objets seulement']
		]);
	});

	it('dit les trois niveaux d’une commune scrapée', () => {
		const niveaux = (['objets', 'preavis'] as const).map((d) =>
			conseil(`site-${d}`, 'Conseil communal (site de la commune)', { body_key: '1', donne: [d, 'seances'] })
		);
		const seules = conseil('site-seances', 'Conseil communal (site de la commune)', { body_key: '2', donne: ['seances'] });
		expect(listerConseils([...niveaux, seules]).map((c) => c.donne)).toEqual([
			'objets et séances',
			'séances et préavis',
			'séances seulement'
		]);
	});

	it('ne liste rien sans bloc conseil', () => {
		expect(listerConseils([source('permis'), source('fond')])).toEqual([]);
	});
});

/** Une plateforme déclarée dans la section `plateformes` de sources.json. */
const plateforme = (id: string, nom: string): Plateforme => ({
	id,
	nom,
	editeur: `Éditeur de ${nom}`,
	variantes: [{ id: 'seances', marqueur: 'marqueur', niveaux: [['seances']] }]
});
const PLATEFORMES = [
	plateforme('i-web', 'i-web'),
	plateforme('quicksite', 'Quicksite'),
	plateforme('webcommunes', 'Webcommunes')
];

/** Une commune lue sur son site, de la plateforme donnée. */
const commune = (ofs: number, nomPlateforme = 'i-web'): Source =>
	sourceSite({
		id: `site-${ofs}`,
		nom: `Conseil communal de ${ofs} (site de la commune)`,
		couverture: { communes: [ofs], mode: 'scrape' },
		conseil: { body_key: String(ofs), donne: ['seances'] },
		site: {
			plateforme: nomPlateforme,
			variante: 'seances',
			seances: `https://${ofs}.ch/seances`
		}
	});

/** Une commune d'une plateforme retenue déclarée non couverte (#154) : sa raison, sa plateforme, ni conseil ni sonde. */
const nonCouverte = (ofs: number, nomPlateforme = 'i-web'): Source => {
	const s = sourceNonCouverte('preavis_seuls', { bfs: ofs, nom: String(ofs), site: `https://${ofs}.ch` });
	return { ...s, site: { plateforme: nomPlateforme } };
};

describe('conseils couverts avec des communes lues sur leur site, pour À propos', () => {
	const conseil = (id: string, nom: string): Source => ({
		...source(id),
		nom,
		conseil: { body_key: id, donne: ['objets', 'seances'] }
	});
	const sources = [
		conseil('vd', 'Grand Conseil (OpenParlData)'),
		commune(5643),
		commune(5891, 'quicksite'),
		conseil('5586', 'Conseil communal de Lausanne (OpenParlData)'),
		nonCouverte(5790),
		commune(5642),
		nonCouverte(5822, 'webcommunes'),
		source('permis')
	];

	it('garde une ligne par conseil qui n’est pas lu sur un site, dans l’ordre de sources.json', () => {
		expect(conseilsCouverts(sources, PLATEFORMES).sources.map((c) => c.source.id)).toEqual(['vd', '5586']);
	});

	it('compte les communes lues sur leur site, par plateforme, sans les communes non couvertes', () => {
		expect(conseilsCouverts(sources, PLATEFORMES).sites).toEqual({
			communes: 3,
			plateformes: [
				{ nom: 'i-web', communes: 2 },
				{ nom: 'Quicksite', communes: 1 }
			]
		});
	});

	it('suit l’ordre de la section plateformes, pas celui des sources', () => {
		const ordre = [commune(5891, 'quicksite'), commune(5643)];
		expect(conseilsCouverts(ordre, PLATEFORMES).sites.plateformes.map((p) => p.nom)).toEqual(['i-web', 'Quicksite']);
	});

	it('ne compte aucune commune sans source communale couverte', () => {
		expect(
			conseilsCouverts([conseil('vd', 'Grand Conseil (OpenParlData)'), nonCouverte(5790)], PLATEFORMES).sites
		).toEqual({
			communes: 0,
			plateformes: []
		});
	});
});

describe('phrase des communes lues sur leur site, sous « Conseils couverts »', () => {
	it('donne le nombre de communes, puis chaque plateforme avec le sien', () => {
		const sites = {
			communes: 3,
			plateformes: [
				{ nom: 'i-web', communes: 2 },
				{ nom: 'Quicksite', communes: 1 }
			]
		};
		expect(phraseSitesLus(sites)).toBe('et 3 communes dont Vigie Vaud lit le site : i-web (2), Quicksite (1)');
	});

	it('accorde une seule commune au singulier', () => {
		expect(
			phraseSitesLus({
				communes: 1,
				plateformes: [{ nom: 'i-web', communes: 1 }]
			})
		).toBe('et 1 commune dont Vigie Vaud lit le site : i-web (1)');
	});

	it('ne dit rien sans commune lue', () => {
		expect(phraseSitesLus({ communes: 0, plateformes: [] })).toBeNull();
	});
});

describe('liste Sources d’À propos, avec des communes lues sur leur site', () => {
	const sources = [
		source('fond'),
		{
			...source('vd'),
			conseil: { body_key: 'VD', donne: ['objets', 'seances'] }
		} satisfies Source,
		commune(5643),
		commune(5891, 'quicksite'),
		nonCouverte(5790),
		nonCouverte(5822, 'webcommunes'),
		commune(5642)
	];
	const couches = [{ nom: 'Conseils', sources: ['vd', 'site-5643', 'site-5891', 'site-5642'] }];

	it('réunit toutes les sources communales, couvertes ou non, en une seule entrée « Sites des communes »', () => {
		expect(ids(grouperSources(couches, sources, PLATEFORMES))).toEqual([
			['Conseils', ['vd', 'sites-des-communes']],
			['Carte et communes', ['fond']]
		]);
	});

	it('nomme dans cette entrée les plateformes des communes couvertes, avec la licence et la voie de leurs sources', () => {
		const [conseils] = grouperSources(couches, sources, PLATEFORMES);
		expect(conseils.sources[1]).toEqual({
			id: 'sites-des-communes',
			nom: 'Sites des communes',
			plateformes: ['i-web', 'Quicksite'],
			licence: 'Actes officiels (art. 5 LDA) : métadonnées et liens seulement',
			voie_acces: 'cron'
		});
	});

	it('y range aussi les communes non couvertes que la couche Conseils déclare (#154), sans entrée à part', () => {
		const declarees = [{ nom: 'Conseils', sources: sourcesDeLaCouche(sources) }];
		expect(declarees[0].sources).toContain('site-5790');
		expect(ids(grouperSources(declarees, sources, PLATEFORMES))).toEqual([
			['Conseils', ['vd', 'sites-des-communes']],
			['Carte et communes', ['fond']]
		]);
	});

	it('n’ajoute pas l’entrée sans source communale', () => {
		expect(ids(grouperSources(couches, [source('fond'), source('vd')], PLATEFORMES))).toEqual([
			['Conseils', ['vd']],
			['Carte et communes', ['fond']]
		]);
	});
});

describe('clé, commune et nom d’un conseil, comme le cron', () => {
	it.each([
		['VD', 'vd', null],
		['5586', '5586', 5586],
		['5938', '5938', 5938]
	])('body_key %s : clé %s, commune %s', (body_key, cle, commune) => {
		const conseil: Conseil = { body_key, donne: ['objets'] };
		expect([cleConseil(conseil), communeDuConseil(conseil)]).toEqual([cle, commune]);
	});

	// Les mêmes cas que `nom_du_conseil` du cron (`pipeline/tests/test_sources.py`), qui écrit le nom de l'index :
	// un cas ajouté d'un côté s'ajoute de l'autre.
	it.each([
		['Grand Conseil (OpenParlData)', 'Grand Conseil'],
		['Conseil communal de Lausanne (OpenParlData)', 'Conseil communal de Lausanne'],
		["Conseil communal d'Yverdon-les-Bains (OpenParlData)", 'Conseil communal d’Yverdon-les-Bains'],
		['Conseil général de Nyon (OpenParlData, essai)', 'Conseil général de Nyon'],
		['Conseil communal (CC) de Morges', 'Conseil communal (CC) de Morges'],
		['Conseil communal de Pully', 'Conseil communal de Pully']
	])('« %s » → « %s »', (nomSource, nom) => {
		expect(nomDuConseil(nomSource)).toBe(nom);
	});
});
