import { afterEach, describe, expect, it } from 'vitest';
import { flushSync } from 'svelte';
import { creerRegistre, type Registre, type VueCarte } from './registre.svelte.js';
import type { CoucheInscrite, Lieu, Rubrique } from './types.js';
import { SOMMAIRE } from './url.js';
import { LUTRY, PULLY } from '#tests/faux-canton.js';
import { creerFauxNavigateur, tache, type FauxNavigateur } from '#tests/faux-navigateur.svelte.js';

/*
 * Le registre par scénarios, sans navigateur ni SvelteKit : un faux navigateur tient l'historique, une fausse carte
 * note ce qu'on lui demande.
 */

/** Un dossier de Pully, avec sa position. */
const DOSSIER = { couche: 'permis', element: '1' };
const POSITION: [number, number] = [6.67, 46.5];
const LIEUX: Record<string, Lieu> = { '1': { fiches: [{ commune: 'pully' }], position: POSITION } };

const composant = async () => ({ default: (() => {}) as never });

const rubrique = (id: string, champs: Partial<Rubrique> = {}): Rubrique => ({
	id,
	nom: id,
	phrase: '',
	rang: 0,
	unite: { un: '', plusieurs: '' },
	portee: 'zone',
	compteur: () => Promise.reject(new Error('non chargé')),
	...champs
});

/**
 * Trois couches à onglet, chacune avec sa rubrique : Permis (ses dossiers, `?d=`), Conseils, qui déclare aussi la
 * fiche du Grand Conseil et sa rubrique, et Routes.
 */
const COUCHES: CoucheInscrite[] = [
	{
		id: 'permis',
		nom: 'Permis',
		sources: [],
		permanente: false,
		cleElement: 'd',
		localiser: async (element) => LIEUX[element] ?? null,
		introuvable: (element) => `Aucun dossier n° ${element}.`,
		rubriques: [rubrique('permis')],
		composants: { Carte: composant, Volet: composant, Onglet: composant, Fiche: composant }
	},
	{
		id: 'conseils',
		nom: 'Conseils',
		sources: [],
		permanente: false,
		fiche: {
			id: 'grand-conseil',
			chemin: '/grand-conseil',
			nom: 'Grand Conseil',
			sousTitre: '',
			description: '',
			position: [6.63, 46.52]
		},
		rubriques: [rubrique('conseils'), rubrique('grand-conseil', { fiche: 'grand-conseil' })],
		composants: { Carte: composant, Volet: composant, Onglet: composant }
	},
	{
		id: 'routes',
		nom: 'Routes',
		sources: [],
		permanente: false,
		rubriques: [rubrique('routes')],
		composants: { Carte: composant, Volet: composant, Onglet: composant }
	}
];

/** Une carte qui note les mouvements demandés par le registre. */
function fausseCarte() {
	const mouvements: unknown[] = [];
	const carte: VueCarte = {
		aller: (c, anime) => void mouvements.push({ aller: c, anime }),
		voler: (lon, lat, zoom) => void mouvements.push({ voler: [lon, lat], zoom }),
		vueCanton: () => void mouvements.push('canton'),
		cadrer: (emprise, anime) => void mouvements.push({ cadrer: emprise, anime })
	};
	return { carte, mouvements };
}

const fins: (() => void)[] = [];
afterEach(() => fins.splice(0).forEach((f) => f()));

/** Laisse aboutir navigations, localisations et effets. */
async function calme() {
	for (let i = 0; i < 10; i++) {
		flushSync();
		await tache();
	}
	flushSync();
}

interface Site {
	nav: FauxNavigateur;
	registre: Registre;
	mouvements: unknown[];
}

/** Arrive sur le site à `adresse`, sur bureau ou sur téléphone : la coquille crée le registre et le branche. */
async function arriver(adresse: string, { telephone = false } = {}): Promise<Site> {
	const nav = creerFauxNavigateur(adresse);
	const { carte, mouvements } = fausseCarte();
	let registre!: Registre;
	fins.push(
		$effect.root(() => {
			registre = creerRegistre(COUCHES, () => [PULLY, LUTRY], nav.navigateur);
			registre.brancherAdresse(
				() => carte,
				() => telephone
			);
		})
	);
	// SvelteKit appelle `afterNavigate` au montage de la coquille, une fois ses effets lancés.
	flushSync();
	nav.monter();
	await calme();
	return { nav, registre, mouvements };
}

describe('ouvrir un lien partagé', () => {
	it('mène le dossier de la carte seule à la fiche de sa commune, sans nouvelle entrée, et y va d’un saut', async () => {
		const { nav, registre, mouvements } = await arriver('/?d=1');

		expect(nav.historique).toEqual(['/commune/pully?d=1']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(registre.panneau).toBe('permis');
		expect(mouvements).toEqual([{ aller: { lon: 6.67, lat: 46.5, zoom: 16 }, anime: false }]);
	});

	it('retire le dossier introuvable de l’adresse, et le dit près de la recherche', async () => {
		const { nav, registre } = await arriver('/commune/lutry?d=404&volet=permis');

		expect(nav.historique).toEqual(['/commune/lutry?volet=permis']);
		expect(registre.fiche).toEqual({ commune: 'lutry' });
		expect(registre.ouvert).toBeNull();
		expect(registre.avis).toBe('Aucun dossier n° 404.');
		expect(registre.panneau).toBe('permis');
	});

	it('rétablit la vue partagée, qui l’emporte sur la fiche', async () => {
		const { nav, registre, mouvements } = await arriver('/commune/pully?vue=46.50000,6.60000,13.00');

		expect(nav.historique).toEqual(['/commune/pully?vue=46.50000,6.60000,13.00']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(mouvements).toEqual([{ aller: { lat: 46.5, lon: 6.6, zoom: 13 }, anime: false }]);
	});
});

describe('précédent et suivant du navigateur', () => {
	it('referment puis rouvrent le dossier ouvert dans la fiche, et la carte revient au canton', async () => {
		const { nav, registre, mouvements } = await arriver('/');
		registre.ouvrir({ commune: 'pully' });
		await calme();
		registre.ouvrir(DOSSIER);
		await calme();
		expect(nav.historique).toEqual(['/', '/commune/pully', '/commune/pully?d=1&volet=sommaire']);
		mouvements.length = 0;

		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/commune/pully');
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toBeNull();
		expect(mouvements).toEqual([]);

		await nav.suivant();
		await calme();
		expect(nav.adresse).toBe('/commune/pully?d=1&volet=sommaire');
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(mouvements).toEqual([{ voler: POSITION, zoom: 16 }]);

		await nav.precedent();
		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/');
		expect(registre.fiche).toBeNull();
		expect(registre.ouvert).toBeNull();
		expect(mouvements.at(-1)).toBe('canton');
		expect(nav.historique).toEqual(['/', '/commune/pully', '/commune/pully?d=1&volet=sommaire']);
	});

	it('rétablissent la rubrique ouverte : elle entre dans l’historique, et la vue de la carte non', async () => {
		const { nav, registre } = await arriver('/');
		expect(registre.panneau).toBe(SOMMAIRE);
		registre.deplacement([6.5, 46.4, 6.8, 46.6], { lat: 46.5, lon: 6.65, zoom: 12 }, false);
		await calme();
		registre.panneau = 'routes';
		await calme();
		expect(nav.historique).toEqual(['/?vue=46.50000,6.65000,12.00', '/?vue=46.50000,6.65000,12.00&volet=routes']);

		await nav.precedent();
		await calme();
		expect(registre.panneau).toBe(SOMMAIRE);
		await nav.suivant();
		await calme();
		expect(registre.panneau).toBe('routes');
	});
});

describe('de la carte à une fiche commune, et retour', () => {
	const VUE = { lat: 46.5, lon: 6.65, zoom: 12 };

	it('ouvre la fiche dans une nouvelle entrée, cadrée sur la commune ; le retour rend la vue de la carte', async () => {
		const { nav, registre, mouvements } = await arriver('/');
		registre.deplacement([6.5, 46.4, 6.8, 46.6], VUE, false);
		await calme();

		registre.ouvrir({ commune: 'pully' });
		await calme();
		expect(nav.historique).toEqual(['/?vue=46.50000,6.65000,12.00', '/commune/pully']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.commune).toBe(PULLY);
		expect(registre.titre).not.toBeNull();
		expect(mouvements).toEqual([{ cadrer: PULLY.cadre, anime: true }]);

		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/?vue=46.50000,6.65000,12.00');
		expect(registre.fiche).toBeNull();
		expect(registre.titre).toBeNull();
		expect(mouvements.at(-1)).toEqual({ aller: VUE, anime: true });
	});

	it('ferme la fiche vers la carte seule, dans une nouvelle entrée, en gardant la vue', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.deplacement([6.6, 46.45, 6.7, 46.55], VUE, false);
		await calme();

		registre.fermerFiche();
		await calme();
		expect(nav.historique).toEqual(['/commune/pully?vue=46.50000,6.65000,12.00', '/?vue=46.50000,6.65000,12.00']);
		expect(registre.fiche).toBeNull();
	});

	it('ouvre la fiche propre d’une couche à son chemin', async () => {
		const { nav, registre, mouvements } = await arriver('/');
		registre.ouvrir({ fiche: 'grand-conseil' });
		await calme();

		expect(nav.historique).toEqual(['/', '/grand-conseil']);
		expect(registre.fiche).toEqual({ fiche: 'grand-conseil' });
		expect(registre.propre?.fiche.nom).toBe('Grand Conseil');
		expect(mouvements).toEqual([{ voler: [6.63, 46.52], zoom: 16 }]);
	});

	it('ferme un dossier ouvert dans la fiche par un retour arrière', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.ouvrir(DOSSIER);
		await calme();
		expect(nav.historique).toEqual(['/commune/pully', '/commune/pully?d=1&volet=sommaire']);

		registre.fermer();
		await calme();
		expect(nav.index).toBe(0);
		expect(nav.adresse).toBe('/commune/pully');
		expect(registre.ouvert).toBeNull();
	});

	it('ferme un dossier ouvert depuis la carte seule en remplaçant l’adresse : le retour arrière quitterait la fiche', async () => {
		const { nav, registre } = await arriver('/');
		registre.ouvrir(DOSSIER);
		await calme();
		expect(nav.historique).toEqual(['/', '/commune/pully?d=1&volet=sommaire']);
		expect(nav.etat).toEqual({ element: { depuis: null } });

		registre.fermer();
		await calme();
		expect(nav.historique).toEqual(['/', '/commune/pully']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toBeNull();
	});

	it('remonte aussi les entrées poussées par-dessus le dossier, et garde la rubrique ouverte depuis', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.ouvrir(DOSSIER);
		await calme();
		registre.panneau = 'conseils';
		await calme();
		expect(nav.historique).toEqual([
			'/commune/pully',
			'/commune/pully?d=1&volet=sommaire',
			'/commune/pully?d=1&volet=conseils'
		]);

		registre.fermer();
		await calme();
		expect(nav.index).toBe(0);
		expect(nav.adresse).toBe('/commune/pully?volet=conseils');
		expect(registre.ouvert).toBeNull();
		expect(registre.panneau).toBe('conseils');
	});
});

describe('panneau : le sommaire ou une rubrique', () => {
	it('ouvre la rubrique que nomme une ancienne adresse de volet, et le sommaire pour les autres', async () => {
		expect((await arriver('/?volet=routes')).registre.panneau).toBe('routes');
		expect((await arriver('/?volet=conseils')).registre.panneau).toBe('conseils');
		for (const volet of ['fil', 'hotels-de-ville', '', 'inconnu'])
			expect((await arriver(`/?volet=${volet}`)).registre.panneau).toBe(SOMMAIRE);
	});

	it('n’écrit plus couches= : une ancienne adresse à couches= donne le sommaire', async () => {
		const { nav, registre } = await arriver('/?couches=routes');
		expect(registre.panneau).toBe(SOMMAIRE);
		expect(registre.dessinee).toBeNull();
		registre.panneau = 'routes';
		await calme();
		expect(nav.adresse).toBe('/?volet=routes');
	});

	it('garde le sommaire d’un dossier ouvert depuis le sommaire, au rechargement', async () => {
		const { registre } = await arriver('/commune/pully?d=1&volet=sommaire');
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(registre.panneau).toBe(SOMMAIRE);
	});

	it('reste sur le sommaire à la fiche du Grand Conseil, dont la rubrique n’a pas de volet', async () => {
		const { registre } = await arriver('/grand-conseil');
		expect(registre.panneau).toBe(SOMMAIRE);
	});
});

describe('couche dessinée', () => {
	it('aucune au sommaire, celle de la rubrique ouverte ensuite', async () => {
		const { registre } = await arriver('/');
		expect(registre.dessinee).toBeNull();
		registre.panneau = 'permis';
		expect(registre.dessinee).toBe('permis');
		registre.panneau = SOMMAIRE;
		registre.panneau = 'routes';
		expect(registre.dessinee).toBe('routes');
	});

	it('suit l’onglet de la fiche commune ouverte, sans changer le panneau', async () => {
		const { registre } = await arriver('/?volet=routes');
		registre.ouvrir({ commune: 'pully' });
		await calme();
		expect(registre.ongletCourant).toBe('permis');
		expect(registre.dessinee).toBe('permis');
		expect(registre.panneau).toBe('routes');

		// La liste des restrictions reste chargée et comptée pendant que la carte dessine les permis de la fiche.
		const routes = registre.contexte(COUCHES[2]);
		expect([routes.listee, routes.dessinee]).toEqual([true, false]);
		expect(registre.contexte(COUCHES[0]).dessinee).toBe(true);

		registre.onglet = 'routes';
		expect(registre.dessinee).toBe('routes');
		expect(registre.panneau).toBe('routes');
		expect([routes.listee, routes.dessinee]).toEqual([true, true]);
	});

	it('prend l’onglet de l’élément ouvert dans la fiche commune', async () => {
		const { registre } = await arriver('/commune/pully?d=1&onglet=routes');
		expect(registre.ongletCourant).toBe('permis');
		expect(registre.dessinee).toBe('permis');
	});

	it('reste celle de la rubrique quand la fiche du Grand Conseil est ouverte', async () => {
		const { registre } = await arriver('/grand-conseil?volet=routes');
		expect(registre.ongletCourant).toBeNull();
		expect(registre.dessinee).toBe('routes');
	});

	it('monte dès l’arrivée la carte des couches qui ont une fiche propre, puis celle de la couche dessinée', async () => {
		const { registre } = await arriver('/');
		const montees = () => ['permis', 'conseils', 'routes'].filter((id) => registre.montee(id));
		expect(montees()).toEqual(['conseils']);
		registre.panneau = 'routes';
		await calme();
		registre.panneau = SOMMAIRE;
		await calme();
		expect(montees()).toEqual(['conseils', 'routes']);
	});
});

describe('vue du téléphone', () => {
	it('arrive sur la vue Fiche d’une fiche, sans l’écrire ; changer de vue crée une entrée que le retour défait', async () => {
		const { nav, registre } = await arriver('/commune/pully', { telephone: true });
		expect(registre.affichage).toBe('fiche');
		expect(nav.historique).toEqual(['/commune/pully']);

		registre.affichage = 'carte';
		await calme();
		expect(nav.historique).toEqual(['/commune/pully', '/commune/pully?affichage=carte']);

		await nav.precedent();
		await calme();
		expect(registre.affichage).toBe('fiche');
	});

	it('arrive sur le panneau, la carte ou la fiche selon l’adresse', async () => {
		expect((await arriver('/', { telephone: true })).registre.affichage).toBe('panneau');
		expect((await arriver('/?affichage=fil', { telephone: true })).registre.affichage).toBe('panneau');
		expect((await arriver('/?affichage=couches', { telephone: true })).registre.affichage).toBe('panneau');
		expect((await arriver('/?vue=46.50000,6.60000,13.00', { telephone: true })).registre.affichage).toBe('carte');
		expect((await arriver('/commune/pully?affichage=carte', { telephone: true })).registre.affichage).toBe('carte');
	});

	it('ouvre un dossier depuis une rubrique sur la carte, en une seule entrée, et le retour ramène au panneau', async () => {
		const { nav, registre } = await arriver('/', { telephone: true });
		registre.panneau = 'permis';
		await calme();
		expect(nav.historique).toEqual(['/', '/?volet=permis']);

		registre.ouvrir(DOSSIER);
		expect(registre.affichage).toBe('carte');
		await calme();
		expect(nav.historique).toEqual(['/', '/?volet=permis', '/commune/pully?d=1&affichage=carte']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toEqual(DOSSIER);

		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/?volet=permis');
		expect(registre.ouvert).toBeNull();
		expect(registre.affichage).toBe('panneau');
		expect(registre.panneau).toBe('permis');
	});

	it('ouvre une fiche depuis le panneau dans la vue Fiche, et sa fermeture ramène au panneau', async () => {
		const { nav, registre } = await arriver('/', { telephone: true });
		registre.deplacement([6.5, 46.4, 6.8, 46.6], { lat: 46.5, lon: 6.65, zoom: 12 }, false);
		await calme();
		registre.ouvrir({ commune: 'pully' });
		await calme();
		expect(registre.affichage).toBe('fiche');

		registre.fermerFiche();
		await calme();
		expect(registre.affichage).toBe('panneau');
		// La carte a une vue : sans `affichage=`, l'adresse rouvrirait la carte.
		expect(nav.adresse).toBe('/?vue=46.50000,6.65000,12.00&affichage=panneau');
		expect((await arriver(nav.adresse, { telephone: true })).registre.affichage).toBe('panneau');
	});

	it('ramène à la carte la fermeture d’une fiche ouverte depuis la carte', async () => {
		const { registre } = await arriver('/?vue=46.50000,6.60000,13.00', { telephone: true });
		registre.ouvrir({ commune: 'pully' });
		await calme();
		expect(registre.affichage).toBe('carte');
		registre.affichage = 'fiche';
		await calme();

		registre.fermerFiche();
		await calme();
		expect(registre.affichage).toBe('carte');
	});

	it('ouvre la Recherche plein écran dans une entrée de même adresse, que le précédent referme sans rien fermer d’autre', async () => {
		const { nav, registre } = await arriver('/commune/pully?d=1&affichage=carte', { telephone: true });
		expect(registre.recherche).toBe(false);

		registre.ouvrirRecherche();
		expect(registre.recherche).toBe(true);
		await calme();
		expect(nav.historique).toEqual(['/commune/pully?d=1&affichage=carte', '/commune/pully?d=1&affichage=carte']);
		expect(nav.index).toBe(1);

		await nav.precedent();
		await calme();
		expect(registre.recherche).toBe(false);
		expect(nav.index).toBe(0);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(registre.affichage).toBe('carte');

		// Le suivant ne la rouvre pas : il mène à son entrée, sans rien changer.
		await nav.suivant();
		await calme();
		expect(registre.recherche).toBe(false);
		expect(nav.adresse).toBe('/commune/pully?d=1&affichage=carte');
		expect(registre.ouvert).toEqual(DOSSIER);

		// Rouverte, elle remplace l’entrée laissée par le suivant.
		await nav.precedent();
		await calme();
		registre.ouvrirRecherche();
		await calme();
		expect(nav.historique).toHaveLength(2);
		expect(nav.index).toBe(1);
	});

	it('referme la Recherche en retirant son entrée, au retour', async () => {
		const { nav, registre } = await arriver('/', { telephone: true });
		registre.ouvrirRecherche();
		await calme();

		registre.fermerRecherche();
		// Refermée au retour seulement : ce qu'on y a choisi s'ouvre une fois l'entrée retirée.
		expect(registre.recherche).toBe(true);
		await calme();
		expect(registre.recherche).toBe(false);
		expect(nav.index).toBe(0);
		expect(nav.adresse).toBe('/');
	});

	it('compte l’entrée de la Recherche dans celles que remonte la fermeture du dossier', async () => {
		const { nav, registre } = await arriver('/commune/pully?affichage=carte', { telephone: true });
		registre.ouvrir(DOSSIER);
		await calme();
		registre.ouvrirRecherche();
		await calme();
		expect(nav.historique).toHaveLength(3);

		// Refermée par le précédent ; le suivant mène à son entrée, d’où fermer le dossier ramène à la fiche.
		await nav.precedent();
		await calme();
		await nav.suivant();
		await calme();
		registre.fermer();
		await calme();
		expect(nav.index).toBe(0);
		expect(registre.ouvert).toBeNull();
	});

	it('n’écrit pas la vue du téléphone sur bureau', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.affichage = 'carte';
		await calme();
		expect(nav.historique).toEqual(['/commune/pully']);
	});
});

describe('composants des couches', () => {
	it('importe chaque composant une fois, et réimporte celui dont l’import a échoué', async () => {
		let essais = 0;
		const volet = async () => {
			if (++essais === 1) throw new Error('import raté');
			return { default: (() => {}) as never };
		};
		const couche: CoucheInscrite = { ...COUCHES[0], composants: { Carte: composant, Volet: volet } };
		const nav = creerFauxNavigateur('/');
		let registre!: Registre;
		fins.push($effect.root(() => void (registre = creerRegistre([couche], () => [PULLY], nav.navigateur))));

		await expect(registre.composant(couche, 'Volet')).rejects.toThrow('import raté');
		const p = registre.composant(couche, 'Volet');
		await p;
		expect(registre.composant(couche, 'Volet')).toBe(p);
		expect(essais).toBe(2);
		expect(registre.composant(couche, 'Onglet')).toBeNull();
	});
});
