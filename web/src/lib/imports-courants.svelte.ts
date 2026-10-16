// Dernier import des conseils pour la visite en cours : `conseils/import.json` est chargé une seule fois, au premier
// besoin (badge d'une source `import`, page Couverture), dans le navigateur. Avant (et à la pré-génération), il vaut
// `null`, et le badge dit le dernier import inconnu.
import { browser } from '$app/env';
import { chargerImports } from './imports-conseils.js';
import type { ImportConseils } from './schema.js';

let imports = $state.raw<ImportConseils | null>(null);
/** Vrai une fois le fichier chargé, même illisible : `imports` vaut alors `null`. */
let charge = $state(false);
let demande = false;

/** Le contenu de `conseils/import.json`, une fois chargé et lisible ; `null` sinon. */
export function importsCourants(): ImportConseils | null {
	if (browser && !demande) {
		demande = true;
		chargerImports(fetch).then((i) => {
			imports = i;
			charge = true;
		});
	}
	return imports;
}

/** Vrai une fois `conseils/import.json` chargé, lisible ou non. */
export function importsCharges(): boolean {
	return charge;
}
