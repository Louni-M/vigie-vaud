// Rechargement de secours quand un fichier du site (code ou feuille de style) ne se charge pas : un 503 pendant
// la propagation d'un déploiement sur GitHub Pages, ou un onglet resté sur l'ancienne version dont les fichiers
// ont disparu. Sans lui, la page reste à moitié chargée jusqu'à ce que le visiteur la recharge. La date du dernier
// rechargement est gardée dans sessionStorage : on ne recharge pas une deuxième fois dans le délai, jamais en boucle.

/** Clé, dans sessionStorage, de la date du dernier rechargement de secours. */
export const CLE_RECHARGEMENT = 'vigie-vaud:rechargement';

/** Pas plus d'un rechargement de secours dans ce délai (10 min). */
export const DELAI_RECHARGEMENT = 10 * 60_000;

type Stockage = Pick<Storage, 'getItem' | 'setItem'>;

/**
 * Réserve le rechargement de secours : `true` s'il est permis (sa date est alors notée), `false` si un autre a eu
 * lieu dans le délai. `stockage` est une fonction, car lire `sessionStorage` peut lever une exception ; sans
 * stockage utilisable, pas de rechargement : rien n'empêcherait une boucle.
 */
export function reserverRechargement(stockage: () => Stockage, maintenant: number): boolean {
	try {
		const s = stockage();
		const dernier = Number(s.getItem(CLE_RECHARGEMENT));
		// Une date dans le futur (horloge reculée) ne bloque pas pour toujours.
		if (dernier && dernier <= maintenant && maintenant - dernier < DELAI_RECHARGEMENT) return false;
		s.setItem(CLE_RECHARGEMENT, String(maintenant));
		return true;
	} catch {
		return false;
	}
}

/**
 * Vrai si l'erreur vient d'une feuille de style. Sans elle, le module se charge quand même : la page peut
 * s'afficher, moins bien mise en forme. Le message est celui du code de préchargement de Vite.
 */
export function estFeuilleDeStyle(erreur: unknown): boolean {
	return erreur instanceof Error && erreur.message.startsWith('Unable to preload CSS');
}
