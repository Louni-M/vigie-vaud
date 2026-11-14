/**
 * La façon dont la personne s'est servie de la page en dernier : au doigt, au pointeur (souris, stylet) ou au
 * clavier. Rendre le focus à un champ de saisie ouvre le clavier de l'écran : après un toucher, on s'en garde.
 *
 * C'est le geste qui compte, pas l'écran : un téléphone peut avoir un clavier, une tablette une souris.
 */
export type Saisie = 'toucher' | 'pointeur' | 'clavier';

/**
 * La saisie que trahit un évènement. Les touches d'un clavier à l'écran arrivent sans nom (« Unidentified », ou
 * « Process » pendant une composition) : elles suivent un toucher, qu'elles ne remplacent pas (`null`).
 */
export function saisieDe(
	e: { type: 'pointerdown'; pointerType: string } | { type: 'keydown'; key: string }
): Saisie | null {
	if (e.type === 'pointerdown') return e.pointerType === 'touch' ? 'toucher' : 'pointeur';
	return e.key === 'Unidentified' || e.key === 'Process' ? null : 'clavier';
}

let derniere: Saisie | null = null;

/** La dernière saisie vue depuis `suivreSaisie` ; `null` avant la première. */
export const derniereSaisie = () => derniere;

/** Suit les saisies de la personne dans la page ; renvoie de quoi cesser. */
export function suivreSaisie(): () => void {
	const noter = (e: PointerEvent | KeyboardEvent) => {
		const s = saisieDe(e as Parameters<typeof saisieDe>[0]);
		if (s) derniere = s;
	};
	addEventListener('pointerdown', noter, { capture: true, passive: true });
	addEventListener('keydown', noter, { capture: true, passive: true });
	return () => {
		removeEventListener('pointerdown', noter, { capture: true });
		removeEventListener('keydown', noter, { capture: true });
	};
}
