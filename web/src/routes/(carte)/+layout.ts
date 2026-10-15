import { getCommunes } from '#lib/socle/communes.js';
import type { LayoutLoad } from './$types';

// Index des communes (swisstopo, hébergé avec le site), intégré aux pages pré-générées : la fiche d'une
// commune est rendue avec la page, et la recherche est prête sans attendre. Aucune donnée CAMAC n'est lue ici :
// les dossiers sont chargés en direct par le navigateur.
export const load: LayoutLoad = async ({ fetch }) => ({ communes: await getCommunes(fetch) });
