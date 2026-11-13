// Dernier import des conseils pour la visite en cours : `conseils/import.json` est chargé au premier besoin (badge
// d'une source `import`, page Couverture), dans le navigateur, et relu après un échec (`creerEtatSource`). Avant (et
// à la pré-génération), il vaut `null`, et le badge dit le dernier import inconnu.
import { creerEtatSource } from './etat-source.svelte.js';
import { chargerImports } from './imports-conseils.js';
import type { ImportConseils } from './schema.js';

// Les deux lectures déclenchent le chargement : une page qui ne lit le contenu qu'une fois le fichier chargé
// (`importsCharges() ? … importsCourants() … : '…'`) le demande quand même.
const imports = creerEtatSource(() => chargerImports(fetch));

/** Le contenu de `conseils/import.json`, une fois chargé et lisible ; `null` sinon. */
export function importsCourants(): ImportConseils | null {
	return imports.valeur();
}

/** Vrai une fois le premier chargement de `conseils/import.json` terminé, même en échec. */
export function importsCharges(): boolean {
	return imports.chargee();
}
