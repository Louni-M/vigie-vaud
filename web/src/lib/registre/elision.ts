/**
 * Complément « de <nom> » d'une commune, partout où le site la nomme après « de » (« Fermer la fiche de Pully »,
 * « l'administration communale du Mont-sur-Lausanne », « le site des Clées ») : « d’ » devant une
 * voyelle ou un y (« d’Yverdon-les-Bains », « d’Echallens », « d’Ollon »), et l'article contracté devant « Le » et
 * « Les » (« du Chenit », « des Clées »). Le h initial est traité comme aspiré : les communes vaudoises en h
 * s'écrivent « de Hautemorges », « de Henniez », « de Hermenches ». « La » et « L’ » restent tels quels
 * (« de La Sarraz », « de L’Abbaye »).
 */
export function deNom(nom: string): string {
	if (/^Les /.test(nom)) return `des ${nom.slice(4)}`;
	if (/^Le /.test(nom)) return `du ${nom.slice(3)}`;
	if (/^[aeiouyàâäéèêëîïôöùûüÿæœ]/i.test(nom)) return `d’${nom}`;
	return `de ${nom}`;
}
