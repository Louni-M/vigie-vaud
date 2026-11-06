// Les textes que les pages Almanach reçoivent tout faits (sources.json, libellés de la Couverture) gardent des espaces
// ordinaires. À l'affichage, l'espace devant ; : ? ! » et après « devient insécable : aucun signe ne se retrouve seul
// en début de ligne.

/** Le texte, avec des espaces insécables devant ; : ? ! » et après «. */
export const insecables = (texte: string): string =>
	texte.replace(/ (?=[;:?!»])/g, ' ').replace(/« /g, '« ');

/** Les nombres affichés à la suisse romande (séparateur de milliers) : « 1 234 ». */
export const nombre = new Intl.NumberFormat('fr-CH');

/** Unités qu'un nombre ne quitte pas en fin de ligne (« 180 m », « 14 jours »). */
const UNITES = 'km|m|cm|mm|mètres?|kg|t|ha|%|min|jours?|semaines?|mois|ans?';

/**
 * Le texte d'une source (titre d'un Objet, point d'ordre du jour, description d'un dossier, remarque d'une
 * restriction), aux règles de l'affichage : les insécables de `insecables`, puis « n° 12 », « 18 h 30 » et
 * « 180 m » insécables, et « ... » en points de suspension.
 */
export const typographier = (texte: string): string =>
	insecables(texte)
		.replace(/\b([nN]°) (?=\S)/g, '$1 ')
		.replace(/(\d) h (\d{2})(?!\d)/g, '$1 h $2')
		.replace(/(\d) h(?![\p{L}\d])/gu, '$1 h')
		.replace(new RegExp(`(\\d) (${UNITES})(?![\\p{L}\\d])`, 'gu'), '$1 $2')
		.replace(/\.\.\.(?!\.)/g, '…');
