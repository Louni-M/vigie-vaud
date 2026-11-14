/**
 * La façon dont la personne s'est servie de la page en dernier : au doigt, au pointeur (souris, stylet) ou au
 * clavier. Rendre le focus à un champ de saisie ouvre le clavier de l'écran : après un toucher, on s'en garde.
 *
 * C'est le geste qui compte, pas l'écran : un téléphone peut avoir un clavier, une tablette une souris.
 */
export type Saisie = 'toucher' | 'pointeur' | 'clavier';

/** Ce qu'on lit de l'élément qui reçoit une touche. */
export interface Cible {
	tagName: string;
	type?: string;
	isContentEditable?: boolean;
}

/** Champs `<input>` sans texte à taper : le clavier de l'écran ne s'ouvre pas pour eux. */
const SANS_TEXTE = new Set(['button', 'checkbox', 'color', 'file', 'image', 'radio', 'range', 'reset', 'submit']);

/** L'élément reçoit du texte tapé : le clavier de l'écran s'ouvre pour lui, sur un appareil tactile. */
export const champDeSaisie = (c: Cible | null) =>
	!!c &&
	(c.isContentEditable === true ||
		c.tagName === 'TEXTAREA' ||
		(c.tagName === 'INPUT' && !SANS_TEXTE.has((c.type ?? 'text').toLowerCase())));

/**
 * La saisie que trahit un évènement. Une touche tapée dans un champ de saisie peut venir du clavier de l'écran,
 * Entrée comprise (« Rechercher ») : elle ne dit rien (`null`), et la saisie d'avant reste, le toucher qui a ouvert
 * ce clavier. Hors d'un champ (Tab, Entrée sur un bouton, Échap dans une liste), c'est un vrai clavier.
 */
export function saisieDe(
	e: { type: 'pointerdown'; pointerType: string } | { type: 'keydown'; cible: Cible | null }
): Saisie | null {
	if (e.type === 'pointerdown') return e.pointerType === 'touch' ? 'toucher' : 'pointeur';
	return champDeSaisie(e.cible) ? null : 'clavier';
}

let derniere: Saisie | null = null;

/** La dernière saisie vue depuis `suivreSaisie` ; `null` avant la première. */
export const derniereSaisie = () => derniere;

/** Suit les saisies de la personne dans la page ; renvoie de quoi cesser. */
export function suivreSaisie(): () => void {
	const pointeur = (e: PointerEvent) => (derniere = saisieDe({ type: 'pointerdown', pointerType: e.pointerType }));
	const touche = (e: KeyboardEvent) => {
		const s = saisieDe({ type: 'keydown', cible: e.target instanceof HTMLElement ? e.target : null });
		if (s) derniere = s;
	};
	addEventListener('pointerdown', pointeur, { capture: true, passive: true });
	addEventListener('keydown', touche, { capture: true, passive: true });
	return () => {
		removeEventListener('pointerdown', pointeur, { capture: true });
		removeEventListener('keydown', touche, { capture: true });
	};
}
