/**
 * « Tous (n) », « Toutes les séances (n) » et « Objets de 2025 » disparaissent au clic : le focus irait au corps de
 * la page. Il va plutôt à la première ligne nouvellement affichée de `liste`, la `i`-ième : sur son lien ou son
 * bouton s'il en a un, sinon sur la ligne elle-même, rendue focalisable par le script seulement. Rend `false` s'il
 * n'y a pas de telle ligne, pour que l'appelant choisisse une autre cible.
 */
export function focaliserLigne(liste: HTMLElement | null | undefined, i: number): boolean {
	const ligne = liste?.children.item(i);
	if (!(ligne instanceof HTMLElement)) return false;
	const action = ligne.querySelector<HTMLElement>(':scope > a.ligne, :scope > button.ligne');
	if (action) action.focus();
	else {
		ligne.tabIndex = -1;
		ligne.focus();
	}
	return true;
}

/** Le focus est perdu (sur le corps de la page) ou encore dans `zone` : on peut le déplacer sans surprendre. */
export function focusLibre(zone: HTMLElement | null | undefined): boolean {
	const actif = document.activeElement;
	return !actif || actif === document.body || (zone?.contains(actif) ?? false);
}
