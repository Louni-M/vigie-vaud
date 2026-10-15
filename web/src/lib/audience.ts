// Mesure d'audience GoatCounter (#16). Elle n'existe que si `VITE_GOATCOUNTER` (le code du site chez
// GoatCounter) est défini à la construction : sans lui, ni script ni texte qui en parle. Elle compte le chemin
// de la page sans ses paramètres : `/commune/pully` est compté, le centre de la carte et le dossier ouvert
// (`?d=`) ne le sont pas.

export interface MesureAudience {
	/** Adresse de comptage, lue par le script de GoatCounter (`data-goatcounter`). */
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
