// Mesure d'audience GoatCounter (#16). Elle n'existe que si `VITE_GOATCOUNTER` (le code du site chez
// GoatCounter) est défini à la construction : sans lui, aucune requête ni texte qui en parle. Elle compte le
// chemin de la page sans ses paramètres : `/commune/pully` est compté, le centre de la carte et le dossier
// ouvert (`?d=`) ne le sont pas. Le script de GoatCounter (count.js) n'est pas chargé : il enverrait les
// paramètres de l'adresse (`q`) et la page précédente (`r`). Chaque page vue est envoyée par son pixel de
// comptage, avec le chemin seul.

export interface MesureAudience {
	/** Adresse du pixel de comptage, sans paramètres. */
	compteur: string;
	/** Tableau de bord public. */
	tableau: string;
}

/** Mesure d'audience du code GoatCounter donné à la construction, ou `null` si elle est désactivée. */
export function mesureAudience(code: string | undefined): MesureAudience | null {
	const c = code?.trim();
	if (!c) return null;
	const tableau = `https://${c}.goatcounter.com`;
	return { compteur: `${tableau}/count`, tableau };
}

/**
 * Adresse du pixel qui compte une page vue : le chemin (`p`) et rien d'autre de la page, plus un nombre
 * aléatoire (`rnd`, ignoré par GoatCounter) pour que le navigateur ne la serve pas depuis son cache.
 */
export function adresseDeComptage(mesure: MesureAudience, chemin: string, aleatoire: number): string {
	const parametres = new URLSearchParams({ p: chemin, rnd: aleatoire.toString(36).slice(2) });
	return `${mesure.compteur}?${parametres}`;
}

/**
 * Chemin à compter après une navigation de `depuis` vers `vers` (`depuis` vaut `null` à l'arrivée sur le
 * site), ou `null` s'il n'y a rien à compter : les déplacements de la carte et l'ouverture d'un dossier ne
 * changent que les paramètres, ils restent sur la même page.
 */
export function cheminACompter(depuis: URL | null | undefined, vers: URL | null | undefined): string | null {
	if (!vers) return null;
	if (depuis && depuis.pathname === vers.pathname) return null;
	return vers.pathname;
}

/** Mesure d'audience de cette construction. */
export const AUDIENCE = mesureAudience(import.meta.env.VITE_GOATCOUNTER as string | undefined);
