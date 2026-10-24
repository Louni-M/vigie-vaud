import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import type { TransitionConfig } from 'svelte/transition';
import {
	avancementDeBulle,
	bulleEntree,
	bulleSortie,
	cercleDeBulle,
	DUREE_BULLE,
	rayonDeBulle,
	repliSousLaBulle,
	voletNeuf
} from './bulle.js';

const PERMIS = { largeur: 360, hauteur: 604 };
const HOTELS = { largeur: 360, hauteur: 300 };
const FIL = { largeur: 380, hauteur: 604 };

describe('cercle de la bulle d’un volet', () => {
	it('part du centre de l’icône, avec son rayon', () => {
		const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
		expect(c).toMatchObject({ x: -46, y: 46, r0: 17 });
	});
	it('finit assez grand pour couvrir le coin le plus éloigné du volet', () => {
		const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
		expect(c.r1).toBeCloseTo(Math.hypot(360 + 46, 604 - 46));
	});
	it('ramène dans la hauteur du volet une icône plus basse que lui', () => {
		const c = cercleDeBulle({ largeur: 360, hauteur: 222 }, { x: -46, y: 256, rayon: 17 });
		expect(c.y).toBe(222 - 28);
	});
	it('garde la hauteur de l’icône quand le volet descend jusqu’à elle', () => {
		expect(cercleDeBulle(HOTELS, { x: -46, y: 256, rayon: 17 }).y).toBe(256);
	});
});

describe('rayon de la bulle pendant l’ouverture', () => {
	const c = cercleDeBulle(PERMIS, { x: -46, y: 46, rayon: 17 });
	it('va du rayon de l’icône au rayon final', () => {
		expect(rayonDeBulle(0, c)).toBeCloseTo(17);
		expect(rayonDeBulle(1, c)).toBeCloseTo(c.r1);
	});
	it('ne découvre jamais plus de 9 % du disque final d’une image à l’autre, à 30 images par seconde', () => {
		// 600 ms à 30 images par seconde : 18 images, comme dans le navigateur de Claude Desktop.
		const aire = (t: number) => rayonDeBulle(t, c) ** 2 / c.r1 ** 2;
		const pas = Array.from({ length: 18 }, (_, i) => aire((i + 1) / 18) - aire(i / 18));
		expect(Math.max(...pas)).toBeLessThan(0.09);
	});
});

describe('repli de l’ancien volet sous la nouvelle bulle', () => {
	it('ne bouge pas au départ', () => {
		expect(repliSousLaBulle(0, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 0 });
	});
	it('finit à la taille du nouveau volet, avant la fin', () => {
		expect(repliSousLaBulle(0.85, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 304 });
		expect(repliSousLaBulle(1, PERMIS, HOTELS)).toEqual({ droite: 0, bas: 304 });
	});
	it('replie aussi par la droite le fil, plus large qu’un volet', () => {
		expect(repliSousLaBulle(1, FIL, PERMIS)).toEqual({ droite: 20, bas: 0 });
	});
	it('ne replie rien sous un volet plus grand', () => {
		expect(repliSousLaBulle(1, HOTELS, PERMIS)).toEqual({ droite: 0, bas: 0 });
	});
});

describe('avancement de l’ouverture', () => {
	it('ne prend pas l’appel de Svelte à 0, avant la transition, pour la première image', () => {
		const avancement = avancementDeBulle();
		expect(avancement(0)).toBe(0);
		// Première image peinte en retard, à 40 % du temps : la bulle part de là, sans bond.
		expect(avancement(0.4)).toBe(0);
		expect(avancement(0.7)).toBeCloseTo(0.5);
		expect(avancement(1)).toBe(1);
	});
});

/** Un élément réduit à ce que touchent les transitions : style, classe, enfants, taille fixe. */
interface Faux {
	style: Record<string, string>;
	classList: { contains: (c: string) => boolean };
	inert: boolean;
	offsetWidth: number;
	offsetHeight: number;
	clientWidth: number;
	clientHeight: number;
	scrollTop: number;
	getBoundingClientRect: () => { left: number; top: number; width: number; height: number };
	children: Faux[];
	parentElement: Faux | null;
	append: (e: Faux) => void;
	remove: Mock;
	animate: Mock;
}
function element(classes: string[] = []): Faux {
	const el: Faux = {
		style: {} as Record<string, string>,
		classList: { contains: (c: string) => classes.includes(c) },
		inert: false,
		offsetWidth: 360,
		offsetHeight: 604,
		clientWidth: 360,
		clientHeight: 604,
		scrollTop: 0,
		getBoundingClientRect: () => ({ left: 0, top: 0, width: 360, height: 604 }),
		children: [],
		parentElement: null,
		append(e) {
			el.children.push(e);
			e.parentElement = el;
		},
		remove: vi.fn(),
		animate: vi.fn()
	};
	return el;
}
const entree = (node: Faux) => bulleEntree(node as unknown as HTMLElement, { id: 'permis' });
const sortie = (node: Faux, ouvert: string | null) =>
	bulleSortie(node as unknown as HTMLElement, { id: 'permis', ouvert: () => ouvert })();
const tick = (config: TransitionConfig, t: number) => config.tick?.(t, 1 - t);

describe('transitions d’un volet', () => {
	let reduit: boolean;
	beforeEach(() => {
		reduit = false;
		vi.stubGlobal('document', { querySelector: () => null, createElement: () => element() });
		vi.stubGlobal('matchMedia', () => ({ matches: reduit }));
	});
	afterEach(() => vi.unstubAllGlobals());

	it('une sortie arrête l’ouverture en cours : elle n’écrit plus rien et son liseré est retiré', () => {
		const node = element(['volet']);
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 0.3);
		const fermeture = sortie(node, null);
		expect(node.children[0].remove).toHaveBeenCalled();
		tick(fermeture, 0.5);
		const pendant = { ...node.style };
		// Svelte continue de faire avancer l'entrée, puis l'achève.
		tick(ouverture, 0.6);
		tick(ouverture, 1);
		expect(node.style).toEqual(pendant);
	});

	it('une ouverture interrompue par une autre couche rentre dans son icône, depuis là où elle en était', () => {
		const node = element(['volet']);
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 0.3);
		const avant = { ...node.style };
		const fermeture = sortie(node, 'hotels');
		expect(fermeture.duration).toBeLessThan(DUREE_BULLE);
		tick(fermeture, 1);
		expect(node.style).toMatchObject({ clipPath: avant.clipPath, transform: avant.transform });
		// Elle passe sous la nouvelle bulle.
		expect(node.style.zIndex).toBe('2');
	});

	it('une ouverture finie se replie sous la nouvelle bulle', () => {
		const node = element(['volet']);
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 1);
		const repli = sortie(node, 'hotels');
		expect(repli.duration).toBe(DUREE_BULLE);
		tick(repli, 0.5);
		expect(node.style.clipPath).toMatch(/^inset\(/);
		expect(node.style.zIndex).toBe('2');
	});

	it('une nouvelle entrée retire le liseré de celle qu’elle interrompt', () => {
		const node = element(['volet']);
		tick(entree(node), 0.3);
		entree(node);
		expect(node.children[0].remove).toHaveBeenCalled();
		expect(node.children[1].remove).not.toHaveBeenCalled();
	});

	it('le liseré, coupé à la partie visible du volet, ne le fait pas défiler', () => {
		const node = element(['volet']);
		node.scrollTop = 120;
		node.clientWidth = 345;
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 0.5);
		const cadre = node.children[0];
		expect(cadre.style).toMatchObject({ overflow: 'hidden', top: '120px', width: '345px', height: '604px' });
		// Le disque, bien plus grand que le volet, est dans le cadre.
		expect(cadre.children[0].style.width).not.toBe('');
	});

	it('l’ouverture reste au niveau des volets, sous la recherche', () => {
		const node = element(['volet']);
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 0.5);
		expect(node.style.zIndex).toBe('');
	});

	it.each([
		['replié sous une autre couche', 'hotels'],
		['en train de se fermer', null]
	])('rouvert alors qu’il était %s, le volet n’est plus touché par la sortie que Svelte remet à son début', (_, ouvert) => {
		const node = element(['volet']);
		const ouverture = entree(node);
		tick(ouverture, 0);
		tick(ouverture, 1);
		const fermeture = sortie(node, ouvert);
		tick(fermeture, 0.5);
		const reouverture = entree(node);
		tick(reouverture, 0);
		const avant = { ...node.style };
		expect(avant.clipPath).toMatch(/^circle\(/);
		expect(avant.zIndex).toBe('');
		tick(fermeture, 1);
		expect(node.style).toEqual(avant);
	});

	it('avec les mouvements réduits, l’ancien volet s’efface aussi en fondu quand une autre couche s’ouvre', () => {
		reduit = true;
		const repli = sortie(element(['volet']), 'hotels');
		expect(repli.tick).toBeUndefined();
		expect(repli.css?.(0.5, 0.5)).toBe('opacity: 0.5');
	});

	it('avec les mouvements réduits, un volet rouvert pendant son fondu revient au niveau des volets', () => {
		reduit = true;
		const node = element(['volet']);
		sortie(node, 'hotels');
		expect(node.style.zIndex).toBe('2');
		entree(node);
		expect(node.style.zIndex).toBe('');
	});
});

describe('nouveau volet, sous lequel l’ancien se replie', () => {
	it('écarte un volet qui sort encore, après deux changements rapides', () => {
		const parent = element();
		const ancien = element(['volet']);
		const sortant = element(['volet']);
		const neuf = element(['volet']);
		for (const e of [ancien, sortant, neuf]) parent.append(e);
		ancien.inert = sortant.inert = true;
		expect(voletNeuf(ancien as unknown as HTMLElement)).toBe(neuf);
	});
});
