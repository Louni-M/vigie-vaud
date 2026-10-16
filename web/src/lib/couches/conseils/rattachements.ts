// Ce que l'onglet Conseil et la fiche d'un Objet disent du rattachement des Objets du Grand Conseil aux communes
// (ADR 0016) : les communes nommées, l'origine du rattachement à une commune, et le courriel qui signale une erreur.
import { COURRIEL } from '#lib/config.js';
import type { CommuneRattachee, LigneObjet } from '#lib/schema.js';
import type { Commune } from '#lib/types.js';
import { lireCle, numeroObjet } from './cles.js';

/** Les noms des communes rattachées, dans l'ordre du rattachement ; une commune que le site ne connaît plus est passée. */
export function communesNommees(rattachees: readonly CommuneRattachee[], communes: readonly Commune[]): string[] {
	return rattachees.flatMap((r) => communes.find((c) => c.bfs === r.ofs)?.nom ?? []);
}

const ORIGINES: Record<CommuneRattachee['origine'], string> = {
	titre: 'nommée dans le titre',
	document: 'citée dans un document',
	correction: 'rattachée à la main'
};

/**
 * Le lien « signaler une erreur » d'un Objet du Grand Conseil : un courriel pré-rempli, d'objet « Rattachement
 * 26_INT_140 », avec la clé de l'Objet et ses communes nommées dans le corps, pour signaler sans compte GitHub.
 */
export function signalement(cle: string, nommees: readonly string[], courriel: string = COURRIEL): string {
	const lue = lireCle(cle);
	const numero = lue ? numeroObjet(lue) : cle;
	const corps = [
		'Bonjour,',
		'',
		`Le rattachement de l’objet ${numero} du Grand Conseil aux communes me semble faux.`,
		'',
		`Clé : ${cle}`,
		`Communes nommées : ${nommees.length ? nommees.join(', ') : 'aucune'}`,
		'',
		'Ce qui ne va pas (une commune en trop, une commune qui manque) :',
		''
	].join('\n');
	// `encodeURIComponent` et non `URLSearchParams` : un client de courriel lit `+` tel quel, pas comme une espace.
	return `mailto:${courriel}?subject=${encodeURIComponent(`Rattachement ${numero}`)}&body=${encodeURIComponent(corps)}`;
}

/** Comment l'Objet est rattaché à la commune (n° OFS) : « nommée dans le titre »… ; `null` s'il ne l'est pas. */
export function origineDans(objet: Pick<LigneObjet, 'communes'>, ofs: number): string | null {
	const r = objet.communes.find((c) => c.ofs === ofs);
	return r ? ORIGINES[r.origine] : null;
}
