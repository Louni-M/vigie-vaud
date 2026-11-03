// Les textes que les pages Almanach reçoivent tout faits (sources.json, libellés de la Couverture) gardent des espaces
// ordinaires. À l'affichage, l'espace devant ; : ? ! » et après « devient insécable : aucun signe ne se retrouve seul
// en début de ligne.

/** Le texte, avec des espaces insécables devant ; : ? ! » et après «. */
export const insecables = (texte: string): string =>
	texte.replace(/ (?=[;:?!»])/g, ' ').replace(/« /g, '« ');
