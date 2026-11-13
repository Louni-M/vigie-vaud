import { afterEach, describe, expect, it } from 'vitest';
import { flushSync } from 'svelte';
import { creerRegistre, type Registre, type VueCarte } from './registre.svelte.js';
import type { CoucheInscrite, Lieu } from './types.js';
import { LUTRY, PULLY } from '#tests/faux-canton.js';
import { creerFauxNavigateur, type FauxNavigateur } from '#tests/faux-navigateur.svelte.js';

/*
 * Le registre par scénarios, sans navigateur ni SvelteKit : un faux navigateur tient l'historique, une fausse carte
 * note ce qu'on lui demande.
 */

/** Un dossier de Pully, avec sa position. */
const DOSSIER = { couche: 'permis', element: '1' };
const POSITION: [number, number] = [6.67, 46.5];
const LIEUX: Record<string, Lieu> = { '1': { fiches: [{ commune: 'pully' }], position: POSITION } };

const composant = async () => ({ default: (() => {}) as never });

/** Deux couches : Permis (ses dossiers, `?d=`) et Conseils, qui déclare la fiche du Grand Conseil. */
const COUCHES: CoucheInscrite[] = [
	{
		id: 'permis',
		nom: 'Permis',
		sources: [],
		permanente: false,
		activeParDefaut: true,
		icone: { signe: 'P', couleur: '#000' },
		cleElement: 'd',
		localiser: async (element) => LIEUX[element] ?? null,
		introuvable: (element) => `Aucun dossier n° ${element}.`,
		composants: { Carte: composant, Volet: composant, Onglet: composant }
	},
	{
		id: 'conseils',
		nom: 'Conseils',
		sources: [],
		permanente: false,
		activeParDefaut: false,
		icone: { signe: 'C', couleur: '#000' },
		fiche: {
			id: 'grand-conseil',
			chemin: '/grand-conseil',
			nom: 'Grand Conseil',
			sousTitre: '',
			description: '',
			position: [6.63, 46.52]
		},
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
		await new Promise((r) => setTimeout(r));
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
		expect(mouvements).toEqual([{ aller: { lon: 6.67, lat: 46.5, zoom: 16 }, anime: false }]);
	});

	it('retire le dossier introuvable de l’adresse, et le dit près de la recherche', async () => {
		const { nav, registre } = await arriver('/commune/lutry?d=404&volet=permis');

		expect(nav.historique).toEqual(['/commune/lutry?volet=permis']);
		expect(registre.fiche).toEqual({ commune: 'lutry' });
		expect(registre.ouvert).toBeNull();
		expect(registre.avis).toBe('Aucun dossier n° 404.');
		expect(registre.volet).toBe('permis');
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
		expect(nav.historique).toEqual(['/', '/commune/pully', '/commune/pully?d=1']);
		mouvements.length = 0;

		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/commune/pully');
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toBeNull();
		expect(mouvements).toEqual([]);

		await nav.suivant();
		await calme();
		expect(nav.adresse).toBe('/commune/pully?d=1');
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(mouvements).toEqual([{ voler: POSITION, zoom: 16 }]);

		await nav.precedent();
		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/');
		expect(registre.fiche).toBeNull();
		expect(registre.ouvert).toBeNull();
		expect(mouvements.at(-1)).toBe('canton');
		expect(nav.historique).toEqual(['/', '/commune/pully', '/commune/pully?d=1']);
	});

	it('rétablissent le volet ouvert : il entre dans l’historique, et la vue de la carte non', async () => {
		const { nav, registre } = await arriver('/');
		registre.deplacement([6.5, 46.4, 6.8, 46.6], { lat: 46.5, lon: 6.65, zoom: 12 }, false);
		await calme();
		registre.volet = 'conseils';
		await calme();
		expect(nav.historique).toEqual(['/?vue=46.50000,6.65000,12.00', '/?vue=46.50000,6.65000,12.00&volet=conseils']);

		await nav.precedent();
		await calme();
		expect(registre.volet).toBe('fil');
		await nav.suivant();
		await calme();
		expect(registre.volet).toBe('conseils');
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
		expect(nav.historique).toEqual(['/commune/pully', '/commune/pully?d=1']);

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
		expect(nav.historique).toEqual(['/', '/commune/pully?d=1']);
		expect(nav.etat).toEqual({ element: { depuis: null } });

		registre.fermer();
		await calme();
		expect(nav.historique).toEqual(['/', '/commune/pully']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toBeNull();
	});

	it('remonte aussi les entrées poussées par-dessus le dossier, et garde le volet ouvert depuis', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.ouvrir(DOSSIER);
		await calme();
		registre.volet = 'conseils';
		await calme();
		expect(nav.historique).toEqual(['/commune/pully', '/commune/pully?d=1', '/commune/pully?d=1&volet=conseils']);

		registre.fermer();
		await calme();
		expect(nav.index).toBe(0);
		expect(nav.adresse).toBe('/commune/pully?volet=conseils');
		expect(registre.ouvert).toBeNull();
		expect(registre.volet).toBe('conseils');
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

	it('arrive sur la vue que nomme l’adresse', async () => {
		const { registre } = await arriver('/commune/pully?affichage=fil', { telephone: true });
		expect(registre.affichage).toBe('fil');
	});

	it('ouvre un dossier depuis la vue Fil sur la carte, en une seule entrée, et le retour ramène au fil', async () => {
		const { nav, registre } = await arriver('/', { telephone: true });
		registre.affichage = 'fil';
		await calme();
		expect(nav.historique).toEqual(['/', '/?affichage=fil']);

		registre.ouvrir(DOSSIER);
		expect(registre.affichage).toBe('carte');
		await calme();
		expect(nav.historique).toEqual(['/', '/?affichage=fil', '/commune/pully?d=1&affichage=carte']);
		expect(registre.fiche).toEqual({ commune: 'pully' });
		expect(registre.ouvert).toEqual(DOSSIER);
		expect(registre.affichage).toBe('carte');

		await nav.precedent();
		await calme();
		expect(nav.adresse).toBe('/?affichage=fil');
		expect(registre.fiche).toBeNull();
		expect(registre.ouvert).toBeNull();
		expect(registre.affichage).toBe('fil');
	});

	it('n’écrit pas la vue du téléphone sur bureau', async () => {
		const { nav, registre } = await arriver('/commune/pully');
		registre.affichage = 'carte';
		await calme();
		expect(nav.historique).toEqual(['/commune/pully']);
	});
});
