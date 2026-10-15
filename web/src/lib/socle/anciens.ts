import type { Commune } from '#lib/types.js';

/**
 * Adresse `/commune/<ancien-slug>`, qui n'existe pas (pas de pages d'alias) : la 404 la reconnaît d'après
 * `communes.json` et renvoie vers la commune actuelle (« Cully fait partie de Bourg-en-Lavaux depuis 2011 »,
 * « Yverdon s’appelle Yverdon-les-Bains depuis 1982 »).
 * `chemin` est relatif à la base du site.
 */
export function ancienneAdresse(communes: readonly Commune[], chemin: string): { phrase: string; commune: Commune } | null {
	const slug = /^\/commune\/([^/]+)\/?$/.exec(chemin)?.[1];
	for (const commune of communes)
		for (const a of commune.anciens)
			if (a.slug === slug) {
				const lien = a.type === 'Ancien nom' ? 's’appelle' : 'fait partie de';
				return { phrase: `${a.nom} ${lien} ${commune.nom} depuis ${a.annee}`, commune };
			}
	return null;
}
