/**
 * Le volet sort en bulle de l'icône du rail qui l'ouvre : une révélation circulaire (`clip-path: circle()`) part de
 * l'icône et grandit jusqu'au coin le plus éloigné du volet, avec un léger rebond d'échelle. Ouvrir une autre couche
 * ne retire pas l'ancien volet : la nouvelle bulle part de sa propre icône et le recouvre, pendant que l'ancien se
 * replie dessous jusqu'à la taille du nouveau. Fermer le volet fait rentrer la bulle dans son icône.
 *
 * Le cercle est recalculé à chaque image, d'après la taille du volet à cet instant : le Volet d'une couche est chargé
 * à part et fait grandir le volet pendant la transition. Un rayon fixé au départ s'arrête avant le bas du volet, et le
 * reste apparaît d'un coup à la fin ; gonflé d'avance (jusqu'au bas de la carte), il découvre tout le volet dans le
 * premier tiers, et le navigateur de Claude Desktop, à 30 images par seconde, n'en montre que six à-coups.
 *
 * Pas de View Transitions API : elle photographierait toute la page, carte MapLibre comprise, et figerait la carte
 * pendant l'animation. Une transition Svelte ne touche que le volet.
 */
import { backOut, cubicIn, cubicInOut, sineOut } from 'svelte/easing';
import type { TransitionConfig } from 'svelte/transition';

/** Durée de l'ouverture, et du repli de l'ancien volet sous la nouvelle bulle (ms). */
export const DUREE_BULLE = 600;
/** Durée de la fermeture, la bulle qui rentre dans son icône (ms). */
const DUREE_FERMETURE = 300;
/** Marge (px) entre le centre de la bulle et le haut ou le bas du volet. */
const MARGE = 28;

export interface Taille {
	largeur: number;
	hauteur: number;
}

/** La pastille d'une icône du rail, dans le repère du volet : son centre et son rayon. */
export interface Icone {
	x: number;
	y: number;
	rayon: number;
}

/** Le cercle de la bulle dans le repère du volet : son centre, son rayon de départ et son rayon final. */
export interface Cercle {
	x: number;
	y: number;
	r0: number;
	r1: number;
}

/**
 * Le cercle de la bulle d'un volet : centré sur l'icône, à sa hauteur ramenée dans celle du volet, et assez grand à
 * la fin pour couvrir le coin le plus éloigné. Le volet descend au moins jusqu'à la dernière icône du rail (hauteur
 * minimale de `.volet`) : la bulle sort donc de son icône ; la marge ne sert que si la carte est trop basse.
 */
export function cercleDeBulle(volet: Taille, icone: Icone | null): Cercle {
	const x = icone?.x ?? 0;
	const y = Math.min(Math.max(icone?.y ?? 0, MARGE), Math.max(MARGE, volet.hauteur - MARGE));
	const coins = [
		[0, 0],
		[volet.largeur, 0],
		[0, volet.hauteur],
		[volet.largeur, volet.hauteur]
	];
	const r1 = Math.max(...coins.map(([cx, cy]) => Math.hypot(cx - x, cy - y)));
	return { x, y, r0: icone?.rayon ?? 0, r1 };
}

/**
 * Rayon de la bulle à l'instant `t` (0 à 1). L'aire découverte croît comme le carré du rayon : l'accélération porte
 * sur l'aire, qui progresse ainsi régulièrement, sans image qui en découvre beaucoup plus que les autres.
 */
export const rayonDeBulle = (t: number, { r0, r1 }: Cercle) => Math.sqrt(r0 ** 2 + (r1 ** 2 - r0 ** 2) * sineOut(t));

/**
 * Repli de l'ancien volet sous la nouvelle bulle, à l'avancement `u` (0 à 1) : ce qu'on retire à sa droite et en bas
 * pour qu'il finisse à la taille du nouveau. Sans repli, le bas d'un grand volet (Permis) restait visible sous un
 * petit (Hôtels de ville) et disparaissait d'un coup quand on le retirait. Le repli finit un peu avant la fin, quand
 * la bulle a recouvert le haut du volet.
 */
export function repliSousLaBulle(u: number, ancien: Taille, neuf: Taille | null): { droite: number; bas: number } {
	if (!neuf) return { droite: 0, bas: 0 };
	const e = cubicInOut(Math.min(1, Math.max(0, u) / 0.85));
	return {
		droite: Math.max(0, ancien.largeur - neuf.largeur) * e,
		bas: Math.max(0, ancien.hauteur - neuf.hauteur) * e
	};
}

/**
 * Avancement de l'ouverture d'après le temps brut de la transition. Monter le Volet d'une couche (la liste des Permis)
 * peut retarder la première image : l'horloge de la transition a déjà avancé, et la bulle partirait d'un bond.
 * L'avancement repart donc de la première image peinte. Svelte appelle d'abord la transition à 0, avant même de la
 * lancer : cet appel ne compte pas comme une image.
 */
export function avancementDeBulle(): (brut: number) => number {
	let premiere: number | null = null;
	return (brut) => {
		if (brut >= 1) return 1;
		if (brut <= 0) return 0;
		premiere ??= brut;
		return (brut - premiere) / (1 - premiere);
	};
}

const reduit = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
const fondu = (t: number) => `opacity: ${t}`;

/** La pastille ronde de l'icône du rail de la couche (ou du fil), premier enfant de son bouton. */
function pastilleDe(id: string) {
	const bouton = document.querySelector<HTMLElement>(`[data-couche="${id}"]`);
	return (bouton?.firstElementChild as HTMLElement | null) ?? bouton;
}

/** Taille de mise en page du volet, sans l'échelle de l'animation. */
const tailleDe = (node: HTMLElement): Taille => ({ largeur: node.offsetWidth, hauteur: node.offsetHeight });

/** Le cercle de la bulle à cet instant, d'après la position de l'icône et la taille du volet. */
function cercleActuel(node: HTMLElement, pastille: HTMLElement | null): Cercle {
	const taille = tailleDe(node);
	const v = node.getBoundingClientRect();
	const echelle = taille.largeur ? v.width / taille.largeur : 1;
	const p = pastille?.getBoundingClientRect();
	const icone = p && {
		x: (p.left + p.width / 2 - v.left) / echelle,
		y: (p.top + p.height / 2 - v.top) / echelle,
		rayon: p.width / 2
	};
	return cercleDeBulle(taille, icone ?? null);
}

function poser(node: HTMLElement, { x, y }: Cercle, rayon: number, echelle: number) {
	node.style.clipPath = `circle(${rayon}px at ${x}px ${y}px)`;
	node.style.transform = `scale(${echelle})`;
	node.style.transformOrigin = `${x}px ${y}px`;
}

/** Où en était une ouverture interrompue : la part du rayon final atteinte, et l'échelle. */
interface Ouverture {
	part: number;
	echelle: number;
}

/**
 * L'ouverture en cours de chaque volet, et de quoi l'arrêter. Avec `in:` et `out:` séparés, Svelte n'arrête pas
 * l'entrée quand le volet sort, et ne la termine pas quand une nouvelle entrée l'interrompt : sans arrêt, elle
 * continuerait d'écrire son cercle pendant la sortie, puis effacerait tout à la fin, et son liseré resterait.
 */
const ouvertures = new WeakMap<HTMLElement, () => Ouverture>();

function arreterOuverture(node: HTMLElement): Ouverture | null {
	const arreter = ouvertures.get(node);
	ouvertures.delete(node);
	return arreter?.() ?? null;
}

/** Entrée : la bulle grandit depuis l'icône, au-dessus de tout volet encore affiché. */
export function bulleEntree(node: HTMLElement, { id }: { id: string }): TransitionConfig {
	arreterOuverture(node);
	if (reduit()) return { duration: 120, css: fondu };
	const pastille = pastilleDe(id);
	// L'icône « pousse » la bulle : un petit battement.
	pastille?.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.18)' }, { transform: 'scale(1)' }], {
		duration: 320,
		easing: 'ease-out'
	});
	// Le bord de la bulle : un disque de même rayon, ombré vers l'intérieur. Le clip-path coupe tout ce qui dépasse :
	// il ne reste qu'un liseré juste à l'intérieur du cercle, visible là où il passe sur l'ancien volet.
	const bord = document.createElement('div');
	Object.assign(bord.style, {
		position: 'absolute',
		borderRadius: '50%',
		boxShadow: 'inset 0 0 0 1.5px rgb(0 0 0 / 0.10), inset 0 0 22px 2px rgb(0 0 0 / 0.20)',
		pointerEvents: 'none',
		zIndex: '1'
	});
	node.append(bord);
	// Avant la première image : le volet ne doit pas apparaître entier un instant.
	const depart = cercleActuel(node, pastille);
	poser(node, depart, depart.r0, 0.9);
	node.style.zIndex = '5';
	const avancement = avancementDeBulle();
	let ouverture: Ouverture = { part: 0, echelle: 0.9 };
	let arretee = false;
	// La sortie reprend le cercle là où il en est ; elle ne passe plus devant le volet qui s'ouvre.
	ouvertures.set(node, () => {
		arretee = true;
		bord.remove();
		node.style.zIndex = '';
		return ouverture;
	});
	return {
		duration: DUREE_BULLE,
		tick: (brut) => {
			if (arretee) return;
			const t = avancement(brut);
			const c = cercleActuel(node, pastille);
			const r = rayonDeBulle(t, c);
			ouverture = { part: c.r1 > c.r0 ? (r - c.r0) / (c.r1 - c.r0) : 1, echelle: 0.9 + 0.1 * backOut(t) };
			poser(node, c, r, ouverture.echelle);
			// Une sortie interrompue (le volet rouvert) a pu le repasser sous les autres.
			node.style.zIndex = '5';
			Object.assign(bord.style, { left: `${c.x - r}px`, top: `${c.y - r}px`, width: `${2 * r}px`, height: `${2 * r}px` });
			// Le liseré s'efface sur la fin, quand le cercle a presque couvert le volet.
			bord.style.opacity = String(Math.min(1, (1 - t) * 3));
			if (t === 1) {
				ouvertures.delete(node);
				bord.remove();
				Object.assign(node.style, { clipPath: '', transform: '', transformOrigin: '', zIndex: '' });
			}
		}
	};
}

/**
 * Le nouveau volet, sous lequel l'ancien se replie : un autre `.volet` du même parent qui n'est pas en train de sortir
 * (Svelte rend `inert` un élément qui sort). Après deux changements rapides, un volet qui sort encore est là aussi.
 */
export function voletNeuf(node: HTMLElement): HTMLElement | undefined {
	return [...(node.parentElement?.children ?? [])].find(
		(e): e is HTMLElement => e !== node && e.classList.contains('volet') && !(e as HTMLElement).inert
	);
}

/**
 * Sortie : si une autre couche s'ouvre (`ouvert()` n'est pas nul), le volet se replie sous la nouvelle bulle ; sinon,
 * ou si son ouverture n'était pas finie, il rentre dans son icône depuis là où il en est. En sortie, Svelte fait aller
 * `t` de 1 à 0. La configuration est rendue par une fonction : Svelte garde celle d'une sortie interrompue (le volet
 * rouvert) pour la sortie suivante, et une fonction est rappelée à chaque sortie, une fois le nouveau volet monté.
 */
export function bulleSortie(
	node: HTMLElement,
	{ id, ouvert }: { id: string; ouvert: () => string | null }
): () => TransitionConfig {
	return () => {
		const interrompue = arreterOuverture(node);
		if (reduit()) {
			node.style.zIndex = '2';
			return { duration: 120, css: fondu };
		}
		if (ouvert() !== null && !interrompue) {
			return {
				duration: DUREE_BULLE,
				tick: (t) => {
					const n = voletNeuf(node);
					const { droite, bas } = repliSousLaBulle(1 - t, tailleDe(node), n ? tailleDe(n) : null);
					node.style.zIndex = '2';
					node.style.clipPath = `inset(0px ${droite}px ${bas}px 0px round 10px)`;
				}
			};
		}
		const { part, echelle } = interrompue ?? { part: 1, echelle: 1 };
		const pastille = pastilleDe(id);
		return {
			duration: DUREE_FERMETURE,
			tick: (t) => {
				const c = cercleActuel(node, pastille);
				poser(node, c, c.r0 + (c.r1 - c.r0) * part * cubicIn(t), 0.92 + (echelle - 0.92) * t);
			}
		};
	};
}
