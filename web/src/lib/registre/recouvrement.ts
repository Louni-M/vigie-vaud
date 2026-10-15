/** Préfixe des ancres que le registre pose sur la carte, une par couche, dans l'ordre du registre. */
export const PREFIXE_ANCRE = 'couche:';

/**
 * Calques des couches dessinées au-dessus de celle dont l'ancre est `ancre`, d'après l'ordre de dessin de la
 * carte (`ordre`, du dessous au dessus). Le repère du socle, au-dessus de la dernière ancre, n'en fait pas partie.
 */
export function calquesAuDessus(ordre: readonly string[], ancre: string): string[] {
	const debut = ordre.indexOf(ancre);
	const fin = ordre.findLastIndex((id) => id.startsWith(PREFIXE_ANCRE));
	return ordre.slice(debut + 1, fin).filter((id) => !id.startsWith(PREFIXE_ANCRE));
}
